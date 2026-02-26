# Risk Register and Mitigation Matrix

## Scoring

- Impact: Low / Medium / High
- Likelihood: Low / Medium / High
- Priority: derived from impact x likelihood

## Risks

| ID | Risk | Impact | Likelihood | Priority | Owner | Mitigation | Contingency |
|---|---|---|---|---|---|---|---|
| R1 | Credentials exposed from insecure storage | High | Medium | High | Security + App Admin | Move credentials to secrets manager, remove plaintext storage | Revoke/rotate credentials immediately |
| R2 | Unauthorized admin access | High | Low | Medium | Security | SSO + MFA + RBAC + admin review process | Disable affected account, audit role changes |
| R3 | Application downtime | High | Medium | High | Infrastructure | Service supervision, health checks, alerting | Failover/restart, temporary maintenance notice |
| R4 | DB connection failures across environments | Medium | High | High | Infra + App Admin | Firewall allowlists, driver baselines, preflight checks | Use fallback datasource or retry after network fix |
| R5 | Audit logs not retained or unavailable | High | Low | Medium | Security + Infra | Centralized log retention and backup policy | Recover from backup; manual incident timeline reconstruction |
| R6 | Configuration drift between DEV/UAT/PROD | Medium | Medium | Medium | Infra | Configuration as code, release checklist | Rollback to previous known-good config |
| R7 | User adoption is low | Medium | Medium | Medium | Product Owner | Role-based training, quick guides, pilot champions | Extended hypercare and process refinement |
| R8 | Performance degradation with concurrent users | Medium | Medium | Medium | Infra + Engineering | Capacity testing, limits, tuning | Scale instance size/count, optimize heavy endpoints |
| R9 | Last-admin lockout scenario | High | Low | Medium | App Admin | Enforced safeguards in user lifecycle APIs | Emergency break-glass admin process |
| R10 | Dependency vulnerability in runtime libraries | High | Medium | High | Security + Engineering | Scheduled dependency scans and patch windows | Emergency patch and redeploy |

## Open Actions Before Go-Live

- [ ] Finalize secrets management design
- [ ] Finalize SSO integration and admin group mapping
- [ ] Complete firewall and routing approvals
- [ ] Define RPO/RTO and backup retention
- [ ] Sign off incident runbooks and escalation contacts
