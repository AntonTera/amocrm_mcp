# amoCRM MCP Server

MCP server for [amoCRM](https://www.amocrm.ru/) (Kommo) API v4. Exposes tools for leads, contacts, companies, tasks, notes, pipelines, associations, analytics, and custom fields.

Built with [FastMCP](https://github.com/jlowin/fastmcp). Works with Claude Desktop, Cursor, and any MCP-compatible client.

## Features

- **39 MCP tools** across 11 domains (leads, contacts, companies, tasks, notes, pipelines, associations, account, batch, unsorted, analytics)
- **OAuth 2.0** token refresh with disk persistence
- **Long-lived token mode** for simpler single-account deployments
- **Rate limiting** — 7 req/s with automatic 429 backoff and jitter
- **HAL+JSON normalization** — strips `_links`, flattens `_embedded`
- **Consistent response envelopes** — `{data, pagination}` or `{error, status_code, detail}`
- **stdio, SSE, and streamable-http** transports

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Configure

Copy `.env.example` to `.env` and fill in your amoCRM credentials:

```bash
cp .env.example .env
```

You need at minimum:
- `AMO_SUBDOMAIN` — your amoCRM account subdomain
- `AMO_ACCESS_TOKEN` — OAuth access token

For automatic token refresh, also set:
- `AMO_CLIENT_ID`, `AMO_CLIENT_SECRET`, `AMO_REFRESH_TOKEN`

### 3. Run

```bash
# stdio (default — for Claude Desktop, Cursor, etc.)
python -m amocrm_mcp

# SSE transport
AMO_TRANSPORT=sse AMO_PORT=8000 python -m amocrm_mcp

# Streamable HTTP transport
AMO_TRANSPORT=streamable-http AMO_PORT=8000 python -m amocrm_mcp
```

### Claude Desktop config

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "amocrm": {
      "command": "python",
      "args": ["-m", "amocrm_mcp"],
      "env": {
        "AMO_SUBDOMAIN": "your-subdomain",
        "AMO_ACCESS_TOKEN": "your-token"
      }
      }
    }
}
```

## Vercel Deployment

Current production deployment for `helloevospru`:

- MCP endpoint: `https://amocrm-mcp-helloevospru.vercel.app/mcp`
- Healthcheck: `https://amocrm-mcp-helloevospru.vercel.app/healthz`

This repository is set up for the simplest multi-account operating model:

- **one Vercel project = one amoCRM account**
- store amoCRM credentials in Vercel project environment variables
- connect Codex to the project-specific `/mcp` URL

### Deploy a new amoCRM account

1. Create a new Vercel project from this repository.
2. Add production environment variables:
   - `AMO_SUBDOMAIN=<your amoCRM subdomain>`
   - `AMO_ACCESS_TOKEN=<your long-lived token>`
   - leave `AMO_CLIENT_ID`, `AMO_CLIENT_SECRET`, and `AMO_REFRESH_TOKEN` empty if you use long-lived token mode
3. Deploy to production:

```bash
npx vercel link --project <new-project-name>
npx vercel env add AMO_SUBDOMAIN production --value <subdomain>
npx vercel env add AMO_ACCESS_TOKEN production --value <long-lived-token>
npx vercel deploy --prod -y
```

4. Use the project URL in Codex:

```toml
[mcp_servers.amocrm_<account_name>]
url = "https://<your-project>.vercel.app/mcp"
```

Recommended naming:

- Vercel project: `amocrm-mcp-<account>`
- Codex server key: `amocrm_<account>`

## Tools

| Domain | Tools | Description |
|--------|-------|-------------|
| **Leads** | `leads_list`, `leads_get`, `leads_search`, `leads_create`, `leads_create_complex`, `leads_update` | Full lead lifecycle |
| **Contacts** | `contacts_get`, `contacts_search`, `contacts_create`, `contacts_update` | Contact management |
| **Companies** | `companies_get`, `companies_search`, `companies_create`, `companies_update` | Company management |
| **Tasks** | `tasks_list`, `tasks_get`, `tasks_create`, `tasks_update` | CRM task operations |
| **Notes** | `notes_list`, `notes_create` | Notes on entities |
| **Pipelines** | `pipelines_list`, `pipelines_get`, `pipelines_list_statuses` | Pipeline & status info |
| **Associations** | `associations_get_linked`, `associations_link_entities` | Entity relationships |
| **Account** | `account_get`, `account_list_users`, `account_list_custom_fields`, `account_create_custom_field`, `account_update_custom_field`, `account_delete_custom_field` | Account metadata and custom field management |
| **Batch** | `batch_create_leads`, `batch_create_contacts`, `batch_update_leads` | Bulk operations |
| **Analytics** | `analytics_get_events`, `analytics_get_pipeline_analytics`, +1 | CRM analytics |
| **Unsorted** | `unsorted_list`, `unsorted_accept`, `unsorted_reject` | Unsorted inbox |

## Getting amoCRM Credentials

1. Go to your amoCRM account → **Settings** → **Integrations**
2. Create a new integration (or use an existing one)
3. Copy the **access token**, **client ID**, and **client secret**
4. Your subdomain is the part before `.amocrm.ru` in your account URL

## License

MIT
