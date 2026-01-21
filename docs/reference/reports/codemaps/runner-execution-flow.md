---
type: codemap
id: MAP-runner-execution-flow
title: "Runner Execution Flow: Frontend to Server and Back"
status: active
owners: "agents"
created: 2026-01-21
updated: 2026-01-21
topic: "runner execution"
links:
  - "ADR-0002"
  - "ADR-0038"
  - "ADR-0039"
  - "ADR-0044"
---

## Purpose

This codemap traces the complete runner execution flow from frontend user interaction through server processing, background queuing, Docker container execution, and result delivery back to the frontend.

## Quick Index (Code + Docs)

### Frontend (SPA)

- **Submission Hook**: `frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts`
- **Polling Mechanism**: `frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts`
- **Result View**: `frontend/apps/skriptoteket/src/views/tools/ToolRunView.vue`

### Backend (API & Application)

- **Tool Run Endpoint**: `src/skriptoteket/web/api/v1/tools.py`
- **Execution Handler**: `src/skriptoteket/application/scripting/handlers/execute_tool_version.py`
- **Execution Pipeline**: `src/skriptoteket/application/scripting/handlers/execute_tool_version_pipeline.py`

### Workers & Infrastructure

- **Queue Worker**: `src/skriptoteket/workers/execution_queue_worker.py`
- **Job Processor**: `src/skriptoteket/workers/execution_queue_job_processor.py`
- **Docker Runner**: `src/skriptoteket/infrastructure/runner/docker/runner.py`
- **Container Runner**: `runner/_runner.py`

---

## Execution Flow

### 1. Frontend Tool Submission

User submits tool execution through Vue.js frontend to FastAPI backend.

```text
Frontend Tool Submission Flow
├── User submits tool run <-- ToolRunView.vue:136
│   ├── submitRun() in useToolRun.ts <-- useToolRun.ts:137
│   │   └── API POST to /tools/{slug}/run
│   └── FastAPI endpoint handler <-- tools.py:209
│       └── start_tool_run() receives request
├── Request processing <-- tools.py:222
│   ├── Validate inputs & files <-- tools.py:234
│   └── Delegate to application handler
├── Initial response handling <-- useToolRun.ts:194
│   ├── Store run_id from response <-- useToolRun.ts:196
│   └── fetchRun() gets full run details
└── Real-time updates <-- useToolRun.ts:133
    ├── Check if running/queued status
    └── Start polling for execution results <-- useToolRun.ts:207
```

### 2. Server Request Processing

FastAPI handlers validate and process execution requests, deciding between direct execution or queuing.

```text
Server Request Processing Flow
├── ExecuteToolVersionHandler.handle()
│   ├── Check queue settings <-- execute_tool_version.py:154
│   ├── Decide execution path
│   │   ├── Queue execution path
│   │   │   ├── Create run record <-- execute_tool_version.py:183
│   │   │   └── Enqueue background job <-- execute_tool_version.py:201
│   │   └── Direct execution path
│   │       └── Call pipeline handler
│   └── Return response to API
└── execute_tool_version_pipeline()
    ├── Load & validate inputs
    ├── Execute tool via runner <-- execute_tool_version_pipeline.py:178
    └── Process & return results
```

### 3. Background Worker Processing

Execution queue workers claim and process background jobs.

```text
Background Worker Processing
├── run_execution_queue_worker() main loop <-- execution_queue_worker.py:34
│   ├── _claim_next_job() <-- execution_queue_worker.py:104
│   │   └── process_claim() <-- execution_queue_worker.py:117
│   │       ├── load_execution_context() <-- execution_queue_job_processor.py:77
│   │       │   └── loads tool/version/run data <-- execution_queue_job_db.py:15
│   │       ├── runner.execute() <-- execution_queue_job_processor.py:170
│   │       │   └── DockerToolRunner execution
│   │       └── finish_run() <-- execution_queue_job_processor.py:274
│   │           └── updates run with results
│   └── heartbeat loop for job leasing <-- execution_queue_job_processor.py:319
└── Worker lifecycle management <-- execution_queue_worker.py:56
    ├── container setup with DI
    └── lease TTL and polling config
```

### 4. Docker Container Execution

Docker runner creates isolated containers and executes user scripts.

```text
Docker Runner Execution Flow
├── DockerToolRunner.execute() entrypoint <-- runner.py:69
│   ├── Capacity management check <-- runner.py:80
│   └── Execute in thread pool <-- runner.py:94
│       └── _execute_sync() main logic <-- runner.py:359
│           ├── Initialize Docker client <-- runner.py:437
│           ├── Create Docker volume <-- runner.py:452
│           ├── Build workdir archive <-- runner.py:461
│           ├── Create container with limits <-- runner.py:467
│           ├── Upload work directory <-- runner.py:495
│           ├── Start container execution <-- runner.py:496
│           └── Container runs _runner.py
│               ├── Load user script module <-- _runner.py:166
│               ├── Find entrypoint function <-- _runner.py:168
│               └── Execute user script <-- _runner.py:172
```

### 5. Result Processing and Return

Container results are extracted, processed, and returned to frontend.

```text
Result Processing Chain
├── Container execution completes
│   ├── fetch_stdout_stderr() extracts logs <-- runner.py:515
│   │   └── fetch_result_json_bytes() reads JSON <-- runner.py:521
│   ├── store_output_archive() saves files <-- runner.py:637
│   └── Container writes result.json <-- _runner.py:191
├── Runner returns ToolExecutionResult
│   └── Job processor finalizes run <-- execution_queue_job_processor.py:274
│       └── Database updated with results <-- execution_queue_job_processor.py:296
└── Frontend polling mechanism
    ├── useToolRunPolling checks status
    │   └── API call to get run details
    └── UI updates with execution results <-- ToolRunView.vue:334
```

---

## Key Locations

| ID | Title | Path |
| -- | ----- | ---- |
| 1a | Submit tool run via API | `frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts:182` |
| 1b | Fetch initial run details | `frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts:203` |
| 1c | Start polling for updates | `frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts:206` |
| 1d | FastAPI endpoint handler | `src/skriptoteket/web/api/v1/tools.py:209` |
| 1e | Delegate to application handler | `src/skriptoteket/web/api/v1/tools.py:248` |
| 2a | Check queue configuration | `src/skriptoteket/application/scripting/handlers/execute_tool_version.py:154` |
| 2b | Create queued run record | `src/skriptoteket/application/scripting/handlers/execute_tool_version.py:183` |
| 2c | Enqueue background job | `src/skriptoteket/application/scripting/handlers/execute_tool_version.py:201` |
| 2d | Direct execution pipeline | `src/skriptoteket/application/scripting/handlers/execute_tool_version.py:242` |
| 2e | Call runner protocol | `src/skriptoteket/application/scripting/handlers/execute_tool_version_pipeline.py:178` |
| 3a | Claim next available job | `src/skriptoteket/workers/execution_queue_worker.py:104` |
| 3b | Process claimed job | `src/skriptoteket/workers/execution_queue_worker.py:117` |
| 3c | Load execution context | `src/skriptoteket/workers/execution_queue_job_processor.py:77` |
| 3d | Execute tool via runner | `src/skriptoteket/workers/execution_queue_job_processor.py:170` |
| 3e | Finalize run results | `src/skriptoteket/workers/execution_queue_job_processor.py:274` |
| 4a | Execute in thread pool | `src/skriptoteket/infrastructure/runner/docker/runner.py:94` |
| 4b | Initialize Docker client | `src/skriptoteket/infrastructure/runner/docker/runner.py:437` |
| 4c | Create Docker container | `src/skriptoteket/infrastructure/runner/docker/runner.py:467` |
| 4d | Upload work directory | `src/skriptoteket/infrastructure/runner/docker/runner.py:495` |
| 4e | Execute user script | `runner/_runner.py:172` |
| 5a | Extract stdout/stderr | `src/skriptoteket/infrastructure/runner/docker/runner.py:515` |
| 5b | Extract result JSON | `src/skriptoteket/infrastructure/runner/docker/runner.py:521` |
| 5c | Store output artifacts | `src/skriptoteket/infrastructure/runner/docker/runner.py:637` |
| 5d | Write result file | `runner/_runner.py:191` |
| 5e | Poll for run results | `frontend/apps/skriptoteket/src/composables/tools/useToolRun.ts:120` |
