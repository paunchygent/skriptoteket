---
type: runbook
id: RUN-SKRIPT-runbook-huleedu-skriptoteket-integration-on-hemma
title: 'Runbook: HuleEdu + Skriptoteket Integration on Hemma'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
retired_ids:
- RUN-huleedu-integration
summary: 'Runbook: HuleEdu + Skriptoteket Integration on Hemma'
system: hemma.hule.education
---

## Trigger

### Trigger

### Source: Architecture Overview

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

### Preconditions

### Source: Network Configuration

| Network | Purpose | Services |
|---------|---------|----------|
| `hule-network` | External, shared infra | nginx-proxy, shared-postgres, jaeger, prometheus |
| `huleedu_internal_network` | HuleEdu microservices | All HuleEdu services, Kafka, Redis |
| Host | GPU inference | llama-server, tabby |

Docker containers access host GPU via `host.docker.internal:8082`.

### Source: Shared PostgreSQL

All databases run in `shared-postgres` on `hule-network`.

### Source: Environment Variables (HuleEdu .env)

```bash

### Steps

### Source: Deployment



### Source: Maintenance



### Expected Results

### Source: Health Checks



### Source: References

- [runbook-gpu-ai-workloads.md](runbook-gpu-ai-workloads.md) - GPU operations
- [runbook-home-server.md](runbook-home-server.md) - Server infrastructure
- [runbook-tabby-codemirror.md](runbook-tabby-codemirror.md) - AI completion services

### Stop Conditions

### Source: Troubleshooting



### Rollback

The source does not provide a separate rollback section; no additional rollback is recorded.

### Source: Databases

| Application | Databases |
|-------------|-----------|
| Skriptoteket | `skriptoteket` |
| HuleEdu | `huleedu_batch_conductor`, `huleedu_batch_orchestrator`, `huleedu_cj_assessment`, `huleedu_class_management`, `huleedu_content`, `huleedu_email`, `huleedu_entitlements`, `huleedu_essay_lifecycle`, `huleedu_file_service`, `huleedu_identity`, `huleedu_nlp`, `huleedu_result_aggregator`, `huleedu_spellchecker` |

### Source: Create HuleEdu Databases

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

### Source: Create Database User

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

### Source: Skriptoteket

```bash
ssh hemma "cd ~/apps/skriptoteket && git pull && docker compose -f compose.prod.yaml up -d --build"
```

### Source: HuleEdu

```bash
ssh hemma "cd ~/apps/huleedu && git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build"
```

### Source: Database

HULEEDU_DB_USER=huleedu_user
HULEEDU_PROD_DB_PASSWORD=<production-password>

### Source: Authentication

JWT_SECRET_KEY=<jwt-secret>
HULEEDU_INTERNAL_API_KEY=<internal-api-key>

### Source: LLM Providers (for cj_assessment, llm_provider_service)

ANTHROPIC_API_KEY=<key>
OPENAI_LLM_COMPLETION_API_KEY=<key>

### Source: Local GPU inference

NLP_SERVICE_LOCAL_LLM_ENABLED=true
LLM_PROVIDER_SERVICE_LOCAL_LLM_ENABLED=true

### Source: Email (SMTP)

EMAIL_SMTP_HOST=mail.privateemail.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USERNAME=<username>
EMAIL_SMTP_PASSWORD=<password>
```

### Source: Skriptoteket ↔ HuleEdu Integration



### Source: Runner Access to NLP Service

Skriptoteket runner containers can call HuleEdu's NLP service for tool scripts that need NLP inference.

**Configuration:** Runner joins `huleedu_internal_network`:

```python

### Source: In Skriptoteket runner configuration

networks = ["huleedu_internal_network"]

### Source: Tool script can then call:



### Source: http://nlp_service:8000/api/v1/...

```

### Source: GPU Access

Both applications access the same GPU via `host.docker.internal`:

| Application | Service | GPU Access |
|-------------|---------|------------|
| Skriptoteket | web | `http://host.docker.internal:8082` (completions) |
| HuleEdu | nlp_service | `http://host.docker.internal:8082` (inference) |
| HuleEdu | llm_provider_service | `http://host.docker.internal:8082` (small tasks) |

### Source: Domain Configuration



### Source: DNS Records (Namecheap)

| Subdomain | Type | Target |
|-----------|------|--------|
| `skriptoteket.hule.education` | A | hemma IP (via ddclient) |
| `huleedu.hule.education` | A | hemma IP |
| `api.huleedu.hule.education` | A | hemma IP |
| `ws.huleedu.hule.education` | A | hemma IP |

### Source: nginx-proxy Routing

| Domain | Container | Port |
|--------|-----------|------|
| `skriptoteket.hule.education` | skriptoteket-web | 8000 |
| `huleedu.hule.education` | huleedu_bff_teacher_service | 4101 |
| `api.huleedu.hule.education` | huleedu_api_gateway_service | 8080 |
| `ws.huleedu.hule.education` | huleedu_websocket_service | 8080 |

### Source: Skriptoteket

```bash
ssh hemma "curl -s https://skriptoteket.hule.education/healthz"
```

### Source: HuleEdu

```bash

### Source: BFF (frontend)

ssh hemma "curl -s https://huleedu.hule.education/healthz"

### Source: API Gateway

ssh hemma "curl -s https://api.huleedu.hule.education/healthz"

### Source: Internal services (from within network)

ssh hemma "docker exec huleedu_api_gateway_service curl -s http://content_service:8000/healthz"
```

### Source: GPU Services

```bash
ssh hemma "curl -s http://localhost:8082/health"
ssh hemma "curl -s http://localhost:8083/v1/health | jq .model"
```

### Source: Service Can't Reach shared-postgres

```bash

### Source: Check network connectivity

ssh hemma "docker exec huleedu_content_service ping -c 1 shared-postgres"

### Source: Verify service is on hule-network

ssh hemma "docker inspect huleedu_content_service | jq '.[0].NetworkSettings.Networks'"
```

### Source: GPU Not Accessible from Container

```bash

### Source: Check extra_hosts is set

ssh hemma "docker exec huleedu_nlp_service cat /etc/hosts | grep host.docker.internal"

### Source: Test connectivity

ssh hemma "docker exec huleedu_nlp_service curl -s http://host.docker.internal:8082/health"
```

### Source: Database Connection Errors

```bash

### Source: Check ENVIRONMENT is set to production

ssh hemma "docker exec huleedu_content_service printenv | grep ENVIRONMENT"

### Source: Should be: ENVIRONMENT=production



### Source: Check prod DB vars are set

ssh hemma "docker exec huleedu_content_service printenv | grep HULEEDU_PROD"
```

### Source: Kafka/Redis Issues

```bash

### Source: Check Kafka is healthy

ssh hemma "docker exec huleedu_kafka kafka-topics.sh --bootstrap-server localhost:9092 --list"

### Source: Check Redis

ssh hemma "docker exec huleedu_redis redis-cli ping"
```

### Source: Restart All HuleEdu Services

```bash
ssh hemma "cd ~/apps/huleedu && docker compose -f docker-compose.yml -f docker-compose.prod.yml restart"
```

### Source: View Logs

```bash

### Source: Specific service

ssh hemma "docker logs -f huleedu_nlp_service --tail 100"

### Source: All services

ssh hemma "cd ~/apps/huleedu && docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f"
```

### Source: Database Backup

```bash

### Source: Run the governed all-DB shared-postgres backup from Hemma.

ssh hemma "cd /home/paunchygent/apps/huleedu && pdm run run-local-pdm shared-postgres-backup run --execute"
```

Production backup payloads belong under
`/srv/storage/hemma/shared-postgres/backups/`, not `~/backups`. Use the HuleEdu
`shared-postgres-backup verify --latest` and `restore-test --latest` commands
for manifest and restore proof before cross-product database work.

## Preconditions

The migrated source records no separate statement for this section.

## Steps

The migrated source records no separate statement for this section.

## Expected Results

The migrated source records no separate statement for this section.

## Stop Conditions

The migrated source records no separate statement for this section.

## Rollback

The migrated source records no separate statement for this section.
