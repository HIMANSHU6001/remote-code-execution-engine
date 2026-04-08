# RCE Online Judge API

This project uses Fern with OpenAPI as the source of truth for HTTP APIs.

## What is documented

- Authentication endpoints
- Problem fetch endpoint
- Submission lifecycle endpoints
- Health probes

## Important note about WebSocket

Real-time updates use `WS /ws/{job_id}` and are intentionally documented in prose (README) rather than OpenAPI.

Use this flow in clients:

1. `POST /submit`
2. Poll `GET /submissions/{job_id}`
3. Optionally open `WS /ws/{job_id}?token=<jwt>` for push updates
