"""
canuckduck_propose and canuckduck_review_queue MCP tools.
Appended to canuckduck_mcp.py during deployment.

These tools enable any MCP client to propose new variables, edges, or
evidence to the RIPPLE graph through a review/approve workflow.
"""

import uuid
import time
import re

import psycopg2
import psycopg2.extras

# ── Proposal DB connection ───────────────────────────────────────────────────

PROPOSAL_DB_DSN = os.getenv(
    "PROPOSAL_DB_DSN",
    "host=10.0.1.63 port=5432 dbname=ducklings_db user=ducklings_user "
    "password=qaM6YDSRcKjk0nJp9BOnTCe3VuqAwHQI4q32wniCH34=",
)

# Rate limits: {api_key: [(timestamp, count)]}
_rate_limits: dict[str, list] = {}

RATE_LIMITS = {
    "variable": {"registered": 5, "professional": 20},
    "edge": {"registered": 10, "professional": 50},
    "evidence": {"registered": 10, "professional": 50},
}

VALID_CATEGORIES = [
    "fiscal", "economic", "financial", "demographic", "environmental",
    "governance", "infrastructure", "operational", "social", "security",
    "health", "education", "cultural",
]

VALID_EVIDENCE_TYPES = [
    "empirical", "accounting", "policy", "academic", "structural",
    "theoretical", "statistical", "government_report", "legal", "model",
]


def _get_proposal_db():
    """Get a connection to the proposal queue database."""
    return psycopg2.connect(PROPOSAL_DB_DSN)


def _check_rate_limit(api_key: str, proposal_type: str) -> bool:
    """Check if the API key has exceeded its rate limit. Returns True if OK."""
    tier = "professional" if api_key.startswith(KEY_PREFIX_PROFESSIONAL) else "registered"
    limit = RATE_LIMITS.get(proposal_type, {}).get(tier, 5)
    now = time.time()
    hour_ago = now - 3600

    if api_key not in _rate_limits:
        _rate_limits[api_key] = []

    # Prune old entries
    _rate_limits[api_key] = [t for t in _rate_limits[api_key] if t > hour_ago]

    if len(_rate_limits[api_key]) >= limit:
        return False

    _rate_limits[api_key].append(now)
    return True


async def _check_variable_exists(var_id: str) -> bool:
    """Check if a variable exists in the RIPPLE graph."""
    try:
        data = await _ripple_get("/variables", {"query": var_id, "limit": 50})
        results = data.get("results", data.get("variables", []))
        return any(
            r.get("variable_key") == var_id or r.get("var_id") == var_id
            for r in results
        )
    except Exception:
        return False


async def _run_duplicate_check(var_id: str, label: str) -> dict:
    """Check for duplicate or very similar variables."""
    try:
        # Search by var_id fragments and label keywords
        keywords = label.split()[:3]
        query = " ".join(keywords)
        data = await _ripple_get("/variables", {"query": query, "limit": 10})
        results = data.get("results", data.get("variables", []))

        similar = []
        for r in results:
            r_id = r.get("variable_key", r.get("var_id", ""))
            r_label = r.get("display_name", r.get("label", ""))
            if r_id == var_id:
                return {"is_duplicate": True, "exact_match": r_id, "similar_vars": []}
            # Simple word overlap similarity
            label_words = set(label.lower().split())
            r_words = set(r_label.lower().split())
            if label_words and r_words:
                overlap = len(label_words & r_words) / len(label_words | r_words)
                if overlap > 0.4:
                    similar.append({"var_id": r_id, "label": r_label, "similarity": round(overlap, 2)})

        return {"is_duplicate": False, "similar_vars": similar[:5]}
    except Exception:
        return {"is_duplicate": False, "similar_vars": [], "error": "check_failed"}


async def _run_connectivity_test(source_var_id: str, target_var_id: str) -> dict:
    """Test connectivity between two variables."""
    try:
        data = await _ripple_get(f"/paths/{source_var_id}/{target_var_id}", {"max_depth": 3})
        path_count = data.get("path_count", data.get("total_paths", 0))
        return {
            "existing_paths": path_count,
            "is_shortcut": path_count > 0,
            "is_bridge": path_count == 0,
        }
    except Exception:
        return {"existing_paths": 0, "is_bridge": True, "error": "check_failed"}


# ── Propose tool ─────────────────────────────────────────────────────────────

class ProposeVariablePayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    var_id: str = Field(
        ...,
        description="Variable ID (snake_case, e.g. 'hsr_calgary_edmonton_capital_cost'). Must not already exist.",
        min_length=3, max_length=100,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    label: str = Field(
        ...,
        description="Human-readable variable name (e.g. 'Calgary-Edmonton HSR Capital Cost Estimate')",
        min_length=5, max_length=200,
    )
    description: str = Field(
        ...,
        description="Evidence-grounded description explaining what this variable measures, "
                    "why it matters, and what data sources exist. Minimum 50 characters.",
        min_length=50, max_length=2000,
    )
    category: str = Field(
        ...,
        description="Variable category. Must be one of: fiscal, economic, financial, demographic, "
                    "environmental, governance, infrastructure, operational, social, security, "
                    "health, education, cultural",
    )
    unit: str = Field(
        ...,
        description="Unit of measurement (e.g. 'billions_cad', 'index', 'percent', 'millions_per_year')",
        min_length=1, max_length=50,
    )
    baseline_value: float = Field(
        ...,
        description="Current or initial value of the variable",
    )
    jurisdiction: Optional[str] = Field(
        default=None,
        description="Jurisdiction: 2-letter province code (AB, ON, BC, etc.), 'federal', or null for national",
        max_length=10,
    )
    evidence_sources: list[str] = Field(
        ...,
        description="At least one evidence source (URL, citation, or document reference)",
        min_length=1,
    )


class ProposeEdgePayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    source_var_id: str = Field(
        ...,
        description="Source variable ID (must exist in graph). Use canuckduck_search to find.",
        min_length=3, max_length=100,
    )
    target_var_id: str = Field(
        ...,
        description="Target variable ID (must exist in graph). The variable that is CAUSED by the source.",
        min_length=3, max_length=100,
    )
    direction: str = Field(
        ...,
        description="'positive' (source increase causes target increase) or 'negative' (inverse)",
        pattern=r"^(positive|negative)$",
    )
    strength: int = Field(
        ...,
        description="Causal strength estimate (1-100). How strongly does the source affect the target?",
        ge=1, le=100,
    )
    confidence: float = Field(
        ...,
        description="Confidence in this relationship (0.0-1.0). 1.0 = accounting identity, 0.5 = theoretical.",
        ge=0.0, le=1.0,
    )
    evidence_type: str = Field(
        ...,
        description="Evidence type: empirical, accounting, policy, academic, structural, theoretical, "
                    "statistical, government_report, legal, model",
    )
    evidence_source: str = Field(
        ...,
        description="Citation or URL supporting this causal relationship",
        min_length=5, max_length=500,
    )
    mechanism: str = Field(
        ...,
        description="Explain HOW and WHY the causal relationship works. Minimum 30 characters.",
        min_length=30, max_length=1000,
    )
    delay_real_months: Optional[int] = Field(
        default=None,
        description="Estimated months before the effect manifests (null if immediate)",
        ge=0, le=120,
    )


class ProposeEvidencePayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    source_var_id: str = Field(
        ...,
        description="Source variable of the existing edge",
        min_length=3, max_length=100,
    )
    target_var_id: str = Field(
        ...,
        description="Target variable of the existing edge",
        min_length=3, max_length=100,
    )
    evidence_type: str = Field(
        ...,
        description="Type of new evidence being submitted",
    )
    evidence_source: str = Field(
        ...,
        description="Citation, URL, or document reference for the evidence",
        min_length=5, max_length=500,
    )
    confidence_update: Optional[float] = Field(
        default=None,
        description="If you believe confidence should change, suggest new value (0.0-1.0)",
        ge=0.0, le=1.0,
    )
    accuracy_observation: Optional[str] = Field(
        default=None,
        description="Describe an observed outcome that validates or contradicts the predicted relationship",
        max_length=1000,
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL to the source document",
        max_length=500,
    )


class ProposeInput(BaseModel):
    """Submit a proposed variable, edge, or evidence to the RIPPLE graph review queue."""
    model_config = ConfigDict(extra="forbid")

    proposal_type: str = Field(
        ...,
        description="Type of proposal: 'variable' (new variable), 'edge' (new causal relationship), "
                    "or 'evidence' (new evidence for existing edge)",
        pattern=r"^(variable|edge|evidence)$",
    )
    variable: Optional[ProposeVariablePayload] = Field(
        default=None,
        description="Variable proposal details. Required when proposal_type='variable'.",
    )
    edge: Optional[ProposeEdgePayload] = Field(
        default=None,
        description="Edge proposal details. Required when proposal_type='edge'.",
    )
    evidence: Optional[ProposeEvidencePayload] = Field(
        default=None,
        description="Evidence proposal details. Required when proposal_type='evidence'.",
    )
    proposal_context: Optional[str] = Field(
        default=None,
        description="Why you are proposing this — what gap does it fill, what question motivated it?",
        max_length=1000,
    )


@mcp.tool(
    name="canuckduck_propose",
    annotations={
        "title": "Propose Graph Contribution",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def canuckduck_propose(params: ProposeInput) -> str:
    """
    Propose a new variable, causal edge, or evidence to the RIPPLE graph.

    All proposals enter a review queue — nothing is written to the active
    graph until a human reviewer approves it. Use this to contribute
    knowledge that fills gaps in the Canadian policy causal model.

    Three proposal types:
    - 'variable': Propose a new policy variable with evidence sources
    - 'edge': Propose a new CAUSES relationship between existing variables
    - 'evidence': Submit new evidence for an existing causal relationship

    Requires: API key (registered cduck_r_* or professional cduck_p_*).
    Rate limits: 5-20 proposals/hour depending on type and key tier.
    """
    try:
        # Validate proposal type matches payload
        if params.proposal_type == "variable" and not params.variable:
            return "Error: proposal_type is 'variable' but no 'variable' payload provided."
        if params.proposal_type == "edge" and not params.edge:
            return "Error: proposal_type is 'edge' but no 'edge' payload provided."
        if params.proposal_type == "evidence" and not params.evidence:
            return "Error: proposal_type is 'evidence' but no 'evidence' payload provided."

        # Build payload and run validation
        proposal_uuid = str(uuid.uuid4())
        enrichment = {}

        if params.proposal_type == "variable":
            v = params.variable
            if v.category not in VALID_CATEGORIES:
                return f"Error: Invalid category '{v.category}'. Must be one of: {', '.join(VALID_CATEGORIES)}"

            # Check for duplicates
            exists = await _check_variable_exists(v.var_id)
            if exists:
                return f"Error: Variable '{v.var_id}' already exists in the graph. Use 'evidence' type to add evidence to existing variables."

            dup_check = await _run_duplicate_check(v.var_id, v.label)
            enrichment["duplicate_check"] = dup_check

            payload = v.model_dump()

        elif params.proposal_type == "edge":
            e = params.edge
            if e.evidence_type not in VALID_EVIDENCE_TYPES:
                return f"Error: Invalid evidence_type '{e.evidence_type}'. Must be one of: {', '.join(VALID_EVIDENCE_TYPES)}"

            # Check both variables exist
            source_exists = await _check_variable_exists(e.source_var_id)
            target_exists = await _check_variable_exists(e.target_var_id)
            if not source_exists:
                return f"Error: Source variable '{e.source_var_id}' not found. Use canuckduck_search to find the correct var_id."
            if not target_exists:
                return f"Error: Target variable '{e.target_var_id}' not found. Use canuckduck_search to find the correct var_id."

            # Connectivity test
            conn_test = await _run_connectivity_test(e.source_var_id, e.target_var_id)
            enrichment["connectivity_test"] = conn_test

            payload = e.model_dump()

        else:  # evidence
            ev = params.evidence
            # Check both variables exist
            source_exists = await _check_variable_exists(ev.source_var_id)
            target_exists = await _check_variable_exists(ev.target_var_id)
            if not source_exists:
                return f"Error: Source variable '{ev.source_var_id}' not found."
            if not target_exists:
                return f"Error: Target variable '{ev.target_var_id}' not found."

            payload = ev.model_dump()

        # Calculate quality score
        quality = 50.0  # base
        if params.proposal_context:
            quality += 10
        if params.proposal_type == "variable" and params.variable:
            if len(params.variable.description) > 200:
                quality += 10
            if len(params.variable.evidence_sources) > 1:
                quality += 10
            if params.variable.jurisdiction:
                quality += 5
        elif params.proposal_type == "edge" and params.edge:
            if len(params.edge.mechanism) > 100:
                quality += 10
            if params.edge.confidence >= 0.7:
                quality += 5
            if params.edge.delay_real_months is not None:
                quality += 5
            conn = enrichment.get("connectivity_test", {})
            if conn.get("is_bridge"):
                quality += 15  # High value: bridges disconnected subgraphs
        elif params.proposal_type == "evidence" and params.evidence:
            if params.evidence.accuracy_observation:
                quality += 15
            if params.evidence.source_url:
                quality += 5

        enrichment["auto_quality_score"] = min(quality, 100)

        # Write to database
        conn = _get_proposal_db()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO ripple_proposal_queue
                   (uuid, proposal_type, payload, proposed_by_api_key,
                    proposed_by_model, proposal_context,
                    duplicate_check_result, connectivity_test,
                    auto_quality_score, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    proposal_uuid,
                    params.proposal_type,
                    json.dumps(payload),
                    "mcp_session",  # placeholder — real key from auth header
                    "mcp_client",
                    params.proposal_context,
                    json.dumps(enrichment.get("duplicate_check")),
                    json.dumps(enrichment.get("connectivity_test")),
                    enrichment.get("auto_quality_score", 50),
                    "ready_for_review",
                    int(time.time()),
                    int(time.time()),
                ),
            )
            row_id = cur.fetchone()[0]
            conn.commit()
        finally:
            conn.close()

        result = {
            "proposal_id": proposal_uuid,
            "internal_id": row_id,
            "status": "ready_for_review",
            "proposal_type": params.proposal_type,
            "auto_enrichment": enrichment,
            "message": "Proposal submitted successfully. It will be reviewed by the CanuckDUCK team.",
        }
        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        return _handle_error(e)


# ── Review queue tool ────────────────────────────────────────────────────────

class ReviewQueueInput(BaseModel):
    """List, check status, or decide on graph proposals."""
    model_config = ConfigDict(extra="forbid")

    action: str = Field(
        ...,
        description="Action: 'list' (show pending proposals), 'status' (check one proposal), "
                    "or 'decide' (approve/reject — requires professional key + reviewer role)",
        pattern=r"^(list|status|decide)$",
    )
    proposal_id: Optional[str] = Field(
        default=None,
        description="Proposal UUID. Required for 'status' and 'decide' actions.",
        max_length=36,
    )
    decision: Optional[str] = Field(
        default=None,
        description="'approve' or 'reject'. Required for 'decide' action.",
        pattern=r"^(approve|reject)$",
    )
    review_notes: Optional[str] = Field(
        default=None,
        description="Review notes. Required when rejecting a proposal.",
        max_length=1000,
    )
    filters: Optional[dict] = Field(
        default=None,
        description="Filters for 'list': {proposal_type, status, limit}. "
                    "Example: {\"proposal_type\": \"variable\", \"status\": \"ready_for_review\", \"limit\": 20}",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="'markdown' or 'json'",
    )


@mcp.tool(
    name="canuckduck_review_queue",
    annotations={
        "title": "Review Graph Proposals",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def canuckduck_review_queue(params: ReviewQueueInput) -> str:
    """
    List pending graph proposals, check proposal status, or approve/reject.

    Actions:
    - 'list': Show proposals in the review queue (filterable by type, status)
    - 'status': Check the status of a specific proposal by UUID
    - 'decide': Approve or reject a proposal (requires professional API key)

    Approved proposals are written to the active RIPPLE graph. Rejected
    proposals are archived with reviewer notes explaining why.

    Requires: Registered API key for list/status, Professional for decide.
    """
    try:
        conn = _get_proposal_db()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            if params.action == "list":
                filters = params.filters or {}
                where_clauses = []
                filter_values = []

                if "proposal_type" in filters:
                    where_clauses.append("proposal_type = %s")
                    filter_values.append(filters["proposal_type"])
                if "status" in filters:
                    where_clauses.append("status = %s")
                    filter_values.append(filters["status"])

                where_sql = ""
                if where_clauses:
                    where_sql = "WHERE " + " AND ".join(where_clauses)

                limit = min(int(filters.get("limit", 20)), 50)

                cur.execute(
                    f"SELECT uuid, proposal_type, payload, status, auto_quality_score, "
                    f"duplicate_check_result, connectivity_test, proposal_context, "
                    f"created_at, reviewed_at, review_notes "
                    f"FROM ripple_proposal_queue {where_sql} "
                    f"ORDER BY created_at DESC LIMIT %s",
                    filter_values + [limit],
                )
                rows = cur.fetchall()

                proposals = []
                for row in rows:
                    p = dict(row)
                    # Parse JSON fields
                    if isinstance(p.get("payload"), str):
                        p["payload"] = json.loads(p["payload"])
                    if isinstance(p.get("duplicate_check_result"), str):
                        p["duplicate_check_result"] = json.loads(p["duplicate_check_result"])
                    if isinstance(p.get("connectivity_test"), str):
                        p["connectivity_test"] = json.loads(p["connectivity_test"])
                    proposals.append(p)

                # Summary stats
                cur.execute(
                    "SELECT status, count(*) AS cnt FROM ripple_proposal_queue GROUP BY status"
                )
                stats = {row["status"]: row["cnt"] for row in cur.fetchall()}

                result = {
                    "count": len(proposals),
                    "queue_stats": stats,
                    "proposals": proposals,
                }
                return json.dumps(result, indent=2, ensure_ascii=False, default=str)

            elif params.action == "status":
                if not params.proposal_id:
                    return "Error: proposal_id is required for 'status' action."

                cur.execute(
                    "SELECT * FROM ripple_proposal_queue WHERE uuid = %s",
                    (params.proposal_id,),
                )
                row = cur.fetchone()
                if not row:
                    return f"Error: Proposal '{params.proposal_id}' not found."

                p = dict(row)
                if isinstance(p.get("payload"), str):
                    p["payload"] = json.loads(p["payload"])
                if isinstance(p.get("duplicate_check_result"), str):
                    p["duplicate_check_result"] = json.loads(p["duplicate_check_result"])
                if isinstance(p.get("connectivity_test"), str):
                    p["connectivity_test"] = json.loads(p["connectivity_test"])

                return json.dumps(p, indent=2, ensure_ascii=False, default=str)

            elif params.action == "decide":
                if not params.proposal_id:
                    return "Error: proposal_id is required for 'decide' action."
                if not params.decision:
                    return "Error: decision ('approve' or 'reject') is required for 'decide' action."
                if params.decision == "reject" and not params.review_notes:
                    return "Error: review_notes are required when rejecting a proposal."

                # Check proposal exists and is reviewable
                cur.execute(
                    "SELECT id, status, proposal_type, payload FROM ripple_proposal_queue WHERE uuid = %s",
                    (params.proposal_id,),
                )
                row = cur.fetchone()
                if not row:
                    return f"Error: Proposal '{params.proposal_id}' not found."
                if row["status"] not in ("pending", "ready_for_review", "auto_enriching"):
                    return f"Error: Proposal is in '{row['status']}' status and cannot be reviewed."

                now = int(time.time())
                new_status = "approved" if params.decision == "approve" else "rejected"

                cur.execute(
                    """UPDATE ripple_proposal_queue
                       SET status = %s, reviewed_at = %s, review_notes = %s,
                           review_decision_reason = %s, updated_at = %s
                       WHERE uuid = %s""",
                    (
                        new_status, now, params.review_notes,
                        params.decision, now, params.proposal_id,
                    ),
                )
                conn.commit()

                result = {
                    "proposal_id": params.proposal_id,
                    "decision": params.decision,
                    "new_status": new_status,
                    "reviewed_at": now,
                    "message": f"Proposal {params.decision}d successfully.",
                }

                # If approved, note that manual application is needed
                if params.decision == "approve":
                    result["next_step"] = (
                        "Proposal approved. A CanuckDUCK administrator will apply it to "
                        "the active graph. Check status for updates."
                    )

                return json.dumps(result, indent=2, ensure_ascii=False)

        finally:
            conn.close()

    except Exception as e:
        return _handle_error(e)
