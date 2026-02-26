# Go-Live Checklist and Sign-Off Template

## A) Security Readiness

- [ ] SSO/IdP integration validated in UAT
- [ ] MFA policy applied for admin access
- [ ] Secrets manager integration completed
- [ ] No plaintext credentials in deployment configs
- [ ] Vulnerability scan completed and reviewed
- [ ] Audit logging and export validated

## B) Infrastructure Readiness

- [ ] Production host(s) provisioned and hardened
- [ ] Reverse proxy/load balancer configured with HTTPS
- [ ] DNS entry published for single URL
- [ ] Firewall allowlists approved (inbound/outbound)
- [ ] Health checks and alerting integrated
- [ ] Backup and restore test completed

## C) Application Readiness

- [ ] Initial admin bootstrap tested
- [ ] User lifecycle workflows tested (create/update/reset/delete)
- [ ] Session revocation behavior verified on role change
- [ ] Datasource onboarding and test workflow validated
- [ ] Mapping generation and export validated
- [ ] Audit filter/date-range/export behavior validated

## D) Operational Readiness

- [ ] L1/L2/L3 support ownership confirmed
- [ ] Incident runbooks approved
- [ ] Escalation contacts and on-call matrix published
- [ ] Monitoring dashboard access shared with owners
- [ ] Rollback plan validated

## E) User Readiness

- [ ] Admin training completed
- [ ] End-user training completed
- [ ] User guide and FAQ published
- [ ] Pilot users signed off

## F) Cutover Plan

- [ ] Go-live date/time approved
- [ ] Change window approved
- [ ] Pre-cutover health check passed
- [ ] Post-cutover smoke tests passed
- [ ] Hypercare window activated

## G) Sign-Off

| Team | Name | Role | Decision (Approve/Conditional/Reject) | Date | Notes |
|---|---|---|---|---|---|
| Security |  |  |  |  |  |
| Infrastructure |  |  |  |  |  |
| Application Owner |  |  |  |  |  |
| Supervisor / Sponsor |  |  |  |  |  |

## H) Post Go-Live Review (2-4 weeks)

- [ ] Incident count and severity reviewed
- [ ] User adoption metrics reviewed
- [ ] Performance and capacity reviewed
- [ ] Open risks re-assessed
- [ ] Next-phase roadmap approved
