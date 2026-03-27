# Angular Transition Plan (Backend + Frontend)

## Goal

Move from server-rendered templates to Angular frontend while preserving current Python/FastAPI backend and API contracts.

## Current State

- Frontend: Jinja templates served by FastAPI
- Backend: FastAPI endpoints for auth, datasources, mapping, audit, admin user management
- Session auth: cookie-based

## Phase Plan

### Phase 0: Backend readiness (completed start)

- Add JSON auth endpoints for SPA usage:
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
- Add SSO status endpoint for frontend feature toggles:
  - `GET /api/auth/sso/status`
- Enable CORS for Angular local dev (`localhost:4200`)
- Keep existing routes/templates unchanged for backward compatibility

### Phase 1: Angular shell and auth integration

- Build Angular app with:
  - Login page using `/api/auth/login`
  - Route guards using `/api/auth/me`
  - Logout using `/api/auth/logout`
- Add shared HTTP interceptor for 401 handling

### Phase 2: Feature-by-feature migration

Migrate pages in this order:
1. Dashboard
2. Mapping Workspace
3. Datasources
4. Settings/User Management
5. Audit Logs

Each page should use existing backend APIs without changing business logic.

### Phase 3: Production hardening

- Build and host Angular static files via Nginx/CDN
- Keep FastAPI as API-only backend
- Add environment-specific API base URLs
- Validate CORS policy for production origins

## API Checklist for Angular Team

- Auth:
  - `POST /api/auth/login`
  - `POST /api/auth/logout`
  - `GET /api/auth/me`
  - `GET /api/auth/sso/status`
  - `GET /auth/sso/login`
  - `GET /auth/sso/callback`
- Datasource:
  - `GET /api/datasources`
  - `POST /api/datasources`
  - `PUT /api/datasources/{id}`
  - `DELETE /api/datasources/{id}`
  - `POST /api/datasources/{id}/test`
  - `POST /api/datasources/discover`
  - `GET /api/datasources/{id}/databases`
  - `GET /api/datasources/{id}/schemas`
  - `GET /api/datasources/{id}/tables`
- Mapping:
  - `POST /generate-mapping`
  - `POST /generate-mapping/batch`
- Admin users:
  - `GET /api/admin/users`
  - `POST /api/admin/users`
  - `PUT /api/admin/users/{username}`
  - `POST /api/admin/users/{username}/reset-password`
  - `DELETE /api/admin/users/{username}`
- Audit:
  - `GET /api/audit-logs`
  - `GET /api/audit-logs/export`
- Admin SSO settings:
  - `GET /api/admin/sso-settings`
  - `PUT /api/admin/sso-settings`

## Recommended Angular Module Structure

- `core/`
  - auth service, interceptor, guards
- `shared/`
  - reusable UI components, common models
- `features/dashboard`
- `features/mapping`
- `features/datasources`
- `features/settings`
- `features/audit-logs`

## Acceptance Criteria

- All migrated pages work without server-rendered templates
- Role-based behavior matches backend authorization
- Existing backend tests/smoke checks remain green
- Pilot users can complete end-to-end mapping workflow
