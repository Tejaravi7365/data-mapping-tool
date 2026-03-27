# What Changed (Users/Admins) - One Pager

This page summarizes the latest capabilities and behavior changes for stakeholder demos and quick reviews.

## For End Users

- You can generate mappings with improved fuzzy matching quality.
- You can run bulk multi-table mapping and download a zip with one Excel file per table pair.
- Mapping history and dashboard metrics are now live from runtime data.
- Audit visibility is available via `Audit Logs` with filters and CSV export.

## For Admins

- First-time bootstrap flow is available (`/setup/initial-admin`) in non-dev environments.
- User lifecycle is fully manageable:
  - create/update/disable/delete users
  - reset passwords
  - enforce safeguards (cannot remove last active admin)
- Sessions are revoked automatically on sensitive account changes (role change, disable, reset password, delete).
- Datasource onboarding supports server-first discovery for MSSQL/MySQL and controlled schema/table selection.

## Security and Governance Improvements

- Password hashing uses salted PBKDF2-HMAC-SHA256.
- Session cookies are HTTP-only with TTL and secure behavior under HTTPS.
- Legacy profile endpoints are admin-protected.
- Batch mapping endpoint now requires authenticated session.
- Persistent audit events are captured for admin and operational actions.

## SSO and Enterprise Alignment

- Admin-managed SSO configuration is available in `Settings` (Okta-style OIDC parameters).
- Backend supports SSO login/callback endpoints and SSO status checks for Angular UI integration.
- Angular transition support is started with API-first auth endpoints and CORS for local dev.

## Important Behavior Clarifications

- Redshift discovery/metadata calls require a selected database; missing database now returns explicit feedback.
- Fuzzy matching no longer accepts token-overlap-only matches without sufficient similarity quality.

## Deployment Readiness Snapshot

- Suitable for controlled pilot on college server with:
  - HTTPS reverse proxy
  - role-based access governance
  - monitoring and incident runbooks
- Before full production rollout:
  - move secrets to enterprise vault
  - move local JSON stores to managed data services
  - complete enterprise SSO hardening and validation
