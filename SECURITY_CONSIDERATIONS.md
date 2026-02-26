# Security Considerations for Data Mapping Sheet Generator

## Purpose

This document helps security reviewers, architects, and business stakeholders assess how this tool behaves on a local system and what controls should be applied before broader adoption.

## Security Posture Summary

- The app is designed for **local execution** by default (`127.0.0.1`).
- Current prototype stores users and datasource definitions in local JSON files (`app/data/users.json`, `app/data/datasources.json`).
- Logs mask sensitive fields such as passwords and tokens.
- Data exposure risk is primarily operational (how users run/configure the app), not from background cloud storage in this codebase.

## What data is handled

- Connection details for source/target systems
- Metadata (table names, columns, data types, nullability, lengths)
- Generated mapping sheets (`.xlsx`)

By default, business row-level data is not required for mapping generation; metadata-level access is sufficient.

## Threat Considerations and Mitigations

### 1) Credential exposure

Risk:
- Credentials entered in UI could leak through logs, screenshots, or browser history if mishandled.

Current mitigations:
- Password/token fields are masked in app logging.
- Credentials are not returned in clear text from datasource list APIs (sensitive fields are redacted in responses/logs).

Recommended controls:
- Use least-privilege database users (metadata read only where possible).
- Use dedicated integration/service accounts.
- Avoid shared credentials across teams.
- Migrate datasource credential storage from local JSON to enterprise secrets management before production.

### 2) Unauthorized network access

Risk:
- Running with `--host 0.0.0.0` can expose the service to other machines.

Current mitigations:
- Local loopback execution is the default.

Recommended controls:
- Keep local-only bind (`127.0.0.1`) unless required.
- If network exposure is required, enforce firewall allow-listing and VPN segmentation.
- Do not expose this app directly to public internet.

### 3) Sensitive output files

Risk:
- Exported mapping files may contain sensitive schema intelligence.

Current behavior:
- Excel files are generated for user review and can be saved to Desktop.

Recommended controls:
- Store outputs in approved secure locations.
- Apply endpoint encryption/disk protection policies.
- Classify and retain mapping files under enterprise data handling policy.

### 4) Dependency and runtime risk

Risk:
- Open-source packages can introduce vulnerabilities.

Recommended controls:
- Pin and scan dependencies regularly.
- Run vulnerability scans in CI/CD.
- Keep Python runtime and ODBC drivers patched.

### 5) Hosted deployment risk (EC2/VM shared URL)

Risk:
- Centralized deployment increases blast radius if access controls are weak.

Recommended controls:
- Keep app node private; expose only reverse proxy/ALB.
- Enforce HTTPS/TLS and secure ciphers.
- Use SSO/OIDC + RBAC before enabling broad access.
- Restrict inbound access by corporate network/VPN/security groups.
- Apply OS hardening and patch baselines on host instances.

### 6) One-time connection profile storage risk

Risk:
- Persisting reusable connection definitions can expose credentials if stored insecurely.

Recommended controls:
- Store secrets in managed secret vault (AWS Secrets Manager/HashiCorp Vault), not plaintext.
- Store only secret references in application database.
- Encrypt data at rest for any configuration tables.
- Apply least-privilege IAM policies for secret retrieval.
- Audit secret read operations and rotate credentials periodically.

Current implementation note:
- The current initial release uses local JSON stores (`app/data/datasources.json`, `app/data/users.json`) for rapid prototyping.
- This should be treated as non-production and migrated to a DB + secrets-backed design before enterprise rollout.

### 7) Role/session controls in current build

Current behavior:
- Session cookie based login (`/login`) with prototype roles (`admin`, `user`).
- Session cookies are HTTP-only, TTL-bound, and marked `secure` under HTTPS.
- Server-side sessions enforce expiration.
- Password storage uses salted PBKDF2-HMAC-SHA256 hashes.
- Legacy SHA-256 hashes are auto-migrated to PBKDF2 on successful login.
- Admin-gated management APIs/pages cover datasource, user, and legacy profile operations.

Recommended controls:
- Use signed/rotated session secrets with persistent backing store (for multi-instance hosting).
- Integrate enterprise identity (SSO/OIDC) instead of local user file.
- Add audit event persistence for admin actions.

## Operational Best Practices

- Run the tool on managed corporate machines only.
- Use environment-specific service accounts.
- Restrict access to generated files and logs.
- Review logs for repeated connection failures or unusual usage patterns.
- Add enterprise authentication if multi-user deployment is planned.

## Recommended Enterprise Deployment Pattern

For production-grade use:

- Containerize app with signed images.
- Place behind internal reverse proxy/API gateway.
- Add SSO/RBAC and audit trail.
- Centralize logging in SIEM with redaction controls.
- Integrate secrets manager instead of manual credential entry.
- Add profile-level authorization checks for source/target selection.
- Add approval workflow for onboarding new connection profiles.

## Security Assurance Statement (for stakeholders)

When executed as designed (local bind, least-privileged credentials, controlled outputs), this tool supports secure metadata-driven mapping generation with low residual risk. The primary governance focus should be operational controls, credential management, and endpoint hardening.
