# SECURITY — Enterprise AI Security & LLM Guardrails Policy

**Smart-Document-Chatbot** is engineered with enterprise cybersecurity standards to prevent data leakage, model manipulation, and unauthorized system access, following the **OWASP Top 10 for Large Language Model Applications**.

---

## 🛡️ 1. OWASP Top 10 for LLMs Compliance Matrix

| OWASP Risk | Threat Vector | System Defense & Mitigation |
| :--- | :--- | :--- |
| **LLM01: Prompt Injection** | Adversarial instructions in uploaded docs or user queries attempting to hijack system prompts. | **Pre-execution sanitization**: Regex & pattern detector identifying jailbreak markers (`ignore previous`, `system override`); isolated user input delimiters; fail-closed rejection. |
| **LLM02: Sensitive Information Disclosure** | Accidental exposure of PII (national IDs, phones, emails) in vector embeddings or LLM completions. | **2-Layer PII Redaction Pipeline**: Ingestion-time masking before vectorization (Qdrant) and output guardrail redaction before streaming to frontend. |
| **LLM04: Model Denial of Service** | Resource exhaustion via massive documents or prompt flooding. | **Fail-closed Rate Limiting** with sliding window counters, chunk limits, and prompt compression (`prompt_compressor.py`). |
| **LLM06: Excessive Agency** | Autonomous agents performing unauthorized state changes or destructive actions. | **Human-In-The-Loop (HITL)**: LangGraph state checkpoints enforce strict human approval via explicit confirmation endpoints before side-effect mutations execute. |
| **LLM08: Vector and Embedding Weaknesses** | Malicious injection of poisoned embeddings into shared spaces. | **Multi-tenant isolation**: Query and retrieval payloads strictly partitioned by `tenant_id` and role-based permissions (RBAC). |
| **LLM09: Misinformation & Hallucination** | LLM generating ungrounded facts or fake citations. | **Corrective RAG (CRAG) + Evidence Gate ($\ge 0.3$)**: Answers strictly require verifiable citations `[S1]`, `[S2]` linked to document offsets; honest refusal if evidence threshold is unmet. |

---

## 🔒 2. Enterprise Infrastructure & Secrets Governance

- **Zero-Secret Commitment**: No API keys, JWT secrets, or connection strings are baked into Docker images or committed to Git.
- **Runtime Injection**: Secrets managed via **Azure Key Vault** / Cloudflare Workers environment variables.
- **Fail-Closed Principle**: Security filters and rate limiters fail-closed—if security checks encounter an anomaly, requests are aborted safely.
- **Audit Logging**: All ingestion, deletion, retrieval, and admin actions are immutably recorded in the `AuditLog` table.

---

## 🔍 3. Automated Vulnerability Scanning

- **Static Analysis (SAST)**: Gitleaks secrets scanning in CI/CD pipeline.
- **Container Security**: Trivy container vulnerability scanner active on every build.
