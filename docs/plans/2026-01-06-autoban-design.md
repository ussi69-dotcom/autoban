# AutoBan - Autonomous Multi-Agent Kanban Platform

**Generated:** 2026-01-06
**Status:** Approved for Implementation

## Overview

AutoBan je hybridní platforma kombinující sílu oh-my-opencode multi-agent orchestrace s enterprise-grade web UI a kanban task managementem.

### Key Decisions

- **Deployment**: Hybrid (CLI for power, Web UI for visualization)
- **Target**: Enterprise/larger teams (OAuth, RBAC, audit logs, tenant isolation)
- **Tech Stack**: Next.js + Python FastAPI + PostgreSQL
- **Agent Execution**: Agent Pool on server (long-lived processes)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AUTOBAN PLATFORM                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Web UI    │  │   CLI Tool  │  │   VS Code Extension     │  │
│  │  (Next.js)  │  │  (optional) │  │      (future)           │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                │
│         └────────────────┼─────────────────────┘                │
│                          ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              API Gateway (FastAPI + WebSocket)            │  │
│  │         Auth │ RBAC │ Rate Limit │ Audit Log              │  │
│  └───────────────────────────────────────────────────────────┘  │
│         │              │              │              │          │
│         ▼              ▼              ▼              ▼          │
│  ┌──────────┐  ┌──────────────┐  ┌─────────┐  ┌────────────┐   │
│  │  Agent   │  │    Task      │  │ Project │  │  Session   │   │
│  │  Pool    │  │   Manager    │  │ Manager │  │  Manager   │   │
│  │ Manager  │  │   (Kanban)   │  │         │  │            │   │
│  └──────────┘  └──────────────┘  └─────────┘  └────────────┘   │
│         │              │              │              │          │
│         └──────────────┴──────────────┴──────────────┘          │
│                          ▼                                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   PostgreSQL Database                     │  │
│  │   Users │ Projects │ Tasks │ Sessions │ Audit │ Memory    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Tech Stack

- **Frontend**: Next.js 14 + TypeScript + Tailwind + shadcn/ui
- **Backend**: Python FastAPI + async SQLAlchemy
- **Database**: PostgreSQL (multi-tenant ready)
- **Real-time**: WebSocket pro live agent updates
- **Auth**: OAuth2 (GitHub, Google) + API keys
- **Agent Runtime**: Bun/Node.js procesy spravované Supervisord

---

## Agent Pool System

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT POOL MANAGER                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Agent Registry                         │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │   │
│  │  │Sisyphus │ │ Oracle  │ │Explore  │ │Frontend │ ...    │   │
│  │  │ (opus)  │ │(gpt-5.2)│ │ (grok)  │ │(gemini) │        │   │
│  │  │ IDLE    │ │ BUSY    │ │ IDLE    │ │ IDLE    │        │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Agent Lifecycle:                                               │
│  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐         │
│  │ INIT   │───▶│ IDLE   │───▶│ BUSY   │───▶│ IDLE   │         │
│  └────────┘    └────────┘    └────────┘    └────────┘         │
│       │                           │              │             │
│       │         ┌─────────┐       │              │             │
│       └────────▶│  ERROR  │◀──────┘              │             │
│                 └────┬────┘                      │             │
│                      │      ┌──────────┐         │             │
│                      └─────▶│ RESTART  │─────────┘             │
│                             └──────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Types

| Agent | Model | Role | Pool Size |
|-------|-------|------|-----------|
| Sisyphus | claude-opus-4-5 | Orchestrátor | 2-5 |
| Oracle | gpt-5.2 | Architekt, review | 1-3 |
| Explore | grok-code | Rychlé hledání | 3-8 |
| Frontend | gemini-3-pro | UI/UX specialist | 1-3 |
| Implement | claude-opus | Implementace | 2-5 |
| Fixer | claude-opus | Debugging | 1-3 |

### Key Features

| Feature | Description |
|---------|-------------|
| Auto-scaling | Min/max počet instancí per agent type |
| Health checks | Heartbeat každých 30s, auto-restart při selhání |
| Warm pool | Pre-spawned agenti pro nulovou latenci |
| Session affinity | Agent si pamatuje kontext projektu |
| Resource limits | CPU/RAM limity per agent |
| Priority queue | Urgent tasky předbíhají standardní |

---

## Web UI & Kanban System

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🏠 AutoBan    Projects ▼    Agents    Settings              [User ▼] [Logout]  │
├────────────────────────────────────────────┬────────────────────────────────────┤
│                                            │                                    │
│  📊 KANBAN BOARD            [+ New Task]   │  💬 OPENCODE TERMINAL              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │  ┌────────────────────────────────┐│
│  │  TODO    │ │IN PROGRESS│ │  DONE    │   │  │ Project: e-commerce-app       ││
│  │   (5)    │ │   (2)     │ │  (12)    │   │  │ Agent: Sisyphus 🟢            ││
│  ├──────────┤ ├──────────┤ ├──────────┤   │  ├────────────────────────────────┤│
│  │┌────────┐│ │┌────────┐│ │┌────────┐│   │  │                                ││
│  ││Add auth││ ││Fix cart││ ││User reg││   │  │ 👤 Potřebuju přidat platební   ││
│  ││────────││ ││────────││ │└────────┘│   │  │    bránu Stripe do checkoutu.  ││
│  ││🤖 Sisy ││ ││🔧 Fixer││ │┌────────┐│   │  │                                ││
│  │└────────┘│ │└────────┘│ ││API v2  ││   │  │ 🤖 Rozumím. Nejprve provedu    ││
│  │┌────────┐│ │          │ │└────────┘│   │  │    analýzu checkout flow...    ││
│  ││Refactor││ │          │ │          │   │  │                                ││
│  │└────────┘│ │          │ │          │   │  │    ✅ Analyzován checkout      ││
│  └──────────┘ └──────────┘ └──────────┘   │  │    ✅ Nalezeny 3 integr. body  ││
│                                            │  │    ✅ Stripe SDK kompatibilní ││
│  ─────────────────────────────────────────│  │                                ││
│  🤖 AGENT ACTIVITY                         │  │    Navrhuji rozdělit na 4     ││
│  ┌────────────────────────────────────┐   │  │    subtasky:                   ││
│  │ Sisyphus: Analyzing checkout...    │   │  │                                ││
│  │ > Reading src/checkout/index.ts    │   │  │    1. Stripe SDK setup         ││
│  │ > Found PaymentProvider interface  │   │  │    2. Payment form component   ││
│  │ > Checking existing payment...     │   │  │    3. Webhook handler          ││
│  │                              [Logs]│   │  │    4. Error handling + retry   ││
│  └────────────────────────────────────┘   │  │                                ││
│                                            │  │ 👤 Super, zadej to do kanbanu ││
│  📁 FILES CHANGED                          │  │                                ││
│  ┌────────────────────────────────────┐   │  │ 🤖 Vytvářím tasky...           ││
│  │ M src/checkout/payment.ts     +45  │   │  │    ✅ Created: Stripe SDK      ││
│  │ A src/stripe/client.ts        +120 │   │  │    ✅ Created: Payment form    ││
│  │ M package.json                +2   │   │  │    ✅ Created: Webhook handler ││
│  │                        [View Diff] │   │  │    ✅ Created: Error handling  ││
│  └────────────────────────────────────┘   │  │                                ││
│                                            │  │ 📋 4 tasky přidány do TODO    ││
│                                            │  ├────────────────────────────────┤│
│                                            │  │ > Spusť první task_           ││
│                                            │  └────────────────────────────────┘│
└────────────────────────────────────────────┴────────────────────────────────────┘
```

### OpenCode Terminal Features

| Feature | Description |
|---------|-------------|
| Context-aware | Agent vidí aktuální projekt, repo, otevřené tasky |
| Kanban commands | `@kanban create`, `@kanban list`, `@kanban assign` |
| Auto-sync | Když agent vytvoří task, okamžitě se objeví v boardu |
| Research mode | Diskuze, plánování bez okamžité akce |
| Execute mode | "Zadej do kanbanu" → vytvoří skutečné tasky |
| History | Celá konverzace uložena, navazování |

### System Prompt Injection

```markdown
## KANBAN INTEGRATION

Máš přístup k Kanban boardu projektu {{project_name}}.

Dostupné nástroje:
- `kanban_list_tasks(status?)` - zobraz tasky
- `kanban_create_task(title, description, profile)` - vytvoř task
- `kanban_create_subtasks(tasks_json)` - batch vytvoření
- `kanban_update_task(id, status)` - změň status
- `kanban_assign_agent(task_id, agent)` - přiřaď agenta

Workflow:
1. Když uživatel řekne "zadej do kanbanu" → použij kanban_create_*
2. Když řekne "spusť task" → kanban_assign_agent + začni pracovat
3. Po dokončení → kanban_update_task(id, "done")
```

---

## Database Schema

```sql
-- ============================================
-- CORE ENTITIES
-- ============================================

-- Organizace (tenant isolation)
CREATE TABLE organizations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    plan            VARCHAR(50) DEFAULT 'free',
    settings        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Uživatelé
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    name            VARCHAR(255),
    avatar_url      TEXT,
    oauth_provider  VARCHAR(50),
    oauth_id        VARCHAR(255),
    api_key_hash    VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

-- Členství v organizaci
CREATE TABLE org_members (
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(50) NOT NULL,
    invited_by      UUID REFERENCES users(id),
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (org_id, user_id)
);

-- ============================================
-- PROJECTS & REPOSITORIES
-- ============================================

CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    settings        JSONB DEFAULT '{}',
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    archived_at     TIMESTAMPTZ
);

CREATE TABLE repositories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    git_url         TEXT NOT NULL,
    default_branch  VARCHAR(100) DEFAULT 'main',
    local_path      TEXT,
    last_synced_at  TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- KANBAN TASKS
-- ============================================

CREATE TYPE task_status AS ENUM (
    'backlog', 'todo', 'in_progress', 'in_review', 'done', 'cancelled'
);

CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high', 'urgent');

CREATE TABLE tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    parent_task_id  UUID REFERENCES tasks(id),

    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    status          task_status DEFAULT 'todo',
    priority        task_priority DEFAULT 'medium',

    recommended_profile  VARCHAR(50),
    assigned_agent_id    UUID,

    labels          TEXT[] DEFAULT '{}',
    estimated_mins  INTEGER,
    actual_mins     INTEGER,

    branch_name     VARCHAR(255),
    pr_url          TEXT,

    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX idx_tasks_parent ON tasks(parent_task_id);

-- ============================================
-- AGENT POOL & SESSIONS
-- ============================================

CREATE TYPE agent_status AS ENUM (
    'initializing', 'idle', 'busy', 'error', 'stopping', 'stopped'
);

CREATE TABLE agent_instances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type      VARCHAR(100) NOT NULL,
    model           VARCHAR(255) NOT NULL,
    status          agent_status DEFAULT 'initializing',

    pid             INTEGER,
    cpu_percent     REAL,
    memory_mb       REAL,

    current_task_id UUID REFERENCES tasks(id),
    current_session_id UUID,

    last_heartbeat  TIMESTAMPTZ,
    error_message   TEXT,
    restart_count   INTEGER DEFAULT 0,

    started_at      TIMESTAMPTZ DEFAULT NOW(),
    stopped_at      TIMESTAMPTZ
);

CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID REFERENCES agent_instances(id),
    task_id         UUID REFERENCES tasks(id),
    project_id      UUID REFERENCES projects(id),
    user_id         UUID REFERENCES users(id),

    status          VARCHAR(50) DEFAULT 'active',
    messages        JSONB DEFAULT '[]',
    tool_calls      INTEGER DEFAULT 0,
    tokens_used     INTEGER DEFAULT 0,

    parent_session_id UUID REFERENCES sessions(id),

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ
);

-- ============================================
-- SHARED MEMORY (Agent Knowledge Base)
-- ============================================

CREATE TABLE project_memory (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,

    memory_type     VARCHAR(50) NOT NULL,
    key             VARCHAR(255) NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(1536),

    source_task_id  UUID REFERENCES tasks(id),
    source_agent    VARCHAR(100),
    confidence      REAL DEFAULT 1.0,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,

    UNIQUE(project_id, memory_type, key)
);

CREATE INDEX idx_memory_embedding ON project_memory
    USING ivfflat (embedding vector_cosine_ops);

-- ============================================
-- AUDIT LOG
-- ============================================

CREATE TABLE audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID REFERENCES organizations(id),
    user_id         UUID REFERENCES users(id),
    agent_id        UUID REFERENCES agent_instances(id),

    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(50),
    resource_id     UUID,

    details         JSONB DEFAULT '{}',
    ip_address      INET,
    user_agent      TEXT,

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_org_time ON audit_log(org_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);

-- ============================================
-- GIT WORKTREES
-- ============================================

CREATE TABLE worktrees (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id         UUID REFERENCES repositories(id) ON DELETE CASCADE,
    task_id         UUID REFERENCES tasks(id),

    branch_name     VARCHAR(255) NOT NULL,
    local_path      TEXT NOT NULL,
    base_commit     VARCHAR(40),

    status          VARCHAR(50) DEFAULT 'active',

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    merged_at       TIMESTAMPTZ,
    deleted_at      TIMESTAMPTZ
);
```

---

## API Endpoints

### Authentication

```
POST /api/v1/auth/login          - OAuth login initiation
GET  /api/v1/auth/callback       - OAuth callback handler
POST /api/v1/auth/api-key        - Generate API key
POST /api/v1/auth/logout         - Invalidate session
```

### Organizations

```
GET    /api/v1/organizations                      - List user's organizations
POST   /api/v1/organizations                      - Create organization
GET    /api/v1/organizations/:org_id              - Get organization details
PUT    /api/v1/organizations/:org_id              - Update organization
DELETE /api/v1/organizations/:org_id              - Delete organization
GET    /api/v1/organizations/:org_id/members      - List members
POST   /api/v1/organizations/:org_id/members/invite - Invite member
DELETE /api/v1/organizations/:org_id/members/:user_id - Remove member
```

### Projects

```
GET    /api/v1/projects                           - List projects
POST   /api/v1/projects                           - Create project
GET    /api/v1/projects/:project_id               - Get project with stats
PUT    /api/v1/projects/:project_id               - Update project
DELETE /api/v1/projects/:project_id/archive       - Archive project
GET    /api/v1/projects/:project_id/repos         - List repositories
POST   /api/v1/projects/:project_id/repos         - Add repository
POST   /api/v1/projects/:project_id/repos/:id/sync - Sync repository
DELETE /api/v1/projects/:project_id/repos/:id     - Remove repository
```

### Tasks (Kanban)

```
GET    /api/v1/projects/:project_id/tasks         - List tasks (kanban board)
POST   /api/v1/projects/:project_id/tasks         - Create single task
POST   /api/v1/projects/:project_id/tasks/batch   - Create multiple tasks
GET    /api/v1/tasks/:task_id                     - Get task detail
PUT    /api/v1/tasks/:task_id                     - Update task
PATCH  /api/v1/tasks/:task_id/status              - Quick status change
POST   /api/v1/tasks/:task_id/assign              - Assign agent to task
DELETE /api/v1/tasks/:task_id                     - Delete task
```

### Agent Pool

```
GET    /api/v1/agents                             - List agent instances
POST   /api/v1/agents/spawn                       - Spawn new agent
GET    /api/v1/agents/:agent_id                   - Get agent details
POST   /api/v1/agents/:agent_id/stop              - Stop agent
POST   /api/v1/agents/:agent_id/restart           - Restart agent
GET    /api/v1/agents/:agent_id/logs              - Stream agent logs
```

### Sessions

```
GET    /api/v1/sessions                           - List sessions
GET    /api/v1/sessions/:session_id               - Get session with messages
POST   /api/v1/sessions                           - Create new session
POST   /api/v1/sessions/:session_id/messages      - Send message
POST   /api/v1/sessions/:session_id/cancel        - Cancel session
```

### Project Memory

```
GET    /api/v1/projects/:project_id/memory        - List memory entries
POST   /api/v1/projects/:project_id/memory        - Add memory entry
DELETE /api/v1/projects/:project_id/memory/:id    - Delete memory
POST   /api/v1/projects/:project_id/memory/search - Semantic search
```

### Git Worktrees

```
GET    /api/v1/projects/:project_id/worktrees     - List worktrees
POST   /api/v1/projects/:project_id/worktrees     - Create worktree
POST   /api/v1/worktrees/:worktree_id/merge       - Merge worktree
DELETE /api/v1/worktrees/:worktree_id             - Abandon worktree
```

### Audit Log

```
GET    /api/v1/organizations/:org_id/audit        - Query audit log
GET    /api/v1/organizations/:org_id/audit/export - Export audit log
```

---

## WebSocket Events

### Client → Server

```json
{ "type": "subscribe", "channel": "project:<project_id>" }
{ "type": "subscribe", "channel": "agent:<agent_id>:logs" }
{ "type": "subscribe", "channel": "session:<session_id>" }
{ "type": "session:message", "session_id": "<uuid>", "content": "..." }
{ "type": "unsubscribe", "channel": "..." }
```

### Server → Client

```json
{ "type": "task:updated", "task_id": "<uuid>", "changes": {...} }
{ "type": "agent:status", "agent_id": "<uuid>", "status": "busy" }
{ "type": "agent:log", "agent_id": "<uuid>", "message": "..." }
{ "type": "session:message", "session_id": "<uuid>", "role": "assistant", "content": "..." }
{ "type": "session:tool", "session_id": "<uuid>", "tool": "read_file", "status": "completed" }
{ "type": "background:completed", "parent_session_id": "<uuid>", "summary": "..." }
```

---

## Implementation Phases

### Phase 1: Agent Core (Priority: URGENT)
- Project setup (monorepo, Docker, PostgreSQL)
- Agent Pool Manager
- Core API (auth, organizations, projects, tasks)
- WebSocket server
- Session management
- Agent integration (oh-my-opencode adaptation)

### Phase 2: Web UI
- Next.js setup with Tailwind + shadcn/ui
- Authentication UI
- Dashboard
- Kanban board with drag-drop
- Integrated terminal
- Agent monitor

### Phase 3: Shared Memory & Autonomy
- pgvector setup
- Memory types and API
- Agent context injection
- Autonomy features
- Learning pipeline

### Phase 4: Kanban Deep Integration & Git Worktrees
- Advanced kanban (subtasks, dependencies)
- Git worktree management
- PR integration
- Verification pipeline
- Handover system

### Phase 5: QoL Features & Polish
- File operations
- Export/import
- Notifications (email, Slack, Discord)
- Analytics
- Plugin system
- Enterprise features (SSO, compliance)

---

## Phase 1 Tasks

| # | Task | Profile | Dependencies | Priority |
|---|------|---------|--------------|----------|
| 1.1.1 | Setup monorepo (Turborepo) | IMPLEMENT | - | URGENT |
| 1.1.2 | Docker Compose + PostgreSQL | IMPLEMENT | 1.1.1 | URGENT |
| 1.1.3 | FastAPI boilerplate + Alembic | IMPLEMENT | 1.1.2 | URGENT |
| 1.1.4 | Database schema migration | IMPLEMENT | 1.1.3 | URGENT |
| 1.2.1 | Agent Pool Manager class | IMPLEMENT | 1.1.3 | URGENT |
| 1.2.2 | Process spawning logic | IMPLEMENT | 1.2.1 | HIGH |
| 1.2.3 | Health check system | IMPLEMENT | 1.2.1 | HIGH |
| 1.2.4 | Resource monitoring | IMPLEMENT | 1.2.1 | MEDIUM |
| 1.3.1 | OAuth2 (GitHub) integration | IMPLEMENT | 1.1.3 | URGENT |
| 1.3.2 | OAuth2 (Google) integration | IMPLEMENT | 1.3.1 | HIGH |
| 1.3.3 | Organizations CRUD API | IMPLEMENT | 1.1.4 | HIGH |
| 1.3.4 | Projects CRUD API | IMPLEMENT | 1.3.3 | HIGH |
| 1.3.5 | Tasks CRUD API | IMPLEMENT | 1.3.4 | HIGH |
| 1.3.6 | Agents API endpoints | IMPLEMENT | 1.2.1 | HIGH |
| 1.4.1 | WebSocket connection manager | IMPLEMENT | 1.1.3 | URGENT |
| 1.4.2 | Channel subscription system | IMPLEMENT | 1.4.1 | HIGH |
| 1.4.3 | Agent log streaming | IMPLEMENT | 1.4.2, 1.2.1 | HIGH |
| 1.5.1 | Session model & API | IMPLEMENT | 1.3.5 | HIGH |
| 1.5.2 | Message routing | IMPLEMENT | 1.5.1, 1.2.1 | HIGH |
| 1.5.3 | Response streaming | IMPLEMENT | 1.5.2, 1.4.1 | HIGH |
| 1.6.1 | Agent runtime wrapper | IMPLEMENT | 1.2.1 | URGENT |
| 1.6.2 | oh-my-opencode adaptation | IMPLEMENT | 1.6.1 | HIGH |
| 1.6.3 | Sisyphus kanban awareness | IMPLEMENT | 1.6.2, 1.3.5 | HIGH |
| 1.6.4 | Background task support | IMPLEMENT | 1.6.2 | MEDIUM |

---

## Source Repositories

- **MyKanban**: https://github.com/ussi69-dotcom/MyKanban
- **oh-my-opencode**: https://github.com/code-yeongyu/oh-my-opencode
- **AutoBan (this project)**: https://github.com/ussi69-dotcom/autoban
