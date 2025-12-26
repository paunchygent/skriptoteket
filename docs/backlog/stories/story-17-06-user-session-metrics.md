---
type: story
id: ST-17-06
title: "User session metrics"
status: ready
owners: "agents"
created: 2025-12-27
epic: "EPIC-17"
acceptance_criteria:
  - "Given the /metrics endpoint, when I query for user metrics, then I see skriptoteket_active_sessions gauge"
  - "Given a user logs in successfully, when I check metrics, then skriptoteket_logins_total{status='success'} increments"
  - "Given a user login fails, when I check metrics, then skriptoteket_logins_total{status='failure'} increments"
  - "Given the Grafana dashboard, when I view user session panel, then I see current active session count over time"
  - "Given the Grafana dashboard, when I view login activity panel, then I see login rate with success/failure breakdown"
---

## Context

Operators need visibility into user activity to understand usage patterns and detect anomalies (e.g., brute force attempts, unusual session counts). Currently no user-related metrics are exposed.

## Metrics to Add

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `skriptoteket_active_sessions` | Gauge | - | Current count of active user sessions |
| `skriptoteket_logins_total` | Counter | status | Login attempts (success/failure) |
| `skriptoteket_users_by_role` | Gauge | role | Active users by role (user/contributor/admin/superuser) |

## Implementation

### 1. Add metrics to `src/skriptoteket/observability/metrics.py`

```python
"active_sessions": Gauge(
    "skriptoteket_active_sessions",
    "Current count of active user sessions",
    registry=REGISTRY,
),
"logins_total": Counter(
    "skriptoteket_logins_total",
    "Total login attempts",
    ["status"],  # success, failure
    registry=REGISTRY,
),
"users_by_role": Gauge(
    "skriptoteket_users_by_role",
    "Active users by role",
    ["role"],  # user, contributor, admin, superuser
    registry=REGISTRY,
),
```

### 2. Instrument identity layer

- Login handler: increment `logins_total` on success/failure
- Session middleware or `/metrics` endpoint: compute active sessions from session store
- Role breakdown: query from session data or compute at scrape time

### 3. Add dashboard panels

Add to HTTP metrics dashboard or create dedicated user activity dashboard:

- **Active Sessions** - Time series of `skriptoteket_active_sessions`
- **Login Rate** - `rate(skriptoteket_logins_total[5m])` by status
- **Login Success Rate** - Percentage gauge with thresholds
- **Users by Role** - Stacked area or pie chart

## Files

Modify:
- `src/skriptoteket/observability/metrics.py` (add metrics)
- `src/skriptoteket/web/routes/auth.py` or login handler (instrument logins)
- `src/skriptoteket/web/routes/observability.py` (compute active sessions at scrape time)
- `observability/grafana/provisioning/dashboards/skriptoteket-http-metrics.json` (add panels)

## Notes

- Active sessions computed at scrape time avoids maintaining separate state
- Consider adding `skriptoteket_session_duration_seconds` histogram for session length analysis (future)
- Failed login rate can trigger alerts for brute force detection (future ST-17-03 enhancement)
