# Architecture Roadmap

## Objective

Evolve the tool from local, single-user execution into a secure, shared, enterprise-ready mapping platform with reusable connection profiles, metadata discovery, and AI-assisted mapping acceleration.

## Current Baseline (Today)

- FastAPI-based web app
- Local/VM runtime with UI + API
- Multi-source/target mapping (Salesforce, MSSQL, MySQL, Redshift)
- Connector test endpoints
- Parameter-based datasource creation flow in admin UI
- Dynamic datasource discovery (databases, schemas, tables)
- Schema-aware mapping workspace selectors (source and target)
- Live dashboard and mapping history driven by persisted mapping run data
- Excel export + Desktop copy
- Basic logging with masked passwords/tokens

---

## Phase 1: Shared Hosted Access (EC2/VM)

### Goal

Provide one URL that users can open directly without local setup on each machine.

### Scope

- Deploy app to EC2/VM
- Add reverse proxy (Nginx) and HTTPS
- Run app with service manager (`systemd`/`supervisor`)
- Add health/version endpoint checks into monitoring

### Deliverables

- Internal URL for tool access
- Deployment runbook
- Basic uptime monitoring + logs

### Risks

- Open network access if security groups/firewall are loose
- Drift between deployed config and local config

### Success metrics

- >95% of target users can access via URL
- No local install required for regular usage
- Stable uptime during business hours

---

## Phase 2: One-Time Connection Profiles + RBAC

### Goal

Move from per-run credential entry to reusable, governed connection profiles.

### Scope

- Admin-managed connection profiles (source/target)
- Secrets in vault (AWS Secrets Manager/Vault), not plaintext DB
- Role-based profile visibility (who can use which profiles)
- Audit logs for profile usage and secret reads

### Deliverables

- Profile management data model + admin APIs
- RBAC enforcement in backend + UI filtering
- Security policy and rotation process for secrets

### Risks

- Secret leakage if references and permissions are misconfigured
- Over-broad profile permissions across teams

### Success metrics

- >80% reduction in manual credential re-entry
- Auditable access trail for profile usage
- Zero plaintext credential storage in app database

---

## Phase 3: Metadata Discovery + Dropdown UX (Delivered)

### Goal

Let users select databases/schemas/tables from discovered metadata instead of typing names manually.

### Scope

- Endpoints to list databases/schemas/tables by selected datasource
- UI dropdowns for source/target datasource, database, schema, and object/table selection
- Caching strategy for metadata browsing performance

### Deliverables

- Discovery APIs (`/api/datasources/{id}/databases`, `/schemas`, `/tables`)
- Dynamic UI selectors with search/filter
- Error handling for permissions/metadata access failures

### Risks

- Slow metadata listing on large databases
- Inconsistent privilege models across systems

### Success metrics

- Lower data-entry errors in source/target selection
- Faster mapping setup time per request

---

## Phase 4: Multi-Table Batch Mapping

### Goal

Generate mappings for multiple table/object pairs in one run.

### Scope

- Multi-select table/object UX
- Batch job execution for multiple pairs
- Consolidated output (workbook tabs or zipped files)

### Deliverables

- Batch mapping API contract
- Progress/status feedback in UI
- Output packaging strategy

### Risks

- Long-running requests/timeouts
- Output file size and memory usage growth

### Success metrics

- Batch throughput improvement vs single-table runs
- Reduced manual repetition for integration teams

---

## Phase 5: AI-Enhanced Mapping Suggestions

### Goal

Improve non-exact name/type matching confidence using ETL patterns and semantic similarity.

### Scope

- Suggest transformations and candidate target columns
- Confidence scoring + explanation in output
- Human review workflow for suggested matches

### Deliverables

- AI suggestion engine interface
- Explainable suggestion notes in mapping output
- Evaluation framework (precision/recall feedback loop)

### Risks

- False positives in automated suggestions
- Governance concerns for opaque recommendations

### Success metrics

- Higher accepted-match rate on non-exact column names
- Reduced manual remediation effort

---

## Cross-Phase Non-Functional Requirements

- Security: SSO/OIDC, RBAC, secrets manager, encrypted transport
- Observability: structured logs, metrics, alerting, traceability
- Reliability: retries, timeout controls, graceful error handling
- Performance: metadata caching, pagination, batch orchestration
- Governance: audit logs, approval workflows, change history

---

## Suggested Delivery Sequence

1. Phase 1 (Hosted URL)
2. Phase 2 (Profiles + RBAC + Secrets)
3. Phase 3 (Dropdown discovery)
4. Phase 4 (Multi-table batch)
5. Phase 5 (AI suggestions)

This sequence minimizes risk and gives immediate user value at each step.
