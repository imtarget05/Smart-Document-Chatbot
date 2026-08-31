# Test plan — top_p (nucleus) sampling

Feature: every LLM call now carries a configurable `top_p` (env `LLM_TOP_P`, default `0.95`)
end-to-end, so output randomness is tunable without code changes.

## Coverage matrix

| Layer | What is verified | Automated by |
|---|---|---|
| Java config | default `topP == 0.95`, LLM_TOP_P binding | `LlmConfigTest.defaultsAreSensible` |
| Java sync call | request body `options.top_p` sent to router | `LlmClientTest.chatSendsTopPSamplingInOptions` |
| Java streaming | same options shape on the stream payload | same options builder (`MessageHandler.buildChatRequest`) |
| Router local provider | defaults 0.95 when omitted, keeps override | `llm-router/tests/test_top_p.py` |
| Router cloudflare | forwards top_p/temperature, invents none | `llm-router/tests/test_top_p.py` |
| Full chain (localhost) | HTTP payload -> router -> provider receives 0.95 | `scripts/local_top_p_e2e.py` |

## Commands

```bash
# unit tests only
make test-top-p

# full localhost E2E (mock Ollama + real router app, no cloud creds/DB needed)
make e2e-top-p
```

## What the E2E asserts (10 checks)

1. Backend-shaped `/api/chat` payload returns 200 with an answer.
2. Provider receives `options.top_p == 0.95`, `temperature == 0.3`, `num_predict == 2048`.
3. Request with NO options still gets the router default `top_p == 0.95` (regression guard).
4. Explicit override (`top_p: 0.5`) is forwarded untouched.
5. Streaming (`stream: true`) yields NDJSON tokens and forwards `top_p`.

## Known limitation

The browser UI flow (upload -> chat) is covered by `frontend/e2e/fullstack-smoke.spec.ts`,
which needs a live backend + LLM provider. The E2E here proves the sampling-parameter chain
without that infra; set `E2E_API_URL` to run the UI-level smoke against a stack that is up.
