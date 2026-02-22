# Security Considerations for Data Mapping Sheet Generator

## Purpose

This document helps security reviewers, architects, and business stakeholders assess how this tool behaves on a local system and what controls should be applied before broader adoption.

## Security Posture Summary

- The app is designed for **local execution** by default (`127.0.0.1`).
- Credentials are passed at runtime and are **not persisted in a database** by the app.
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
- No credential persistence layer is implemented in app code.

Recommended controls:
- Use least-privilege database users (metadata read only where possible).
- Use dedicated integration/service accounts.
- Avoid shared credentials across teams.

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

## Security Assurance Statement (for stakeholders)

When executed as designed (local bind, least-privileged credentials, controlled outputs), this tool supports secure metadata-driven mapping generation with low residual risk. The primary governance focus should be operational controls, credential management, and endpoint hardening.
