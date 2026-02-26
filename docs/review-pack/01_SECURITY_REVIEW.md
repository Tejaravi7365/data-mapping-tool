# Security Review for College Deployment

## 1) Objective

Assess security readiness for hosting the Data Mapping Tool in a college-managed server environment and define controls required before production use.

## 2) Current Security Baseline

- Session-based login with role checks (`admin`, `user`)
- Password hashing with salted PBKDF2-HMAC-SHA256
- Legacy SHA-256 auto-upgrade on successful login
- Session TTL and secure-cookie behavior under HTTPS
- Admin-only user lifecycle and datasource management APIs
- Session revocation on user disable, password reset, deletion, and role changes
- Audit event capture and filterable audit retrieval/export

## 3) Key Assets to Protect

- Connection credentials and datasource definitions
- User account and role assignments
- Audit logs and admin activity history
- Mapping outputs and metadata intelligence

## 4) Threat Model Summary

- Unauthorized admin actions (privilege abuse or stale sessions)
- Credential leakage from storage or logs
- Excessive network exposure (public internet or flat internal network)
- Weak operational controls (no monitoring, no response runbooks)

## 5) Mandatory Controls Before PROD

1. Identity and Access
   - Integrate SSO/IdP (SAML/OIDC or college-standard auth)
   - Enforce MFA for admin accounts (via IdP)
   - Restrict admin role assignment through approved workflow

2. Secrets and Credential Handling
   - Move datasource credentials to secrets manager
   - Store only secret references in application data store
   - Rotate service credentials on a defined schedule

3. Data and Storage Security
   - Replace local JSON stores with managed DB (users, datasources, audit)
   - Encrypt storage volumes and backups
   - Define retention and archival policy for audit logs

4. Network Security
   - Expose only HTTPS endpoint through reverse proxy/load balancer
   - Keep app process on private interface
   - Restrict DB connectivity by host/port allowlist

5. Application Security
   - Enforce strong password policy for local/bootstrap accounts
   - Add request throttling for login and admin endpoints
   - Add periodic dependency vulnerability scanning

## 6) Recommended Security Operations

- Weekly audit review for admin actions
- Alert on repeated failed logins and repeated datasource test failures
- Quarterly access review (admin/user role certification)
- Quarterly restore test for backup integrity

## 7) Residual Risks (Post Controls)

- Human error during role assignment and datasource onboarding
- Configuration drift between DEV/UAT/PROD
- Outbound dependency/driver compatibility updates

## 8) Security Sign-off Inputs

- Architecture and network diagram approved
- Secrets management design approved
- Penetration/vulnerability report accepted
- Incident response ownership and contact matrix documented
