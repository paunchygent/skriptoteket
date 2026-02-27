---
id: "094-observability-infrastructure"
type: "operations"
created: 2025-12-20
scope: "devops"
---

# 094: Observability Infrastructure

Deployment and operations of the observability stack (Prometheus, Grafana, Jaeger, Loki).

## 1. Stack Components

| Service | Port (External) | Port (Internal) | Purpose |
|---------|-----------------|-----------------|---------|
| Prometheus | 9091 | 9090 | Metrics collection and storage |
| Grafana | 3000 | 3000 | Dashboards and visualization |
| Jaeger | 16686 | 16686 | Trace visualization |
| Jaeger OTLP | 4317 | 4317 | Trace ingestion (gRPC) |
| Loki | 3100 | 3100 | Log aggregation |
| Promtail | - | 9080 | Log collection agent |

## 2. Deployment

The observability stack runs separately from the application:

```bash
# Start observability stack
docker compose -f compose.observability.yaml up -d

# Check status
docker compose -f compose.observability.yaml ps

# View logs
docker compose -f compose.observability.yaml logs -f

# Stop stack
docker compose -f compose.observability.yaml down
```

### PDM Scripts

```bash
pdm run obs-start    # Start stack
pdm run obs-stop     # Stop stack
pdm run obs-restart  # Restart stack
pdm run obs-logs     # Follow logs
pdm run obs-status   # Check status
```

## 3. Access URLs (Home Server)

| Service | URL |
|---------|-----|
| Grafana | http://hemma.hule.education:3000 |
| Prometheus | http://hemma.hule.education:9091 |
| Jaeger UI | http://hemma.hule.education:16686 |

## 4. Network Configuration

All services connect via `hule-network` (external Docker network):

```yaml
# compose.observability.yaml
networks:
  hule-network:
    external: true
```

The application container (`skriptoteket-web`) MUST be on the same network.

## 5. Prometheus Scrape Configuration

```yaml
# observability/prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'skriptoteket'
    static_configs:
      - targets: ['skriptoteket-web:8000']
    metrics_path: '/metrics'

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'loki'
    static_configs:
      - targets: ['loki:3100']
```

## 6. Grafana Datasources

Auto-provisioned via `observability/grafana/provisioning/datasources/`:

```yaml
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090

  - name: Loki
    type: loki
    url: http://loki:3100
    jsonData:
      derivedFields:
        - name: TraceID
          matcherRegex: '"trace_id":"([a-f0-9]+)"'
          url: 'http://jaeger:16686/trace/$${__value.raw}'
          datasourceUid: jaeger

  - name: Jaeger
    type: jaeger
    url: http://jaeger:16686
```

## 7. Data Retention

| Component | Retention | Configuration |
|-----------|-----------|---------------|
| Prometheus | 30 days | `--storage.tsdb.retention.time=30d` |
| Loki | 30 days | `limits_config.retention_period: 30d` |
| Jaeger | In-memory | Traces lost on restart |
| Grafana | Persistent | Volume: `grafana_data` |

## 8. Volume Locations

```yaml
volumes:
  prometheus_data:   # Prometheus TSDB
  loki_data:         # Loki chunks and indices
  promtail_positions:  # Promtail file positions
  grafana_data:      # Grafana dashboards and settings
```

## 9. Troubleshooting

### Prometheus Not Scraping

```bash
# Check targets
curl http://localhost:9091/api/v1/targets

# Verify network connectivity
docker exec prometheus wget -qO- http://skriptoteket-web:8000/metrics | head -20
```

### Loki Not Receiving Logs

```bash
# Check Promtail status
docker logs promtail --tail 50

# Verify Loki readiness
docker exec loki wget -qO- http://localhost:3100/ready
```

### Jaeger Not Receiving Traces

```bash
# Verify tracing is enabled
docker inspect skriptoteket-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep OTEL

# Check for trace headers
curl -si http://localhost:8000/login | grep -i x-trace-id
```

### Grafana Datasource Errors

```bash
# Check Grafana logs
docker logs grafana --tail 50

# Verify connectivity from Grafana
docker exec grafana wget -qO- http://prometheus:9090/-/healthy
```

## 10. Enabling Tracing in Application

After deploying the observability stack, redeploy the application:

```bash
# compose.prod.yaml includes:
# OTEL_TRACING_ENABLED=true
# OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

docker compose -f compose.prod.yaml up -d --build
```

## 11. Log-to-Trace Correlation

In Grafana:
1. Go to Explore → Loki
2. Query logs with `{service_name="skriptoteket"}`
3. Click on a log line with `trace_id`
4. Click "TraceID" link to jump to Jaeger

## References

- ADR-0026: Observability stack infrastructure
- Runbook: `docs/runbooks/runbook-observability-logging.md`
- Compose file: `compose.observability.yaml`
