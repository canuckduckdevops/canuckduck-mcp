# CanuckDUCK RIPPLE MCP Server

**Canadian policy intelligence for AI assistants.**

Connect your AI tool to `mcp.canuckduck.ca` and query a validated Canadian policy causal knowledge graph with 1,328 variables, 4,637 causal relationships, 46 constitutional doctrines, 165 landmark court cases, and live Canadian government data feeds.

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

## Available Tools (11)

### Public (no key required)
| Tool | Description |
|---|---|
| `canuckduck_search` | Search 1,328 policy variables by keyword |
| `canuckduck_stats` | Graph summary — variables, edges, organizations, cases |

### Registered (free API key)
| Tool | Description |
|---|---|
| `canuckduck_forward` | Trace downstream causal effects of a variable |
| `canuckduck_backward` | Trace upstream causes of a variable |
| `canuckduck_paths` | Find all causal paths between two variables |
| `canuckduck_impact` | Full impact radius analysis |
| `canuckduck_evidence` | Source evidence and government citations |
| `canuckduck_news` | Canadian news articles related to a variable |

### Professional (paid key)
| Tool | Description |
|---|---|
| `canuckduck_constitutional` | Explore 46 Canadian constitutional doctrines |
| `canuckduck_root_trace` | Trace a variable to constitutional roots with CanLII case citations |
| `canuckduck_cda_profile` | Constitutional Divergence Analysis for policy topics |

## Data Sources

- **RIPPLE Causal Graph** — 1,328 variables, 4,637 causal edges extracted from 27,000+ community observations and 18,000+ news articles
- **Constitutional Layer** — 46 doctrines, 1,100+ CONSTRAINS edges, mapped via the A.B.E. Constitutional Authority Framework
- **CanLII** — 165 landmark Canadian court cases with SCC/JCPC citations and CanLII URLs
- **Canadian Data Vault** — Live feeds from Statistics Canada, Bank of Canada, IRCC, ECCC, PBO, CIHI
- **Federal Organizations** — 114 departments/agencies with TBS 2025-26 Main Estimates budget data

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
