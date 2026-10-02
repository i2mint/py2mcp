# Prior art for per-call usage logging on an MCP server (2026-10-02)

Research for [i2mint/py2mcp#20](https://github.com/i2mint/py2mcp/issues/20); the decision it informed is [ADR-0001](../decisions/0001-usage-logging-is-a-py2mcp-middleware.md). Standard depth: in-house layers first, then the web, one agent.

## Summary and recommendation

Nothing that exists records what a connector owner actually asks about, with the privacy posture a client-facing connector needs, at zero new dependencies. FastMCP's own logging middleware has no caller and no outcome [1]. The OpenTelemetry MCP conventions, which FastMCP emits natively, are still at *Development* stability, treat arguments and results as opt-in, and define no caller attribute at all; emitting them requires an SDK, an exporter and a backend [2][3][4]. The MCP-specific observability SDKs are permissively licensed but are front doors to hosted analytics or OTLP pipelines [5][6][7][8]. The in-house `enlace_metering` is a cost gate, not a usage log [9]. Two 2026 CVEs show the failure mode to design against: arguments logged in full, unredacted, to a file with no rotation [10][11].

**Recommendation (adopted):** a small FastMCP middleware in py2mcp with a callable sink, a JSON-lines-per-day default sink with retention, redaction before the record exists, and a reader; enablement by host configuration. Keep an OTLP sink as a known next step at the sink seam, and keep hosted vendors as a decision for the user, since they would receive the users' questions.

## What already existed in-house

- **py2mcp** threads `middleware=` through every builder (`mk_mcp_server`, `mk_mcp_from_refs`, `mk_mcp_from_store`, `mk_http_app`, `serve_http`, `serve_stdio`), with the explicit intent "usage metering, cost logging, audit" (issue #6). The OAuth layer runs before middleware, so a middleware can read the verified token via `fastmcp.server.dependencies.get_access_token()`.
- **FastMCP 3.4** (Apache-2.0, already a dependency) ships `fastmcp.server.middleware.logging.LoggingMiddleware` and `StructuredLoggingMiddleware` [1]: they log `event`, `method`, `source`, `duration_ms` and optionally the request payload (length or text, capped) to a Python `logging.Logger`. No caller identity, no result size, no outcome classification, no sink other than `logging`. `TimingMiddleware` / `DetailedTimingMiddleware` log durations only. FastMCP also has a `telemetry` module that emits OpenTelemetry spans using only `opentelemetry-api` (a no-op until an SDK is configured) [3].
- **enlace_metering** (i2mint, public, no runtime deps; `[mcp]` extra for the middleware) [9]: `MeteringMiddleware` resolves identity from the token (`email`, else `sub`), authorizes against an allowlist (deny-by-default), gates on a policy, and writes a write-ahead ledger row (`started` → `done`/`error`) keyed `{principal}/{YYYY-MM}/{id}.json` into any `MutableMapping`. It refuses the call if the ledger write fails. It records tool, principal, status, elapsed time and cost; it does not record arguments, result size or a "no match" outcome, and its deny-by-default is the wrong shape for a connector that relies on the platform allowlist alone. Its `token_email()` is the identity recipe reused here.
- **braidio's** earlier `MeteringMiddleware` is the ancestor of enlace_metering (recording only).
- **Platform convention** (tw_platform, private): connector data lives under the connector's own data root off the deploy tree, set through `Environment=` lines in the systemd unit; the reelee connector's metering ledger is a `dol` file store there.
- Past research across the fleet (`ir discover reports`) covered MCP server design and schema tooling but not usage logging; the rubricator MCP note records that MCP's own server-to-client logging (`notifications/message`) is deprecated in favour of stderr and OpenTelemetry, so it is not a vehicle for this.

## External prior art

### OpenTelemetry semantic conventions for MCP and GenAI

The MCP conventions [2] (now maintained in the `semantic-conventions-genai` repository) are **Development** status. Required: `mcp.method.name`. Conditionally required: `error.type`, `gen_ai.tool.name`, `gen_ai.prompt.name`, `jsonrpc.request.id`, `mcp.resource.uri`, `rpc.response.status_code`. Recommended: `gen_ai.operation.name = execute_tool`, `mcp.session.id`, `mcp.protocol.version`, `network.*`, `client.address`/`server.address`. **Opt-in** because they "may contain sensitive information": `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`. Metrics: `mcp.server.operation.duration`, `mcp.server.session.duration` (and client counterparts). **No caller, user or principal attribute is defined.** The GenAI conventions' stable attributes date from v1.37; agent and tool-orchestration parts still change often [4].

Verdict: *study* (adopt the names in documentation, keep the record mappable), not *depend*. Emitting spans needs `opentelemetry-sdk` plus an exporter plus something to receive them, and the conventions still lack the one field (caller) the question starts with.

### FastMCP's native tracing

FastMCP creates spans for every `tools/call {name}`, `resources/read {uri}` and `prompts/get {name}` with `mcp.method.name`, `mcp.session.id`, `gen_ai.tool.name`, `fastmcp.server.name`, `fastmcp.component.type`; all no-ops without an SDK; arguments and results are not attached by default [3]. The documented setup is `opentelemetry-distro` + `opentelemetry-exporter-otlp` and an OTLP endpoint.

Verdict: *wrap later*. A future OTLP sink for the usage record is the right way to join a tracing pipeline; nothing in FastMCP's tracing records the caller or an outcome.

### MCP observability SDKs and products

| Project | Licence | Shape | Caller | Arguments | Verdict |
|---|---|---|---|---|---|
| MCPcat / AgentCat Python SDK [5] | MIT | Hosted analytics by default; also OTLP / Datadog / Sentry exporters; `identify` callback returns a user id; `redact_sensitive_information` and `redact_event` hooks | yes, via callback | yes, plus the agent's stated context | *avoid* as default (data leaves the host); the `identify` + `redact_event` shape is the pattern worth copying |
| Shinzo (`shinzo` on PyPI) [6] | MIT | OpenTelemetry-compatible instrumentation, Shinzo Labs backend | via OTel | via OTel | *study* |
| Heimdall (`hmdl`) [7] | MIT | OTel-based SDK for MCP servers | via OTel | via OTel | *study* |
| Traceloop `opentelemetry-instrumentation-mcp` (OpenLLMetry) [8] | Apache-2.0 | Instruments the official MCP Python SDK; logs prompts/completions to span attributes by default, `TRACELOOP_TRACE_CONTENT=false` disables | no | yes by default | *avoid* for a client-facing connector; the opt-out-not-opt-in default is the wrong way round |
| `listo-mcp-observability` [12] | — | Lightweight SDK with payload sanitization | — | yes, sanitized | *study* |

The common denominator across them: an OTLP or vendor pipeline, and identity supplied by a host callback because the standard has no field for it. None gives a connector owner a file they can read with `python -m json.tool` the next morning.

### Privacy and retention

Two 2026 disclosures are the concrete argument for the defaults chosen. n8n-MCP (CVE-2026-42282) wrote full `tools/call` arguments to server logs before any redaction, exposing bearer tokens and API keys embedded in arguments wherever logs were forwarded or shared [10]. dbt-MCP (CVE-2026-44969) logged the raw arguments dict at INFO level (and again on error) to a plaintext file in the project directory with no rotation or deletion [11]. The lessons map one-to-one onto the design: redact before the record exists, cap sizes, never log results in full, write outside the app directory, keep a retention period, and make logging an explicit per-connector switch.

## What this leaves open

- An OTLP sink (records → spans with the attribute mapping above) at the `sink` seam, if a tracing backend is ever wanted.
- A hosted vendor (MCPcat et al.): a user decision, because it ships the users' questions off the host.
- Connector-specific outcome classifiers (a search tool's own "no match" shape) at the `outcome` seam, in each connector.

## REFERENCES

1. FastMCP source, `fastmcp/server/middleware/logging.py` and `timing.py`, version 3.4.7 (installed; Apache-2.0). [github.com/jlowin/fastmcp](https://github.com/jlowin/fastmcp)
2. OpenTelemetry. *Semantic conventions for Model Context Protocol (MCP)*, Development status. [github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/mcp.md](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/mcp.md) (moved from [opentelemetry.io/docs/specs/semconv/gen-ai/mcp](https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/))
3. FastMCP docs. *Telemetry* (OpenTelemetry tracing). [gofastmcp.com/v3/servers/telemetry](https://gofastmcp.com/v3/servers/telemetry)
4. Dash0. *OpenTelemetry GenAI semantic conventions explained* (2026). [dash0.com/knowledge/opentelemetry-genai-semantic-conventions-explained](https://www.dash0.com/knowledge/opentelemetry-genai-semantic-conventions-explained)
5. MCPcat. *mcpcat-python-sdk* (MIT). [github.com/mcpcat/mcpcat-python-sdk](https://github.com/mcpcat/mcpcat-python-sdk)
6. Shinzo Labs. *shinzo* on PyPI (MIT). [pypi.org/project/shinzo](https://pypi.org/project/shinzo)
7. Heimdall. *hmdl* on PyPI (MIT). [pypi.org/project/hmdl](https://pypi.org/project/hmdl/)
8. Traceloop. *opentelemetry-instrumentation-mcp* 0.60.0 (Apache-2.0, OpenLLMetry). [simple-repository.app.cern.ch/project/opentelemetry-instrumentation-mcp](https://simple-repository.app.cern.ch/project/opentelemetry-instrumentation-mcp)
9. i2mint. *enlace_metering* — usage tracking and credit/quota gating for enlace connectors. [github.com/i2mint/enlace_metering](https://github.com/i2mint/enlace_metering)
10. CVE-2026-42282. *n8n-MCP: sensitive MCP tool-call arguments logged on authenticated requests in HTTP mode.* [corgea.com/advisories/vulnerabilities/CVE-2026-42282](https://corgea.com/advisories/vulnerabilities/CVE-2026-42282)
11. CVE-2026-44969. *dbt-mcp logs raw tool arguments to a plaintext file with no rotation.* [advisories.gitlab.com/pypi/dbt-mcp/CVE-2026-44969](https://advisories.gitlab.com/pypi/dbt-mcp/CVE-2026-44969/)
12. *listo-mcp-observability* 0.3.0 on PyPI. [pypi.org/project/listo-mcp-observability/0.3.0](https://pypi.org/project/listo-mcp-observability/0.3.0/)
13. Glama. *OpenTelemetry for Model Context Protocol: MCP analytics and agent observability* (2025-11-29). [glama.ai/blog/2025-11-29-open-telemetry-for-model-context-protocol-mcp-analytics-and-agent-observability](https://glama.ai/blog/2025-11-29-open-telemetry-for-model-context-protocol-mcp-analytics-and-agent-observability)
