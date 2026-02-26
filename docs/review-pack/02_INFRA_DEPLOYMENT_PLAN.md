# Infrastructure Deployment Plan

## 1) Target State

Provide a single secure URL for cross-functional users while keeping backend services protected inside college infrastructure.

## 2) Reference Architecture

- User Browser -> `https://mapping.<college-domain>`
- TLS termination at Nginx or internal load balancer
- Reverse proxy routes to FastAPI app service (`127.0.0.1:8101`)
- App service accesses:
  - Managed application DB (users, datasource metadata, audit logs)
  - Secrets manager (credential retrieval)
  - Approved outbound DB servers (MSSQL/MySQL/Redshift/Salesforce endpoints)

## 3) Environment Strategy

- DEV: engineering validation and rapid updates
- UAT: supervised user acceptance with non-production connections
- PROD: controlled and approved datasource onboarding only

Each environment should have:
- separate configuration
- separate credentials
- separate data store
- separate audit logs

## 4) Platform Requirements

- OS: college-approved Linux/Windows server baseline
- Runtime: Python 3.10+ and required ODBC/database drivers
- Service manager: `systemd`/`supervisor`/equivalent
- Reverse proxy: Nginx (or ALB + reverse proxy chain)
- DNS and certificate managed by infra team

## 5) Network and Access Controls

- Public/intranet access only through HTTPS endpoint
- App service port not directly exposed to users
- Egress firewall allowlist for approved DB host:port only
- Admin actions restricted by role and optionally source network segment

## 6) Deployment Steps

1. Provision server(s) and baseline hardening
2. Install runtime dependencies and DB drivers
3. Deploy app artifact and service configuration
4. Configure reverse proxy and TLS certificate
5. Configure environment variables/secrets references
6. Run health checks and smoke tests
7. Execute UAT checklist
8. Production cutover and monitoring handoff

## 7) Monitoring and Observability

- Health endpoint check (`/health/version`)
- Service process uptime and restart metrics
- App logs + audit logs retention
- Alerting:
  - service down
  - high error rate
  - auth failure burst
  - datasource connection failure burst

## 8) Backup and Recovery

- Backup scope:
  - application DB
  - audit log data
  - deployment config (excluding secrets)
- Recovery objectives:
  - define RPO/RTO with infra/security teams
- Recovery validation:
  - scheduled restore drills in UAT

## 9) Suggested Rollout Timeline

- Week 1: infra setup + security control implementation
- Week 2: UAT with pilot users + performance/issue fixes
- Week 3: production go-live and hypercare support
