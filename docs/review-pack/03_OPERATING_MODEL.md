# Operating Model and Adoption Plan

## 1) Stakeholders and Roles

- Product Owner / Supervisor
  - Defines priorities, approves rollout phases
- Security Team
  - Reviews controls, approves production exposure
- Infrastructure Team
  - Hosts service, networking, TLS, monitoring, backups
- Application Admins
  - Manage users, roles, datasource onboarding
- Data Engineers / Analysts
  - Generate and review mappings
- Support Team (L1/L2)
  - Triage incidents and route escalations

## 2) User Personas and Access

- Admin
  - user and role management
  - datasource profile onboarding/testing
  - audit review and export
- User
  - mapping generation and history view
  - limited endpoint access based on role policy

## 3) Standard User Journey

1. User logs in with approved account
2. Selects source and target datasource
3. Discovers database/schema/table metadata
4. Generates mapping output
5. Exports mapping file
6. Actions are auditable for review

## 4) Data Source Onboarding Process

1. Request submitted by team (source/target details + owner)
2. Admin validates network and credentials
3. Admin creates datasource profile
4. Connection test and schema discovery performed
5. Approval and role-scoped assignment completed

## 5) Support and Incident Workflow

- L1
  - login/access issues
  - basic connection troubleshooting
- L2
  - app/service errors
  - datasource connector and metadata failures
- L3 (engineering)
  - code defects and enhancement fixes

Escalation targets:
- security incidents -> Security Team
- platform outage -> Infrastructure Team
- functionality defects -> Application Engineering

## 6) Adoption and Training

- Admin training (90 mins)
  - user lifecycle, role controls, datasource governance, audit exports
- End-user training (60 mins)
  - mapping workflow, validation, export, common errors
- Quick references
  - one-page user guide
  - one-page admin runbook

## 7) Success Metrics

- Time to produce first mapping per project
- Number of successful mapping generations per week
- Reduction in manual mapping defects
- Mean time to resolve user issues
- Number of unauthorized access attempts blocked

## 8) Governance Cadence

- Weekly: operational review (errors, uptime, support tickets)
- Monthly: security and access review (admin actions, role changes)
- Quarterly: roadmap review and capability prioritization
