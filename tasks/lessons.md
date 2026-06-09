# Lessons Learned

## 2026-06-07: Graph service Neo4j connection & API gateway 500

### Graph service Neo4j connection reliability
- Graph service connects to Neo4j once at startup — if it fails, everything cascades: no Kafka consumers, no GraphQL, no startup bulk sync
- **Original fix**: restart graph service manually after Neo4j is running
- **Permanent fix (2026-06-08)**: added exponential backoff retry (1s/2s/4s/8s/16s) in `init_dependencies`, plus a background retry task every 15s that reconnects, starts consumers, and triggers the startup bulk sync once Neo4j becomes available
- `get_neo4j` dependency now reads the module-level `_neo4j_client` directly (not `app.state`), so background reconnection is reflected immediately
- `/ready` endpoint returns 503 when Neo4j is not connected

### PowerShell `-NoNewline` with arrays and `Get-Content` without `-Raw`
- `Set-Content -NoNewline` with an array concatenates items **without any delimiter** (joins them), not just omitting trailing newline
- `Get-Content` (without `-Raw`) returns an array of lines stripping newlines; piping to `Set-Content -NoNewline` flattens the file to one line
- **Fix**: use `Get-Content -Raw` (returns single string), then regex on that string, then `Set-Content -NoNewline` with the single string (preserves existing newlines exactly)

### API gateway `UnboundLocalError` on `/v1/assets`
- `offset` variable was only assigned inside `if cursor:` block but used unconditionally
- Frontend sends page/pagination without cursor → `offset` never initialized → 500
- **Fix**: initialize `offset = 0` at the start and compute from page in the else branch
