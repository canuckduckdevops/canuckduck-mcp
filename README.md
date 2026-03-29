# CanuckDUCK RIPPLE MCP Server

**Canadian policy intelligence for AI assistants.**

Connect your AI tool to `mcp.canuckduck.ca` and query a validated Canadian policy causal knowledge graph with 1,334 variables, 4,826 causal relationships, 46 constitutional doctrines, 165 landmark court cases, 114 federal organizations, and live Canadian government data feeds. 112 variables grounded with authoritative baselines from Statistics Canada, Bank of Canada, PBO, CIHI, and ECCC.

## Quick Start

### Claude.ai
Settings → Integrations → Add MCP Server
- URL: `https://mcp.canuckduck.ca/mcp`
- Header: `Authorization: Bearer YOUR_API_KEY`

### Claude Code / VS Code
```json
{
  "mcpServers": {
    "canuckduck": {
      "type": "streamable-http",
      "url": "https://mcp.canuckduck.ca/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

### Cursor / Windsurf / Other MCP Clients
- URL: `https://mcp.canuckduck.ca/mcp`
- Transport: Streamable HTTP
- Auth: `Authorization: Bearer YOUR_API_KEY`

## Get an API Key

1. Register at [store.canuckduck.ca](https://store.canuckduck.ca)
2. Subscribe to a plan that includes API access
3. Your key is auto-provisioned on checkout
4. View your key at [nest.canuckduck.ca/nest/api-keys](https://nest.canuckduck.ca/nest/api-keys)

## Available Tools (16)

### Public (no key required)
| Tool | Description |
|---|---|
| `canuckduck_search` | Search 1,334 Canadian policy variables by keyword. Use first to find variable IDs for graph traversal. |
| `canuckduck_stats` | Graph summary statistics: variables, edges, organizations, cases, constitutional doctrines. Use to ground responses about graph scope. |
| `canuckduck_geo_lookup` | Look up any Canadian postal code or FSA code. Returns community name, city, province, and coordinates. Example: 'T2P 3H5' returns 'Downtown Commercial Core, Calgary, AB'. |
| `canuckduck_geo_stats` | Geographic data coverage: FSA codes, municipalities, federal ridings, postal codes, communities. |

### Registered (free API key)
| Tool | Description |
|---|---|
| `canuckduck_forward` | Trace what a policy variable CAUSES downstream. Use to answer: 'If we change X, what else changes?' |
| `canuckduck_backward` | Trace what CAUSES a policy variable upstream. Use to answer: 'Why is X happening?' or 'What drives X?' |
| `canuckduck_paths` | Find all causal paths connecting two policy variables. Use to answer: 'How is X connected to Y?' |
| `canuckduck_impact` | Full causal impact radius — all downstream and upstream relationships scored by influence weight. |
| `canuckduck_evidence` | Source evidence and CanLII case citations supporting a causal relationship. Use when sourcing is needed. |
| `canuckduck_news` | Canadian news articles from government and media RSS feeds, filtered by policy topic. |
| `canuckduck_geo_variables` | Find RIPPLE variables scoped to a specific Canadian province. Returns provincial + national variables. |
| `canuckduck_local_impact` | Run a policy scenario and localize impacts to a specific community. Answers: 'What does this mean for MY community?' |

### Professional (paid key)
| Tool | Description |
|---|---|
| `canuckduck_constitutional` | Explore 46 Canadian constitutional doctrines with connected policy variables. Covers Charter rights, division of powers, Duty to Consult. |
| `canuckduck_root_trace` | Trace a variable to constitutional roots with CanLII case citations and legal precedents. |
| `canuckduck_cda_profile` | Constitutional Divergence Analysis profile: pressure scores, Charter divergence, linked legal precedents. |
| `canuckduck_simulate` | Multi-variable policy scenario simulation with projected values, constitutional warnings, and geographic context. |

## Data Sources

- **RIPPLE Causal Graph** — 1,334 variables, 5,130+ causal edges, continuously improved by adversarial Mistral+Gemini audit pipeline
- **Constitutional Layer** — 46 doctrines, 4,006 CONSTRAINS edges (80% variable coverage), mapped via the A.B.E. Constitutional Authority Framework
- **CanLII** — 165 landmark Canadian court cases with SCC/JCPC citations and CanLII URLs
- **Canadian Data Vault** — Live feeds from Statistics Canada, Bank of Canada, IRCC, ECCC, PBO, CIHI
- **Federal Organizations** — 114 departments/agencies with TBS 2025-26 Main Estimates budget data
- **Geospatial** — 1,651 FSA centroids, 5,161 municipalities, 338 federal ridings, 29,638 postal codes, 244 Calgary communities with PostGIS boundaries

## Example Queries

**Search for housing variables:**
> "Search the CanuckDUCK graph for variables related to housing affordability"

**Trace defence spending impact:**
> "What are the downstream effects of Defence Spending in the RIPPLE graph?"

**Constitutional analysis:**
> "What constitutional constraints apply to healthcare spending in Canada?"

## Attribution

Case citations sourced from [CanLII](https://www.canlii.org) (canlii.org). Decisions are Crown copyright.

Live data from Statistics Canada, Bank of Canada, and other Government of Canada sources.

## About

Built by [CanuckDUCK Research Corporation](https://canuckduck.ca). The RIPPLE causal graph is a validated Canadian policy knowledge base created through adversarial AI stress testing and community-sourced evidence extraction.

- **Nest Policy Workbench**: [nest.canuckduck.ca](https://nest.canuckduck.ca)
- **MCP Endpoint**: [mcp.canuckduck.ca/mcp](https://mcp.canuckduck.ca/mcp)
- **Documentation**: [nest.canuckduck.ca/nest/docs/mcp](https://nest.canuckduck.ca/nest/docs/mcp)

## License

Server code: MIT License. Data accessed through the MCP is subject to CanuckDUCK Research Corporation terms of service.
