# AGENTS.md

## Purpose

This repository contains a single-account amoCRM MCP server that can be deployed to Vercel.

Default deployment model:

- one Vercel project = one amoCRM account
- one MCP URL = one amoCRM account
- authentication mode = long-lived token

## Automatic Deployment Playbook

When the user asks to add a new amoCRM client on Vercel, request only these two values:

- `AMO_SUBDOMAIN`
- `AMO_ACCESS_TOKEN`

Do not ask for `AMO_CLIENT_ID`, `AMO_CLIENT_SECRET`, or `AMO_REFRESH_TOKEN` unless the user explicitly wants OAuth refresh flow.

## Assumptions

Unless the user says otherwise, infer everything else from `AMO_SUBDOMAIN`:

- Vercel project name: `amocrm-mcp-<AMO_SUBDOMAIN>`
- Codex MCP server key: `amocrm_<AMO_SUBDOMAIN>`
- MCP URL: `https://amocrm-mcp-<AMO_SUBDOMAIN>.vercel.app/mcp`
- Healthcheck URL: `https://amocrm-mcp-<AMO_SUBDOMAIN>.vercel.app/healthz`

## Required Steps

1. Confirm that the current workspace is this repository:
   - `/Users/antonterentev/Documents/evo.spirit_amocrm/amocrm-mcp`
2. Link the local folder to the target Vercel project:

```bash
npx vercel link --project amocrm-mcp-<AMO_SUBDOMAIN>
```

3. Set production environment variables:

```bash
npx vercel env add AMO_SUBDOMAIN production --value <AMO_SUBDOMAIN> --yes --force
npx vercel env add AMO_ACCESS_TOKEN production --value <AMO_ACCESS_TOKEN> --yes --force
```

4. Deploy to production:

```bash
npx vercel deploy --prod -y
```

5. Return to the user:
   - the production MCP URL
   - the healthcheck URL
   - a ready-to-paste Codex config snippet

## Codex Config Snippet

Use this template in the final response:

```toml
[mcp_servers.amocrm_<AMO_SUBDOMAIN>]
url = "https://amocrm-mcp-<AMO_SUBDOMAIN>.vercel.app/mcp"
```

## Verification Notes

- If `vercel deploy --prod -y` succeeds and the alias is created, consider the deployment complete.
- Do not expose the token in messages.
- Do not rewrite application code for each new client; this flow is configuration-only.
- If a deployment fails because the Vercel project does not exist yet, create it in Vercel first or tell the user that the project must be created from this repository.

## Current Production Example

- `AMO_SUBDOMAIN=helloevospru`
- MCP URL: `https://amocrm-mcp-helloevospru.vercel.app/mcp`
