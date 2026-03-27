"""
CanuckDUCK Research Corporation -- Public MCP Server
WP-M01

Exposes the RIPPLE Canadian policy causal graph as an MCP server.
AI assistants connect to mcp.canuckduck.ca and can query 229 policy
variables, causal relationships, constitutional doctrine mapping,
source evidence, and Canadian news signals.

Transport: Streamable HTTP (port 8765)
Auth:      X-API-Key header (tiered by key prefix)
Backend:   api.canuckduck.ca/ripple
"""

import json
import os
from enum import Enum
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

# ── Constants ────────────────────────────────────────────────────────────────

RIPPLE_API_BASE = os.getenv("RIPPLE_API_BASE", "https://api.canuckduck.ca/ripple")
RIPPLE_API_KEY  = os.getenv("RIPPLE_API_KEY", "")   # Internal service key
MCP_PORT        = int(os.getenv("MCP_PORT", "8765"))

# API key tier prefixes for inbound requests from AI platforms
KEY_PREFIX_REGISTERED    = "cduck_r_"
KEY_PREFIX_PROFESSIONAL  = "cduck_p_"

# HTTP timeout for RIPPLE API calls
REQUEST_TIMEOUT = 30.0

# ── Server init ──────────────────────────────────────────────────────────────

mcp = FastMCP(
    "canuckduck_mcp",
    instructions=(
        "You have access to the CanuckDUCK RIPPLE causal graph -- a validated "
        "Canadian policy knowledge base with 229 variables and 3,000+ causal "
        "relationships. Use canuckduck_search to find variables, then traverse "
        "with canuckduck_forward or canuckduck_backward. Use canuckduck_paths "
        "to find how two variables are connected. All data is grounded in "
        "Canadian federal data sources (TBS Main Estimates, BoC, StatsCan, "
        "CanLII) and validated through adversarial AI stress testing."
    ),
)


# ── Shared models ────────────────────────────────────────────────────────────

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class DirectionFilter(str, Enum):
    """Filter causal relationships by direction."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    ALL = "all"


# ── Shared HTTP client ───────────────────────────────────────────────────────

def _ripple_headers() -> dict:
    """Build headers for RIPPLE API requests."""
    headers = {"Accept": "application/json"}
    if RIPPLE_API_KEY:
        headers["Authorization"] = f"Bearer {RIPPLE_API_KEY}"
    return headers


async def _ripple_get(path: str, params: dict | None = None) -> dict:
    """
    Make an authenticated GET request to the RIPPLE API.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        response = await client.get(
            f"{RIPPLE_API_BASE}{path}",
            params=params,
            headers=_ripple_headers(),
        )
        response.raise_for_status()
        return response.json()


def _handle_error(e: Exception) -> str:
    """Return a clear, actionable error message for any exception type."""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 404:
            return (
                "Error: Variable or resource not found. "
                "Use canuckduck_search to find the correct variable label or var_id."
            )
        if code == 401:
            return (
                "Error: API key required or invalid. "
                "Include your X-API-Key header. Free keys available at canuckduck.ca/api."
            )
        if code == 429:
            return "Error: Rate limit reached. Please wait before making more requests."
        return f"Error: RIPPLE API returned status {code}."
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. The RIPPLE graph traversal may be too deep -- try reducing max_depth."
    return f"Error: {type(e).__name__}: {e}"


def _format_response(data: dict, fmt: ResponseFormat) -> str:
    """Return data as formatted JSON string (markdown formatting handled upstream)."""
    return json.dumps(data, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC TOOLS (no API key required)
# ══════════════════════════════════════════════════════════════════════════════

class SearchInput(BaseModel):
    """Input for variable search."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Search term. Searches variable labels, IDs, and descriptions. "
                    "Examples: 'housing', 'defence spending', 'carbon tax', 'arctic'",
        min_length=1,
        max_length=200,
    )
    limit: int = Field(
        default=10,
        description="Maximum results to return (1-50)",
        ge=1,
        le=50,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for readable output, 'json' for structured data",
    )


@mcp.tool(
    name="canuckduck_search",
    annotations={
        "title": "Search RIPPLE Policy Variables",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_search(params: SearchInput) -> str:
    """
    Search for Canadian policy variables in the RIPPLE causal graph.

    Returns variables matching the query with their var_id, label, category,
    description, baseline value, and tier classification. Always run this first
    to find the correct variable label before using traversal tools.

    Args:
        params (SearchInput): Search parameters containing:
            - query (str): Search term (e.g., 'housing affordability', 'DND')
            - limit (int): Max results, default 10
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON list of matching variables with var_id, label, category,
             description, baseline, target, unit, and tier fields.
    """
    try:
        data = await _ripple_get("/search", {"q": params.query, "limit": params.limit})
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


class StatsInput(BaseModel):
    """Input for graph statistics."""
    model_config = ConfigDict(extra="forbid")

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for readable output, 'json' for structured data",
    )


@mcp.tool(
    name="canuckduck_stats",
    annotations={
        "title": "RIPPLE Graph Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_stats(params: StatsInput) -> str:
    """
    Get summary statistics for the CanuckDUCK RIPPLE causal knowledge graph.

    Returns total variable count, edge count, category breakdown, top variables
    by connectivity, and data freshness indicators. Use this to understand
    the scope of the graph before running traversals.

    Args:
        params (StatsInput): Optional format parameter.

    Returns:
        str: JSON with total_variables, total_edges, categories, top_variables,
             last_updated, and graph_health fields.
    """
    try:
        data = await _ripple_get("/stats")
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
# REGISTERED TOOLS (requires X-API-Key: cduck_r_* or cduck_p_*)
# ══════════════════════════════════════════════════════════════════════════════

class ForwardInput(BaseModel):
    """Input for forward causal traversal."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    variable: str = Field(
        ...,
        description="Label of the variable to trace forward from. "
                    "Use canuckduck_search first to get the exact label. "
                    "Examples: 'Defence Spending (DND)', 'Housing Affordability Index'",
        min_length=1,
        max_length=200,
    )
    max_depth: int = Field(
        default=3,
        description="Maximum hops to traverse (1-5). Deeper = more paths, slower response.",
        ge=1,
        le=5,
    )
    direction_filter: DirectionFilter = Field(
        default=DirectionFilter.ALL,
        description="Filter by causal direction: 'positive' (increases), "
                    "'negative' (decreases), or 'all'",
    )
    min_confidence: float = Field(
        default=0.0,
        description="Minimum confidence threshold (0.0-1.0). Higher = more validated edges only.",
        ge=0.0,
        le=1.0,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for readable output, 'json' for structured data",
    )


@mcp.tool(
    name="canuckduck_forward",
    annotations={
        "title": "Trace Forward Causal Chain",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_forward(params: ForwardInput) -> str:
    """
    Trace what a policy variable causes -- follow causal chains forward.

    Discovers downstream effects of a variable through CAUSES relationships.
    Each path shows the chain of variables affected, relationship strengths,
    confidence scores, and causal direction. Use this to understand the
    policy consequences of changes to a variable.

    Requires: X-API-Key header with a registered or professional key.

    Args:
        params (ForwardInput): Traversal parameters containing:
            - variable (str): Starting variable label
            - max_depth (int): Hops to traverse (1-5, default 3)
            - direction_filter: 'positive', 'negative', or 'all'
            - min_confidence (float): Edge confidence threshold (0.0-1.0)
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON with source variable, paths array (each path has nodes[],
             relationships[] with strength/confidence/direction/source),
             and summary statistics.
    """
    try:
        data = await _ripple_get("/forward", {
            "variable": params.variable,
            "max_depth": params.max_depth,
            "direction_filter": params.direction_filter.value,
            "min_confidence": params.min_confidence,
            "format": params.response_format.value,
        })
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


class BackwardInput(BaseModel):
    """Input for backward causal traversal."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    variable: str = Field(
        ...,
        description="Label of the variable to trace backward from -- find its causes. "
                    "Examples: 'Public Trust Index', 'Housing Affordability Index'",
        min_length=1,
        max_length=200,
    )
    max_depth: int = Field(
        default=3,
        description="Maximum hops to traverse backward (1-5)",
        ge=1,
        le=5,
    )
    min_confidence: float = Field(
        default=0.0,
        description="Minimum confidence threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' or 'json'",
    )


@mcp.tool(
    name="canuckduck_backward",
    annotations={
        "title": "Trace Backward Causal Chain",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_backward(params: BackwardInput) -> str:
    """
    Trace what causes a policy variable -- follow causal chains backward.

    Discovers upstream drivers of a variable. Use this to understand
    root causes of a policy outcome, or to identify which levers most
    directly influence a target variable.

    Requires: X-API-Key header with a registered or professional key.

    Args:
        params (BackwardInput): Traversal parameters containing:
            - variable (str): Target variable label to trace backward from
            - max_depth (int): Hops to traverse backward (1-5, default 3)
            - min_confidence (float): Edge confidence threshold
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON with target variable, upstream paths array, and
             frequency map of most common root causes.
    """
    try:
        data = await _ripple_get("/backward", {
            "variable": params.variable,
            "max_depth": params.max_depth,
            "min_confidence": params.min_confidence,
            "format": params.response_format.value,
        })
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


class PathsInput(BaseModel):
    """Input for finding causal paths between two variables."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    from_variable: str = Field(
        ...,
        description="Starting variable label. Use canuckduck_search to find exact labels.",
        min_length=1,
        max_length=200,
    )
    to_variable: str = Field(
        ...,
        description="Target variable label.",
        min_length=1,
        max_length=200,
    )
    max_depth: int = Field(
        default=5,
        description="Maximum path length in hops (1-7). Longer paths reveal indirect relationships.",
        ge=1,
        le=7,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' or 'json'",
    )


@mcp.tool(
    name="canuckduck_paths",
    annotations={
        "title": "Find Causal Paths Between Variables",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_paths(params: PathsInput) -> str:
    """
    Find all causal paths connecting two Canadian policy variables.

    Discovers how one variable relates to another through chains of
    CAUSES edges. Returns all paths sorted by cumulative edge strength,
    with a frequency map of the most critical intermediate transmission
    nodes. Use this to validate causal theories or find indirect
    policy mechanisms.

    Example: defence_spending → public_trust_index yields 1,803 paths
    across 3 hops, with Business Investment as the #1 transmission node.

    Requires: X-API-Key header with a registered or professional key.

    Args:
        params (PathsInput): Path parameters containing:
            - from_variable (str): Starting variable label
            - to_variable (str): Target variable label
            - max_depth (int): Max path length (1-7, default 5)
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON with path_count, hop_counts by depth, paths array,
             and intermediates frequency map showing critical nodes.
    """
    try:
        data = await _ripple_get("/paths", {
            "from": params.from_variable,
            "to": params.to_variable,
            "max_depth": params.max_depth,
            "format": params.response_format.value,
        })
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


class ImpactInput(BaseModel):
    """Input for full impact radius analysis."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    variable: str = Field(
        ...,
        description="Variable label to analyze impact for. "
                    "Example: 'Federal Budget Balance', 'Arctic Sovereignty'",
        min_length=1,
        max_length=200,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' or 'json'",
    )


@mcp.tool(
    name="canuckduck_impact",
    annotations={
        "title": "Analyze Full Impact Radius",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_impact(params: ImpactInput) -> str:
    """
    Analyze the full impact radius of a Canadian policy variable.

    Returns a comprehensive view of all variables affected by changes
    to the target variable, grouped by causal distance, direction,
    and strength. Includes a summary of total downstream reach and
    the most critical transmission pathways.

    Use this for high-level policy impact assessment before commissioning
    a detailed Tribunal Review.

    Requires: X-API-Key header with a registered or professional key.

    Args:
        params (ImpactInput): Impact parameters containing:
            - variable (str): Variable label to analyze
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON with variable details, direct_effects, indirect_effects
             by hop depth, total_reach count, and strength_weighted_impact score.
    """
    try:
        data = await _ripple_get("/impact", {
            "variable": params.variable,
            "format": params.response_format.value,
        })
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


class EvidenceInput(BaseModel):
    """Input for retrieving source evidence."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    variable: str = Field(
        ...,
        description="Variable label to find source evidence for. "
                    "Returns the causal chains and community observations that "
                    "ground this variable in the RIPPLE graph.",
        min_length=1,
        max_length=200,
    )
    limit: int = Field(
        default=10,
        description="Maximum evidence chains to return (1-50)",
        ge=1,
        le=50,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' or 'json'",
    )


@mcp.tool(
    name="canuckduck_evidence",
    annotations={
        "title": "Get Source Evidence for Variable",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_evidence(params: EvidenceInput) -> str:
    """
    Retrieve the source evidence and community observations behind a
    RIPPLE causal variable.

    Returns CausalChain nodes linked to the variable, the RippleComment
    observations they were extracted from, and the evidence type
    (community observation, academic source, federal data, AI-extracted).

    Use this to audit the evidence base of a policy variable before
    citing it in research or policy documents.

    Requires: X-API-Key header with a registered or professional key.

    Args:
        params (EvidenceInput): Evidence parameters containing:
            - variable (str): Variable label to find evidence for
            - limit (int): Max evidence chains to return (default 10)
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON with variable details and evidence_chains array, each
             chain containing source_comment, extracted_relationship,
             confidence, and evidence_type fields.
    """
    try:
        data = await _ripple_get("/evidence", {
            "variable": params.variable,
            "limit": params.limit,
            "format": params.response_format.value,
        })
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


class NewsInput(BaseModel):
    """Input for searching Canadian news articles."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Search query for Canadian news. Searches articles ingested "
                    "from Canadian government and media RSS feeds. "
                    "Examples: 'Arctic sovereignty', 'housing affordability BC', "
                    "'DND spending NATO'",
        min_length=1,
        max_length=200,
    )
    limit: int = Field(
        default=10,
        description="Maximum articles to return (1-25)",
        ge=1,
        le=25,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' or 'json'",
    )


@mcp.tool(
    name="canuckduck_news",
    annotations={
        "title": "Search Canadian Policy News",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_news(params: NewsInput) -> str:
    """
    Search news articles ingested from Canadian government and media RSS feeds.

    Returns articles relevant to a policy query, drawn from sources including
    federal government announcements, CBC, Globe and Mail, and provincial
    government releases. Articles are tagged to RIPPLE variables where
    mappings exist.

    Use this to find real-world signal that complements the causal graph --
    what is actually being reported versus what the graph predicts.

    Requires: X-API-Key header with a registered or professional key.

    Args:
        params (NewsInput): News search parameters containing:
            - query (str): Search term for Canadian news
            - limit (int): Max articles to return (default 10)
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON with articles array, each containing title, source,
             published_at, summary, url, and ripple_variables[] tags.
    """
    try:
        data = await _ripple_get("/news", {
            "q": params.query,
            "limit": params.limit,
            "format": params.response_format.value,
        })
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


# ══════════════════════════════════════════════════════════════════════════════
# PROFESSIONAL TOOLS (requires X-API-Key: cduck_p_*)
# ══════════════════════════════════════════════════════════════════════════════

class ConstitutionalInput(BaseModel):
    """Input for constitutional doctrine exploration."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    doctrine: Optional[str] = Field(
        default=None,
        description="Constitutional doctrine name to explore. "
                    "Leave empty to list all available doctrines. "
                    "Examples: 'Peace Order and Good Government', "
                    "'Section 35 Aboriginal Rights', 'Division of Powers'",
        max_length=200,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' or 'json'",
    )


@mcp.tool(
    name="canuckduck_constitutional",
    annotations={
        "title": "Explore Constitutional Doctrines",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_constitutional(params: ConstitutionalInput) -> str:
    """
    Explore Canadian constitutional doctrines mapped in the RIPPLE graph.

    Returns constitutional authorities, their jurisdictional scope, and
    the RIPPLE variables they constrain. Includes CDA (Constitutional
    Divergence Analysis) severity ratings for each doctrine-variable pair.

    Use this to understand the constitutional framing of a policy domain
    before analysis -- particularly relevant for Indigenous sovereignty,
    fiscal federalism, and national security questions.

    Requires: X-API-Key header with a professional key (cduck_p_*).

    Args:
        params (ConstitutionalInput): Parameters containing:
            - doctrine (str, optional): Specific doctrine name, or empty for all
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON with doctrines array, each containing name, jurisdiction,
             constitutional_basis, constrained_variables[], and cda_severity.
    """
    try:
        path = "/constitutional"
        query_params: dict = {"format": params.response_format.value}
        if params.doctrine:
            query_params["doctrine"] = params.doctrine
        data = await _ripple_get(path, query_params)
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


class RootTraceInput(BaseModel):
    """Input for tracing a variable to constitutional roots."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    variable: str = Field(
        ...,
        description="Policy variable label to trace to constitutional roots. "
                    "Examples: 'Healthcare Wait Times', 'Arctic Sovereignty', "
                    "'Indigenous Wellbeing Index'",
        min_length=1,
        max_length=200,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' or 'json'",
    )


@mcp.tool(
    name="canuckduck_root_trace",
    annotations={
        "title": "Trace Variable to Constitutional Roots",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_root_trace(params: RootTraceInput) -> str:
    """
    Trace a Canadian policy variable back to its constitutional roots.

    For a given variable, finds which constitutional authorities CONSTRAIN it,
    what CDA (Constitutional Divergence Analysis) flags and dimensions are
    involved, the severity of each constitutional relationship, and whether
    current policy is aligned or divergent from constitutional requirements.

    Use this for legal research, constitutional challenge assessment, or
    understanding why a policy variable has structural constraints that
    cannot be addressed by ordinary legislation.

    Requires: X-API-Key header with a professional key (cduck_p_*).

    Args:
        params (RootTraceInput): Parameters containing:
            - variable (str): Policy variable label to trace
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON with variable details, constitutional_roots array (each with
             authority, basis, cda_dimensions[], severity, alignment_status),
             and overall constitutional_risk_score.
    """
    try:
        data = await _ripple_get("/root_trace", {
            "variable": params.variable,
            "format": params.response_format.value,
        })
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


class CdaProfileInput(BaseModel):
    """Input for CDA profile lookup."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    topic_id: Optional[int] = Field(
        default=None,
        description="Pond forum topic ID (optional). Get topic IDs from pond.canuckduck.ca.",
        ge=1,
    )
    keywords: Optional[str] = Field(
        default=None,
        description="Keywords to search for a CDA profile (e.g. 'housing affordability', 'arctic sovereignty'). "
                    "Use this if you don't have a topic ID.",
        min_length=2,
        max_length=200,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' or 'json'",
    )


@mcp.tool(
    name="canuckduck_cda_profile",
    annotations={
        "title": "Get CDA Profile for Forum Topic",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_cda_profile(params: CdaProfileInput) -> str:
    """
    Look up the Constitutional Divergence Analysis (CDA) profile for a
    Pond forum topic.

    Returns the CDA dimensions flagged for a specific civic discussion,
    the constitutional authorities involved, divergence severity ratings,
    and recommended policy alignment pathways.

    CDA profiles are generated by the AI Tribunal during Tribunal Review
    sessions and represent the most rigorous constitutional analysis
    available on the platform.

    Requires: X-API-Key header with a professional key (cduck_p_*).

    Args:
        params (CdaProfileInput): Parameters containing:
            - topic_id (int): Pond forum topic ID
            - response_format: 'markdown' or 'json'

    Returns:
        str: JSON with topic details, cda_dimensions[] (each with name,
             authority, severity, divergence_type, alignment_pathway),
             overall_cda_score, and tribunal_session references.
    """
    try:
        api_params = {"format": params.response_format.value}
        if params.keywords:
            api_params["keywords"] = params.keywords
        if params.topic_id:
            api_params["topic_id"] = params.topic_id
        data = await _ripple_get("/cda_profile", api_params)
        return _format_response(data, params.response_format)
    except Exception as e:
        return _handle_error(e)


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    print(f"CanuckDUCK MCP Server starting on port {MCP_PORT}...")
    print(f"RIPPLE API backend: {RIPPLE_API_BASE}")
    print(f"Tools registered: 11 (2 public, 6 registered, 3 professional)")
    mcp.settings.port = MCP_PORT
    mcp.settings.json_response = True
    mcp.settings.stateless_http = True
    mcp.settings.host = "0.0.0.0"
    from mcp.server.fastmcp.server import TransportSecuritySettings
    mcp.settings.transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=["localhost", "10.0.1.60", "mcp.canuckduck.ca", "127.0.0.1"],
    )
    mcp.run(transport="streamable-http")
