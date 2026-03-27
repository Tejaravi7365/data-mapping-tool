# Angular Starter: Auth, Audit Logs, and Route Map

This starter complements `docs/ANGULAR_TRANSITION_PLAN.md` and maps directly to current backend APIs.

## 1) Audit Logs Service (Angular)

```ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface AuditLogRow {
  id: string;
  created_at: string;
  actor: string;
  action: string;
  details: string;
  status: string;
  target?: string;
  metadata?: Record<string, unknown>;
}

export interface AuditLogResponse {
  logs: AuditLogRow[];
  filters: {
    actors: string[];
    actions: string[];
    statuses: string[];
    is_admin: boolean;
  };
}

@Injectable({ providedIn: 'root' })
export class AuditLogsService {
  private readonly base = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  getAuditLogs(args: {
    action?: string;
    actor?: string;
    status?: string;
    fromTs?: string;
    toTs?: string;
    limit?: number;
  }): Observable<AuditLogResponse> {
    let params = new HttpParams();
    if (args.action) params = params.set('action', args.action);
    if (args.actor) params = params.set('actor', args.actor);
    if (args.status) params = params.set('status', args.status);
    if (args.fromTs) params = params.set('from_ts', args.fromTs);
    if (args.toTs) params = params.set('to_ts', args.toTs);
    if (args.limit) params = params.set('limit', String(args.limit));
    return this.http.get<AuditLogResponse>(`${this.base}/api/audit-logs`, {
      params,
      withCredentials: true,
    });
  }

  exportAuditLogs(args: {
    action?: string;
    actor?: string;
    status?: string;
    fromTs?: string;
    toTs?: string;
    limit?: number;
  }): string {
    const params = new URLSearchParams();
    if (args.action) params.set('action', args.action);
    if (args.actor) params.set('actor', args.actor);
    if (args.status) params.set('status', args.status);
    if (args.fromTs) params.set('from_ts', args.fromTs);
    if (args.toTs) params.set('to_ts', args.toTs);
    params.set('limit', String(args.limit ?? 1000));
    return `${this.base}/api/audit-logs/export?${params.toString()}`;
  }
}
```

## 2) Admin SSO Settings API Contract

- `GET /api/admin/sso-settings`
- `PUT /api/admin/sso-settings`

Payload shape:

```json
{
  "enabled": true,
  "provider": "okta",
  "issuer_url": "https://dev-xxxxxx.okta.com/oauth2/default",
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "https://mapping.college.edu/auth/callback",
  "scopes": "openid profile email"
}
```

## 3) Angular Route Map

Recommended mapping:

- `/login` -> LoginComponent
- `/dashboard` -> DashboardComponent
- `/mapping` -> MappingWorkspaceComponent
- `/mapping-history` -> MappingHistoryComponent
- `/datasources` -> DatasourcesComponent (admin guard)
- `/settings` -> SettingsComponent
- `/audit-logs` -> AuditLogsComponent

Example `app.routes.ts`:

```ts
import { Routes } from '@angular/router';
import { authGuard, adminGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/login/login.component').then(m => m.LoginComponent) },
  { path: 'dashboard', canActivate: [authGuard], loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent) },
  { path: 'mapping', canActivate: [authGuard], loadComponent: () => import('./features/mapping/mapping.component').then(m => m.MappingComponent) },
  { path: 'mapping-history', canActivate: [authGuard], loadComponent: () => import('./features/mapping-history/mapping-history.component').then(m => m.MappingHistoryComponent) },
  { path: 'datasources', canActivate: [adminGuard], loadComponent: () => import('./features/datasources/datasources.component').then(m => m.DatasourcesComponent) },
  { path: 'settings', canActivate: [authGuard], loadComponent: () => import('./features/settings/settings.component').then(m => m.SettingsComponent) },
  { path: 'audit-logs', canActivate: [authGuard], loadComponent: () => import('./features/audit-logs/audit-logs.component').then(m => m.AuditLogsComponent) },
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  { path: '**', redirectTo: 'dashboard' },
];
```

## 4) Notes for Okta Integration

- Use backend SSO settings as admin-configurable source of truth.
- In production, move `client_secret` to secrets manager and store only reference IDs.
- Add backend OIDC authorize/callback endpoints in the next step to complete IdP login flow.
