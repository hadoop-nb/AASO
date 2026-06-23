# AASO Roadmap: Phases 5 & 6

## Current State
Phases 1–4 complete. 92 tests pass. Stack: FastAPI + SQLAlchemy async + Qdrant + sentence-transformers + pluggable LLM providers.

## Phase 5: Autonomous Operations
Make AASO self-aware, cost-efficient, and operable without direct API calls.

### 5.1 Cost Intelligence
- `LLMCost` model tracking tokens/cost/model per LLM call
- `CostTracker` service recording every `generate()` call
- Per-project budget management
- Cost analytics API endpoints
- Integrate into `LLMService.generate()` — record cost after every call

### 5.2 Persistent Event Store
- `StoredEvent` model for DB-backed event sourcing
- Switchable `EventBus` backend (in-memory for tests, DB for prod)
- Event replay capability
- Audit trail via event history API

### 5.3 Agent Skill Registry + Dynamic Workforce
- `AgentSkill` model (capability, proficiency, agent_type)
- `AgentPool` — manages instances: active/busy/idle
- Load-based task dispatch to available agents
- Workforce API endpoints

### 5.4 Inter-Agent Collaboration
- Enhanced `MessageRouter` with conversation history
- Agent-to-agent delegation (request/response)
- Shared workspace (temporary context passing)

### 5.5 Basic Web Dashboard
- Jinja2 server-rendered HTML served by FastAPI
- Project overview with status
- Agent activity feed
- Cost/budget display
- Simple orchestration controls

## Phase 6: Organizational Intelligence
AASO learns from its own operations and improves autonomously.

### 6.1 Knowledge Graph
- `KnowledgeNode` / `KnowledgeEdge` models (node types: decision, lesson, task, code_file, project)
- `KnowledgeGraphService` with traversal queries (impact analysis, root cause)
- PostgreSQL adjacency list approach (no external graph DB)
- Graph visualization API

### 6.2 Meta-Agent (Organizational Learning)
- Analyzes past orchestration runs, pipeline results, feedback
- Generates retrospectives (daily/weekly)
- Mines failure patterns ("which task types fail most?")
- Suggests prompt/configuration improvements

### 6.3 Skill Evolution
- Agent self-assessment post-task
- Automatic lesson extraction from failures
- Prompt template versioning
- A/B testing of agent configurations

### 6.4 Executive Dashboard
- Real-time KPIs: quality trends, cost efficiency, agent performance, project health
- Historical trend charts
- Drill-down from org → project → task → agent run

### 6.5 Autonomous Planning Agent
- `PlanningAgent` generates work breakdown from high-level goals
- Dynamic re-prioritization based on context/blockers
- Risk assessment for tasks
- Self-scheduling: agents bid on tasks based on capability/availability
