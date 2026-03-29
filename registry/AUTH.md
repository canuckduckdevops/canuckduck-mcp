# CanuckDUCK MCP Authentication

## Tiers

| Tier | Auth | Tools | Rate Limit | Depth |
|------|------|-------|------------|-------|
| **Public** | None required | canuckduck_search, canuckduck_stats, canuckduck_geo_lookup, canuckduck_geo_stats | 5/day | 1-hop |
| **Registered** | `Authorization: Bearer cduck_r_*` | All public + forward, backward, paths, impact, evidence, news, geo_variables, local_impact | 1,000/day | 2-hop |
| **Professional** | `Authorization: Bearer cduck_p_*` | All registered + constitutional, root_trace, cda_profile, simulate | 10,000/day | 3-hop |

## Getting a Key

1. Register at [store.canuckduck.ca](https://store.canuckduck.ca)
2. Subscribe to a plan with API access
3. Your key is auto-provisioned on checkout
4. View your key at [nest.canuckduck.ca/nest/api-keys](https://nest.canuckduck.ca/nest/api-keys)

## Using Your Key

Add the `Authorization` header to your MCP client config:

```json
{
  "mcpServers": {
    "canuckduck": {
      "url": "https://mcp.canuckduck.ca/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

## Public Tools (No Key Required)

The following tools work without any authentication:
- `canuckduck_search` — Search 1,334 policy variables
- `canuckduck_stats` — Graph summary statistics
- `canuckduck_geo_lookup` — Postal code to community lookup
- `canuckduck_geo_stats` — Geographic coverage statistics

These are designed for AI discoverability. Any AI assistant connected to the MCP server can use them immediately.
