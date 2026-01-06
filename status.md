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

### Infrastructure
- Frontend: Next.js 15 on port 3002
- Backend: FastAPI on port 8001
- PostgreSQL on port 5433
- Redis on port 6380
- All running via Docker Compose

### Recent Session Summary

This session focused on fixing API integration issues between frontend and backend.

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

1. **Agent health checks failing** - Old agent records in DB without running processes
2. **Cloudflare Access** - Production site has access gate requiring email auth

---

## Planned Next Steps

### High Priority
1. [ ] Test full user flow end-to-end (create project, create task, move task, delete)
2. [ ] Fix any remaining API errors after TaskStatus alignment
3. [ ] Implement agent spawning functionality

### Medium Priority
4. [ ] Add real-time updates via WebSocket
5. [ ] Implement task assignment to agents
6. [ ] Add agent session/terminal UI
7. [ ] Implement task history tracking

### Low Priority
8. [ ] Add notification system
9. [ ] Implement theme switching (dark/light)
10. [ ] Add organization member management UI

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

**Last working on**: TaskStatus enum alignment fix - changed frontend from `ready`/`blocked` to `todo`/`cancelled` to match backend.

**Next immediate action**: Test task move operation to verify the fix works.
