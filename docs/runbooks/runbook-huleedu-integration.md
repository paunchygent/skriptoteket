---
type: runbook
id: RUN-huleedu-integration
title: "Runbook: HuleEdu + Skriptoteket Integration on Hemma"
status: active
owners: "olof"
created: 2025-12-31
updated: 2025-12-31
system: "hemma.hule.education"
links: ["RUN-gpu-ai-workloads", "RUN-home-server"]
---

Operations guide for running HuleEdu and Skriptoteket together on hemma.hule.education.

## Architecture Overview

```text
                            ┌─────────────────────────────────────┐
                            │           nginx-proxy               │
                            │  (SSL termination, routing)         │
                            └──────────────┬──────────────────────┘
                                           │
            ┌──────────────────────────────┼──────────────────────────────┐
            │                              │                              │
            ▼                              ▼                              ▼
┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│ skriptoteket.hule.edu │    │ huleedu.hule.edu      │    │ api.huleedu.hule.edu  │
│ (Skriptoteket web)    │    │ (BFF Teacher)         │    │ (API Gateway)         │
└───────────┬───────────┘    └───────────┬───────────┘    └───────────┬───────────┘
            │                            │                            │
            │                            └─────────────┬──────────────┘
            │                                          │
            │    ┌─────────────────────────────────────┼─────────────────────────┐
            │    │          huleedu_internal_network   │                         │
            │    │  ┌─────────┐ ┌─────────┐ ┌──────────┴──┐ ┌────────┐ ┌───────┐ │
            │    │  │ content │ │ essay   │ │ nlp_service │ │ kafka  │ │ redis │ │
            │    │  │ service │ │ service │ │             │ │        │ │       │ │
            │    │  └─────────┘ └─────────┘ └─────────────┘ └────────┘ └───────┘ │
            │    └───────────────────────────────────────────────────────────────┘
            │                                    │
            │                                    │
            ▼                                    ▼
┌───────────────────────┐              ┌─────────────────┐
│ Skriptoteket Runner   │──────────────│ nlp_service     │
│ (tool scripts)        │   NLP calls  │ (via internal)  │
└───────────────────────┘              └─────────────────┘
            │
            │
            ▼
┌───────────────────────────────────────────────────────────────────┐
│                        hule-network                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │ shared-postgres │  │ jaeger          │  │ prometheus        │  │
│  │ (all databases) │  │ (tracing)       │  │ (metrics)         │  │
│  └─────────────────┘  └─────────────────┘  └───────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────────┐
│                     Host (systemd services)                        │
│  ┌─────────────────────────┐  ┌─────────────────────────────────┐ │
│  │ llama-server :8082      │  │ tabby :8083                     │ │
│  │ (Qwen3-Coder-30B, ROCm) │  │ (code completion API)           │ │
│  └─────────────────────────┘  └─────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Network Configuration

| Network | Purpose | Services |
|---------|---------|----------|
| `hule-network` | External, shared infra | nginx-proxy, shared-postgres, jaeger, prometheus |
| `huleedu_internal_network` | HuleEdu microservices | All HuleEdu services, Kafka, Redis |
| Host | GPU inference | llama-server, tabby |

Docker containers access host GPU via `host.docker.internal:8082`.

## Shared PostgreSQL

All databases run in `shared-postgres` on `hule-network`.

### Databases

| Application | Databases |
|-------------|-----------|
| Skriptoteket | `skriptoteket` |
| HuleEdu | `huleedu_batch_conductor`, `huleedu_batch_orchestrator`, `huleedu_cj_assessment`, `huleedu_class_management`, `huleedu_content`, `huleedu_email`, `huleedu_entitlements`, `huleedu_essay_lifecycle`, `huleedu_file_service`, `huleedu_identity`, `huleedu_nlp`, `huleedu_result_aggregator`, `huleedu_spellchecker` |

### Create HuleEdu Databases

```bash
ssh hemma "docker exec -it shared-postgres psql -U postgres -c \"
CREATE DATABASE huleedu_batch_conductor;
CREATE DATABASE huleedu_batch_orchestrator;
CREATE DATABASE huleedu_cj_assessment;
CREATE DATABASE huleedu_class_management;
CREATE DATABASE huleedu_content;
CREATE DATABASE huleedu_email;
CREATE DATABASE huleedu_entitlements;
CREATE DATABASE huleedu_essay_lifecycle;
CREATE DATABASE huleedu_file_service;
CREATE DATABASE huleedu_identity;
CREATE DATABASE huleedu_nlp;
CREATE DATABASE huleedu_result_aggregator;
CREATE DATABASE huleedu_spellchecker;
\""
```

### Create Database User

```bash
ssh hemma "docker exec -it shared-postgres psql -U postgres -c \"
CREATE USER huleedu_user WITH PASSWORD '<password>';
GRANT ALL PRIVILEGES ON DATABASE huleedu_batch_conductor TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_batch_orchestrator TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_cj_assessment TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_class_management TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_content TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_email TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_entitlements TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_essay_lifecycle TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_file_service TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_identity TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_nlp TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_result_aggregator TO huleedu_user;
GRANT ALL PRIVILEGES ON DATABASE huleedu_spellchecker TO huleedu_user;
\""
```

## Deployment

### Skriptoteket

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"
```

### HuleEdu

```bash
ssh hemma "cd ~/apps/huleedu && git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build"
```

### Environment Variables (HuleEdu .env)

```bash
# Database
HULEEDU_DB_USER=huleedu_user
HULEEDU_PROD_DB_PASSWORD=<production-password>

# Authentication
JWT_SECRET_KEY=<jwt-secret>
HULEEDU_INTERNAL_API_KEY=<internal-api-key>

# LLM Providers (for cj_assessment, llm_provider_service)
ANTHROPIC_API_KEY=<key>
OPENAI_API_KEY=<key>

# Local GPU inference
NLP_SERVICE_LOCAL_LLM_ENABLED=true
LLM_PROVIDER_SERVICE_LOCAL_LLM_ENABLED=true

# Email (SMTP)
EMAIL_SMTP_HOST=mail.privateemail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=<username>
EMAIL_SMTP_PASSWORD=<password>
```

## Skriptoteket ↔ HuleEdu Integration

### Runner Access to NLP Service

Skriptoteket runner containers can call HuleEdu's NLP service for tool scripts that need NLP inference.

**Configuration:** Runner joins `huleedu_internal_network`:

```python
# In Skriptoteket runner configuration
networks = ["huleedu_internal_network"]

# Tool script can then call:
# http://nlp_service:8000/api/v1/...
```

### GPU Access

Both applications access the same GPU via `host.docker.internal`:

| Application | Service | GPU Access |
|-------------|---------|------------|
| Skriptoteket | web | `http://host.docker.internal:8082` (completions) |
| HuleEdu | nlp_service | `http://host.docker.internal:8082` (inference) |
| HuleEdu | llm_provider_service | `http://host.docker.internal:8082` (small tasks) |

## Domain Configuration

### DNS Records (Namecheap)

| Subdomain | Type | Target |
|-----------|------|--------|
| `skriptoteket.hule.education` | A | hemma IP (via ddclient) |
| `huleedu.hule.education` | A | hemma IP |
| `api.huleedu.hule.education` | A | hemma IP |
| `ws.huleedu.hule.education` | A | hemma IP |

### nginx-proxy Routing

| Domain | Container | Port |
|--------|-----------|------|
| `skriptoteket.hule.education` | skriptoteket-web | 8000 |
| `huleedu.hule.education` | huleedu_bff_teacher_service | 4101 |
| `api.huleedu.hule.education` | huleedu_api_gateway_service | 8080 |
| `ws.huleedu.hule.education` | huleedu_websocket_service | 8080 |

## Health Checks

### Skriptoteket

```bash
ssh hemma "curl -s https://skriptoteket.hule.education/healthz"
```

### HuleEdu

```bash
# BFF (frontend)
ssh hemma "curl -s https://huleedu.hule.education/healthz"

# API Gateway
ssh hemma "curl -s https://api.huleedu.hule.education/healthz"

# Internal services (from within network)
ssh hemma "docker exec huleedu_api_gateway_service curl -s http://content_service:8000/healthz"
```

### GPU Services

```bash
ssh hemma "curl -s http://localhost:8082/health"
ssh hemma "curl -s http://localhost:8083/v1/health | jq .model"
```

## Troubleshooting

### Service Can't Reach shared-postgres

```bash
# Check network connectivity
ssh hemma "docker exec huleedu_content_service ping -c 1 shared-postgres"

# Verify service is on hule-network
ssh hemma "docker inspect huleedu_content_service | jq '.[0].NetworkSettings.Networks'"
```

### GPU Not Accessible from Container

```bash
# Check extra_hosts is set
ssh hemma "docker exec huleedu_nlp_service cat /etc/hosts | grep host.docker.internal"

# Test connectivity
ssh hemma "docker exec huleedu_nlp_service curl -s http://host.docker.internal:8082/health"
```

### Database Connection Errors

```bash
# Check ENVIRONMENT is set to production
ssh hemma "docker exec huleedu_content_service printenv | grep ENVIRONMENT"
# Should be: ENVIRONMENT=production

# Check prod DB vars are set
ssh hemma "docker exec huleedu_content_service printenv | grep HULEEDU_PROD"
```

### Kafka/Redis Issues

```bash
# Check Kafka is healthy
ssh hemma "docker exec huleedu_kafka kafka-topics.sh --bootstrap-server localhost:9092 --list"

# Check Redis
ssh hemma "docker exec huleedu_redis redis-cli ping"
```

## Maintenance

### Restart All HuleEdu Services

```bash
ssh hemma "cd ~/apps/huleedu && docker compose -f docker-compose.yml -f docker-compose.prod.yml restart"
```

### View Logs

```bash
# Specific service
ssh hemma "docker logs -f huleedu_nlp_service --tail 100"

# All services
ssh hemma "cd ~/apps/huleedu && docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f"
```

### Database Backup

```bash
# Backup all HuleEdu databases
ssh hemma "docker exec shared-postgres pg_dump -U postgres huleedu_content > ~/backups/huleedu_content_$(date +%Y%m%d).sql"
```

## References

- [runbook-gpu-ai-workloads.md](runbook-gpu-ai-workloads.md) - GPU operations
- [runbook-home-server.md](runbook-home-server.md) - Server infrastructure
- [runbook-tabby-codemirror.md](runbook-tabby-codemirror.md) - AI completion services
