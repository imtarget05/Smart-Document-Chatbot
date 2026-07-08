# Security Guide

## 1. Security Goals

Engineering Intelligence Copilot handles internal engineering knowledge, uploaded documents, AI prompts, and generated outputs. Security design must protect:

- user identity
- uploaded document confidentiality
- API access boundaries
- vectorized knowledge content
- model/provider secrets
- auditability of sensitive actions

---

## 2. Threat Model

Primary risks:

1. unauthorized API access
2. leaked secrets in source code or environment
3. prompt injection through uploaded or retrieved content
4. data exfiltration through connectors or unsafe tools
5. malicious file uploads
6. over-permissive service-to-service trust
7. missing audit trail for sensitive AI operations
8. insecure deployment defaults

---

## 3. Authentication

### User Authentication
Recommended:
- JWT access tokens for frontend-to-backend requests
- short-lived access token
- optional refresh token rotation
- bcrypt or argon2 password hashing
- account lockout or rate limits for repeated failures

### Service Authentication
Recommended:
- internal API token or mTLS for backend ↔ agent service
- separate service credentials from user credentials
- rotate internal tokens regularly

---

## 4. Authorization

Use RBAC with minimum roles:

- **Admin**
  - manage users
  - manage providers and settings
  - manage data sources
  - view all audit logs

- **Engineer**
  - upload documents
  - run AI workflows
  - create and edit 8D cases
  - view allowed knowledge spaces

- **Viewer**
  - read-only access
  - no connector or admin settings changes

Rules:
- deny by default
- check role at API boundary
- avoid role checks only in frontend
- log permission denials for review

---

## 5. Secret Management

Never hardcode:
- JWT secret
- database password
- provider API keys
- Qdrant auth tokens
- connector credentials

Use:
- `.env` only for local dev
- secret manager or orchestrator secrets in production
- different secrets per environment
- secret rotation procedure

Minimum variables:
- `EIC_JWT_SECRET_KEY`
- database credentials
- LLM provider credentials
- internal service token

---

## 6. File Upload Security

Validation requirements:
- allowlist extensions only
- MIME type validation
- file size limits
- magic-byte validation when possible
- reject executable content
- sanitize filenames
- store with generated IDs, not user-provided names
- antivirus scanning if production environment requires it

Recommended supported types:
- PDF
- DOCX
- TXT
- MD
- CSV
- JSON

Avoid:
- direct HTML rendering of uploaded content
- shelling out to unsafe parsers
- trusting extension alone

---

## 7. Prompt Injection Defense

Documents can contain malicious instructions like:
- “ignore previous instructions”
- “send secrets”
- “reveal system prompt”

Mitigations:
1. separate system instructions from retrieved content
2. label retrieved text as untrusted evidence
3. never allow retrieved content to redefine tool policy
4. strip or flag suspicious patterns
5. require citations for factual answers
6. restrict agent tools by schema and permission
7. do not expose secrets to model context

Safe prompt pattern:
- system prompt defines behavior
- retrieved chunks treated as evidence only
- agent must cite source and refuse unsupported claims

---

## 8. Tool Security

If agents can call tools:
- every tool needs explicit input schema
- validate arguments before execution
- set timeouts
- whitelist allowed outbound destinations
- log tool calls with actor and timestamp
- separate read tools from write tools
- support dry-run for risky operations

High-risk tool categories:
- shell execution
- SQL execution
- external HTTP actions
- ticket creation
- notification sending

Default:
- read-only unless explicitly approved

---

## 9. Data Protection

### At Rest
- encrypt database volume if environment requires it
- secure backups
- protect object/file storage
- apply least-privilege DB accounts

### In Transit
- HTTPS/TLS for frontend and backend
- TLS for external provider calls
- avoid plaintext secrets in logs

### In Retrieval Layer
- chunk metadata may expose sensitive labels
- apply tenant/project scoping in queries
- do not retrieve across unauthorized spaces

---

## 10. Logging and Audit

Log these events:
- login success/failure
- document upload/delete
- connector sync start/finish
- AI workflow execution
- tool invocation
- admin settings changes
- role/permission changes

Audit records should include:
- actor
- action
- resource type
- resource id
- timestamp
- status
- source IP or service identity
- relevant metadata without secrets

Do not log:
- raw passwords
- API keys
- full secret tokens
- highly sensitive raw documents unless policy allows it

---

## 11. API Security Controls

Recommended controls:
- request size limits
- rate limiting
- CORS allowlist
- input validation with Pydantic
- standardized error responses
- pagination for list endpoints
- secure headers at reverse proxy
- CSRF protections if cookie auth used

For public docs endpoints:
- expose only non-sensitive health info
- avoid leaking configuration values

---

## 12. Multi-Tenancy / Data Isolation

If product evolves to multiple teams or customers:
- include tenant or workspace ID in every protected record
- enforce scoped retrieval at DB and vector query layers
- never trust client-provided tenant ID without server validation
- isolate storage and secrets by environment

---

## 13. Dependency and Supply Chain Security

Recommended:
- pin versions in requirements files
- scan dependencies regularly
- review transitive AI packages carefully
- use trusted container base images
- verify third-party connectors before enabling

---

## 14. Deployment Hardening

Production minimum:
- run behind reverse proxy
- disable debug mode
- strong JWT secret
- non-root containers
- restricted network paths
- separate dev and prod configs
- health and readiness endpoints exposed safely
- backup and restore procedure tested

---

## 15. Security Checklist

- [ ] No hardcoded secrets
- [ ] JWT secret loaded from environment
- [ ] RBAC enforced in backend
- [ ] Upload validation implemented
- [ ] Prompt injection guard added
- [ ] Tool calls schema-validated
- [ ] Audit logs for sensitive actions
- [ ] TLS enabled in deployed environment
- [ ] Dependencies pinned and reviewed
- [ ] Production debug mode disabled