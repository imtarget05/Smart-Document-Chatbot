# ADR 0003: Agent Fallback Strategy

Status: Accepted

## Context

The supply-chain agentic path (chain #4, see ADR 0002) diverges eligible queries
to the Python agent service (`AgentClient` → `POST /v1/agent/invoke`). That
service is **experimental**: its LangGraph workflow (`graph/workflow.py`) may be
unavailable, return an ADK-demo fallback, throw on the internal network, or exceed
`agent.timeout-ms`. The core chat product (CRAG over PostgreSQL) is
production-hardened and must never regress because of an experimental dependency.

We need an explicit, observable degradation policy so that:

- A user asking a supply-chain question always gets a useful answer, even if the
  agent is down — never a 5xx or an empty response.
- The fallback is deterministic and unit-tested, not an ad-hoc catch block.
- Operations can tell when fallbacks are happening (silent degradation is worse
  than a loud one).

## Decision

The fallback policy is **best-effort agent, hard RAG floor**, applied as a
layered guard in `ChatService.processQuery` (and mirrored in the streaming path):

1. **Agent invocation is wrapped in try/catch.** Any exception from
   `AgentClient.invokeAgent` (connection refused, 4xx/5xx, timeout, JSON parse
   error) is caught; the query is logged with `"Agentic path failed, falling back
   to RAG"` and control continues to the normal CRAG branch. The user is never
   shown the error — they get a RAG answer.
2. **No circuit breaker on the agent call.** Deliberately omitted: the agent is
   called only for the small fraction of queries that are supply-chain intent
   (see ADR 0002), so a transient agent outage does not create a thundering-herd
   retry storm. A breaker would add latency to the critical chat path for little
   gain at this traffic level. (Revisit if agent traffic exceeds ~10% of queries.)
3. **RAG itself has its own floors** (independent of the agent):
   - `no_evidence` from CRAG → safe abstention response, `chat.abstentions`
     metric incremented.
   - Prompt-injection detected → blocked response, `chat.injection.blocked`
     metric incremented.
   - Web search (Tavily) is the last CRAG resort and is also best-effort
     (failure falls back to lexical-only answer).
4. **Observability of fallback.** Every agent fallback records
   `ragMetrics.recordRequest("agentic", ...)` then continues into the RAG path,
   so dashboards can surface the ratio `agentic_attempts : agentic_fallback`.
   `AgentClientTest` locks both the success path (full response mapped) and the
   failure path (RuntimeException → RAG fallback).

## Alternatives Considered

- **Fail fast / return 503 on agent error.** Rejected: would turn an
  experimental dependency into a user-visible outage for supply-chain queries.
- **Resilience4j circuit breaker around `AgentClient`.** Rejected for now (see
  point 2): adds complexity and latency to the hot path; the low call volume does
  not justify it. The `resilience4j` dependency is already present for the LLM
  client and can be extended here later if needed.
- **Async agent with queue / out-of-band enrichment.** Rejected: the chat
  endpoints are synchronous request/response; introducing a queue would change
  the contract and complicate the SSE stream. Out-of-band enrichment is a future
  enhancement, not a fallback.
- **Always call the agent, cache RAG answer as backup.** Rejected: doubles
  latency/cost on every supply-chain query.

## Consequences

- Supply-chain queries are answered even when the agent is fully down — the
  product degrades gracefully, not loudly.
- The fallback is silent to the user by design; the *only* signal is in metrics
  and logs. Ops must alert on a rising `agentic_fallback` rate rather than on
  errors.
- `AgentClient` persistence of `agent_state` is best-effort (DB errors
  swallowed) so the fallback path cannot itself throw.
- Cost: an agent outage is invisible to users but burns a CRAG pass per affected
  query — acceptable trade-off for availability.
- If the agent is permanently mis-wired (wrong `agent.base-url`), every
  supply-chain query silently becomes a RAG query. `AgentClientTest` guards the
  URL/field contract, but runtime misconfig still needs metric alerting.
