---
type: story
id: ST-17-04
title: "Jaeger public access"
status: ready
owners: "agents"
created: 2025-12-26
epic: "EPIC-17"
acceptance_criteria:
  - "Given nginx-proxy is running, when I navigate to https://jaeger.hemma.hule.education, then I see the Jaeger UI with valid SSL certificate"
  - "Given the Jaeger service in compose.observability.yaml, when I inspect the container environment, then VIRTUAL_HOST and LETSENCRYPT_HOST are set to jaeger.hemma.hule.education"
  - "Given a trace exists in Jaeger, when I access it via the public URL, then the trace details are visible without SSH tunnel"
---

## Context

Jaeger UI is currently internal-only, requiring SSH tunnel access (`ssh -L 16686:localhost:16686 hemma`). This story exposes Jaeger publicly via nginx-proxy with automatic SSL.

## Implementation

### DNS Record

Add A record in Namecheap:
- Host: `jaeger.hemma`
- Type: A
- Value: (server IP, same as other subdomains)

### compose.observability.yaml Changes

```yaml
jaeger:
  image: jaegertracing/jaeger:2.1.0
  container_name: jaeger
  restart: unless-stopped
  environment:
    - JAEGER_LISTEN_HOST=0.0.0.0
    # nginx-proxy integration
    - VIRTUAL_HOST=jaeger.hemma.hule.education
    - VIRTUAL_PORT=16686
    - LETSENCRYPT_HOST=jaeger.hemma.hule.education
  expose:
    - "16686"
  ports:
    # Keep OTLP ports for trace ingestion
    - "4317:4317"
    - "4318:4318"
  networks:
    - hule-network
```

**Note:** Remove direct `16686:16686` port mapping; nginx-proxy handles UI access.

## Files

Modify: `compose.observability.yaml`

Modify: `docs/runbooks/runbook-observability.md` (update access URLs table)

## Notes

- Jaeger has no built-in authentication
- If abuse is detected, add nginx basic auth similar to Prometheus
- OTLP ports (4317, 4318) remain internal for trace ingestion from skriptoteket-web
