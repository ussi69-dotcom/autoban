# AutoBan - Status Report

## Project Overview

**AutoBan** is an AI-powered Kanban board for autonomous software development with coding agents. It combines concepts from MyKanban and oh-my-opencode to create a platform where AI agents can autonomously work on tasks.

**Goal**: Build a fully functional Kanban board with OAuth authentication, project management, task management, and AI agent integration.

---

## Current State (2026-01-06)

### Working Features
- OAuth authentication with GitHub/Google (cookies, cross-origin)
- Project CRUD (create, read, update, delete)
- Task CRUD (create, read, update, delete, status change)
- Kanban board UI with drag-and-drop
- Dashboard with project overview
- User session management via cookies
- **Agent spawn API** (POST /api/v1/agents/spawn)
- **Agent list API** (GET /api/v1/agents)
- **Agent stop API** (POST /api/v1/agents/{id}/stop)
- **Agent UI components** (AgentList, AgentCard)

### Infrastructure
- Frontend: Next.js 15 on port 3002
- Backend: FastAPI on port 8001
- PostgreSQL on port 5433
- Redis on port 6380
- All running via Docker Compose

### Recent Session Summary (2026-01-06)

This session implemented agent spawning functionality through a multi-agent workflow:

**Subtasks executed via workspace sessions:**
- P1: E2E test flow (design)
- P2: Agent spawn backend - Database integration (CODEX)
- P3: Agent spawn API - REST endpoints (CODEX)
- P4: Task assignment to agents (CODEX)
- P5: Agent UI components (GEMINI)
- P6: Visual verification (CLAUDE)
- P7: Fix enum case issue (FIXER)

**Critical bug fixed:** SQLAlchemy enum serialization issue where PostgreSQL expected lowercase enum values ('idle', 'busy') but received uppercase ('IDLE', 'BUSY'). Fixed by adding `values_callable=lambda x: [e.value for e in x]` to the Enum definition.

---

## Completed Work

### 1. OAuth Flow Fixes
- Fixed cookie settings for cross-origin requests (`sameSite: 'none'`, `secure: true`)
- Set cookie domain to `.learnai.cz` for subdomain sharing
- Backend now reads JWT from both Authorization header AND cookies
- Files:
  - `packages/backend/app/api/v1/auth.py`
  - `packages/web/src/app/auth/callback/github/route.ts`

### 2. API Response Format Fixes
- Backend returns `{ items: [...] }` not `{ data: [...] }`
- Fixed all store functions to handle both formats
- Files:
  - `packages/web/src/stores/project.ts`
  - `packages/web/src/hooks/use-api.ts`

### 3. Backend Endpoint Implementations
- Implemented `update_task` endpoint with proper enum conversion
- Implemented `change_task_status` endpoint with timestamp tracking
- Implemented `delete_task` endpoint with cascade support
- Fixed enum conversion (API enums to model enums)
- Files:
  - `packages/backend/app/api/v1/tasks.py`

### 4. TaskStatus Enum Alignment
- Frontend used `ready`/`blocked`, backend uses `todo`/`cancelled`
- Updated all frontend files to match backend enums
- Files updated:
  - `packages/web/src/lib/api.ts`
  - `packages/web/src/stores/project.ts`
  - `packages/web/src/components/kanban/types.ts`
  - `packages/web/src/components/kanban/kanban-board.tsx`
  - `packages/web/src/components/kanban/kanban-column.tsx`
  - `packages/web/src/components/kanban/task-detail-dialog.tsx`
  - `packages/web/src/components/kanban/task-create-dialog.tsx`
  - `packages/web/src/app/(dashboard)/dashboard/page.tsx`

### 5. Missing Pages Created
- `/projects` - Project list page
- `/settings` - User settings page
- `/agents` - Agents overview page
- Files:
  - `packages/web/src/app/(dashboard)/projects/page.tsx`
  - `packages/web/src/app/(dashboard)/settings/page.tsx`
  - `packages/web/src/app/(dashboard)/agents/page.tsx`

### 6. Frontend API Client Fixes
- Changed agents list to use query param: `/api/v1/agents?project_id=X`
- Changed task move to POST `/api/v1/tasks/{id}/status`
- Files:
  - `packages/web/src/lib/api.ts`

---

## Key Files Reference

### Backend
| File | Purpose |
|------|---------|
| `packages/backend/app/api/v1/auth.py` | OAuth, JWT, cookie authentication |
| `packages/backend/app/api/v1/tasks.py` | Task CRUD, status changes |
| `packages/backend/app/api/v1/projects.py` | Project CRUD |
| `packages/backend/app/api/v1/agents.py` | Agent management |
| `packages/backend/app/models/task.py` | Task model with enums |
| `packages/backend/app/main.py` | FastAPI app entry |

### Frontend
| File | Purpose |
|------|---------|
| `packages/web/src/lib/api.ts` | API client, types, endpoints |
| `packages/web/src/stores/project.ts` | Zustand store for projects/tasks |
| `packages/web/src/hooks/use-api.ts` | React Query hooks |
| `packages/web/src/components/kanban/` | Kanban board components |
| `packages/web/src/app/(dashboard)/` | Dashboard pages |

### Config
| File | Purpose |
|------|---------|
| `docker-compose.yml` | Service orchestration |
| `CLAUDE.md` | Development instructions |
| `.env.example` | Environment variables template |

---

## Known Issues

1. **Cloudflare Access** - Production site has access gate requiring email auth

---

## Planned Next Steps

### High Priority
1. [x] ~~Test full user flow end-to-end~~ - DONE
2. [x] ~~Implement agent spawning functionality~~ - DONE
3. [ ] Connect agent spawn UI button to backend API
4. [ ] Implement real agent process spawning (currently only DB record)

### Medium Priority
5. [ ] Add real-time updates via WebSocket
6. [x] ~~Implement task assignment to agents~~ - DONE (API endpoint)
7. [ ] Add agent session/terminal UI
8. [ ] Implement task history tracking

### Low Priority
9. [ ] Add notification system
10. [ ] Implement theme switching (dark/light)
11. [ ] Add organization member management UI

---

## Environment Setup

```bash
# Start all services
npm run docker:up

# View logs
npm run docker:logs

# Restart specific service
docker compose restart backend
docker compose restart web

# Database migrations
npm run db:migrate
```

## URLs

- Frontend: http://localhost:3002
- Backend API: http://localhost:8001
- API Docs: http://localhost:8001/docs
- Production: https://autoban.learnai.cz (behind Cloudflare Access)

---

## Session Handoff

**Last working on**: Agent spawning implementation - completed backend API, DB integration, and UI components.

**Files modified this session:**
- `packages/backend/app/api/v1/agents.py` - Agent spawn/list/stop endpoints with DB integration
- `packages/backend/app/models/agent.py` - Fixed enum values_callable for PostgreSQL compatibility
- `packages/web/src/components/agents/agent-list.tsx` - Agent list UI component
- `packages/web/src/components/agents/agent-card.tsx` - Individual agent card component

**Verified working:**
- `POST /api/v1/agents/spawn` - Creates agent record in DB, returns agent data
- `GET /api/v1/agents` - Lists all agents with status counts
- `POST /api/v1/agents/{id}/stop` - Stops an agent (updates status to 'stopped')

**Next immediate action**: Connect frontend "Spawn Agent" button to backend API call.
