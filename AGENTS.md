# PROJECT KNOWLEDGE BASE

**Generated:** 2026-01-06
**Branch:** main

## OVERVIEW

AutoBan is an AI-powered Kanban board for autonomous software development. It combines project management with coding agents that can autonomously work on tasks.

**Monorepo Structure:**
- `packages/web` - Next.js 15 frontend with React Query, Zustand, TailwindCSS
- `packages/backend` - FastAPI backend with SQLAlchemy, PostgreSQL, Redis

## STRUCTURE
```
autoban/
├── packages/
│   ├── web/                    # Next.js frontend
│   │   ├── src/
│   │   │   ├── app/           # App Router pages
│   │   │   ├── components/    # React components
│   │   │   ├── hooks/         # React Query hooks
│   │   │   ├── lib/           # API client, utilities
│   │   │   └── stores/        # Zustand state
│   │   ├── public/
│   │   └── package.json
│   └── backend/                # FastAPI backend
│       ├── app/
│       │   ├── api/v1/        # API routes
│       │   ├── core/          # Auth, security
│       │   ├── models/        # SQLAlchemy models
│       │   └── services/      # Business logic
│       ├── alembic/           # DB migrations
│       └── requirements.txt
├── docker-compose.yml
├── turbo.json
└── package.json
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| API endpoints | `packages/backend/app/api/v1/` | FastAPI routers |
| API types | `packages/web/src/lib/api.ts` | TypeScript types & client |
| Data fetching | `packages/web/src/hooks/use-api.ts` | React Query hooks |
| UI components | `packages/web/src/components/` | React + Radix UI |
| Auth flow | `packages/backend/app/core/auth.py` | OAuth + JWT |
| DB models | `packages/backend/app/models/` | SQLAlchemy models |
| State management | `packages/web/src/stores/` | Zustand stores |
| Kanban board | `packages/web/src/components/kanban/` | DnD-kit based |

## CODE MAP

### Frontend Entry Points
- `packages/web/src/app/page.tsx` - Landing page
- `packages/web/src/app/(dashboard)/dashboard/page.tsx` - Main dashboard
- `packages/web/src/app/(dashboard)/[projectSlug]/page.tsx` - Project view

### Backend Entry Points
- `packages/backend/app/main.py` - FastAPI app initialization
- `packages/backend/app/api/v1/` - All API routes

### Shared Patterns
- API responses: `{ data: T, meta?: { total, page, limit } }`
- API paths: `/api/v1/{resource}`
- Auth: JWT in HTTPOnly cookie, user info in readable cookie

## CONVENTIONS

### TypeScript/React
- Strict TypeScript, no `any`
- React Query for server state
- Zustand for client state
- Tailwind for styling
- `cn()` utility for class merging

### Python/FastAPI
- Type hints everywhere
- async/await for all I/O
- Pydantic for validation
- Dependency injection via `Depends()`

### API Design
- RESTful endpoints
- Consistent error format: `{ message, code, status, details? }`
- Pagination via query params: `page`, `limit`

## ANTI-PATTERNS (THIS PROJECT)

- Don't use `/api/` prefix alone - always `/api/v1/`
- Don't call `organizations.list()` - projects are fetched directly for current user
- Don't use bare `fetch()` - use `api` client from `@/lib/api`
- Don't manage server state in Zustand - use React Query

## UNIQUE STYLES

- Task statuses: `backlog`, `ready`, `in_progress`, `in_review`, `done`, `blocked`
- Agent types: `sisyphus`, `oracle`, `explore`, `frontend`, `implement`, `fixer`, `librarian`, `document-writer`
- All dates are ISO 8601 strings

## COMMANDS

```bash
# Development (Docker)
npm run docker:up         # Start all services
npm run docker:down       # Stop services
npm run docker:logs       # View logs

# Database
npm run db:migrate        # Run migrations
npm run db:generate       # Generate migration

# Testing
cd packages/backend && pytest
cd packages/web && npm run type-check

# Build
npm run build             # Build all packages
```

## NOTES

### Docker Ports
- Frontend: 3002 (maps to 3000 internal)
- Backend: 8001 (maps to 8000 internal)
- PostgreSQL: 5433 (maps to 5432 internal)
- Redis: 6380 (maps to 6379 internal)

### OAuth Setup Required
GitHub and Google OAuth need client ID/secret in environment variables.

### Database
PostgreSQL 16 with pgvector extension enabled for future AI embeddings support.
