# AutoBan

AI-powered Kanban board for autonomous software development with coding agents.

## Instructions for Claude

### Load Up Context
Take a look at the app and architecture. Understand deeply how it works inside and out. Ask me any questions if there are things you don't understand. This will be the basis for the rest of our conversation.

### Tool Use Summaries
After completing a task that involves tool use, provide a quick summary of the work you've done.

### Adjust Eagerness Down
Do not jump into implementation or change files unless clearly instructed to make changes. When the user's intent is ambiguous, default to providing information, doing research, and providing recommendations rather than taking action. Only proceed with edits, modifications, or implementations when the user explicitly requests them.

### Use Parallel Tool Calls
If you intend to call multiple tools and there are no dependencies between the tool calls, make all of the independent tool calls in parallel. Prioritize calling tools simultaneously whenever the actions can be done in parallel rather than sequentially. For example, when reading 3 files, run 3 tool calls in parallel to read all 3 files into context at the same time. Maximize use of parallel tool calls where possible to increase speed and efficiency. However, if some tool calls depend on previous calls to inform dependent values like the parameters, do not call these tools in parallel and instead call them sequentially. Never use placeholders or guess missing parameters in tool calls.

### Reduce Hallucinations
Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Make sure to investigate and read relevant files BEFORE answering questions about the codebase. Never make any claims about code before investigating unless you are certain of the correct answer - give grounded and hallucination-free answers.

---

## Quick Reference

```bash
# Development
npm run docker:up        # Start all services (postgres, redis, backend, web)
npm run docker:down      # Stop all services
npm run docker:logs      # View logs

# Database
npm run db:migrate       # Run migrations
npm run db:generate      # Generate new migration

# Individual packages
cd packages/web && npm run dev      # Frontend only (needs backend running)
cd packages/backend && uvicorn app.main:app --reload  # Backend only
```

## Architecture

```
autoban/
├── packages/
│   ├── web/          # Next.js 15 frontend (React 18, TypeScript)
│   └── backend/      # FastAPI backend (Python 3.11+)
├── docker-compose.yml
└── turbo.json        # Turborepo config
```

### Services (docker-compose)

| Service  | Port  | Description |
|----------|-------|-------------|
| web      | 3002  | Next.js frontend |
| backend  | 8001  | FastAPI API server |
| postgres | 5433  | PostgreSQL with pgvector |
| redis    | 6380  | Redis cache |

## Frontend (packages/web)

### Tech Stack
- Next.js 15 with App Router
- React 18, TypeScript 5
- TailwindCSS, Radix UI components
- React Query (@tanstack/react-query) for data fetching
- Zustand for client state
- dnd-kit for drag-and-drop
- xterm.js for terminal UI

### Key Directories
```
src/
├── app/                    # Next.js App Router pages
│   ├── (auth)/            # Auth pages (login, register)
│   ├── (dashboard)/       # Protected dashboard pages
│   └── api/               # API routes (if any)
├── components/            # React components
│   ├── ui/               # Shadcn/Radix primitives
│   ├── kanban/           # Kanban board components
│   └── terminal/         # Agent terminal components
├── hooks/                # Custom React hooks
│   └── use-api.ts       # React Query hooks
├── lib/                  # Utilities
│   ├── api.ts           # API client with typed fetch
│   └── utils.ts         # Helper functions (cn, etc.)
└── stores/              # Zustand stores
    └── project.ts       # Project/task state
```

### API Client Pattern
```typescript
// All API calls go through src/lib/api.ts
import { api } from '@/lib/api'

// API paths use /api/v1/ prefix
const projects = await api.projects.list()
const task = await api.tasks.create({ projectId, title })
```

### Data Fetching Pattern
```typescript
// Use React Query hooks from src/hooks/use-api.ts
import { useProjects, useCreateProject } from '@/hooks/use-api'

const { data: projects, isLoading } = useProjects()
const createProject = useCreateProject()
await createProject.mutateAsync({ name: 'New Project' })
```

## Backend (packages/backend)

### Tech Stack
- FastAPI with async/await
- SQLAlchemy 2.0 with asyncpg
- Alembic for migrations
- PostgreSQL with pgvector extension
- Redis for caching/sessions
- JWT authentication (python-jose)

### Key Directories
```
app/
├── api/
│   └── v1/              # API version 1 routes
│       ├── projects.py  # Project CRUD
│       ├── tasks.py     # Task CRUD + move/assign
│       ├── agents.py    # Agent management
│       └── auth.py      # OAuth + JWT auth
├── core/
│   ├── auth.py         # JWT + OAuth helpers
│   └── security.py     # Password hashing
├── models/             # SQLAlchemy models
├── services/           # Business logic
├── config.py           # Settings from env
├── database.py         # DB session management
└── main.py             # FastAPI app entry
```

### API Patterns
```python
# All routes under /api/v1/
@router.get("/projects")
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Returns user's projects
```

### Response Format
```json
{
  "data": { ... },
  "meta": { "total": 10, "page": 1, "limit": 50 }
}
```

## Authentication

OAuth 2.0 with GitHub/Google providers:

1. Frontend redirects to `/api/v1/auth/{provider}`
2. User authenticates with provider
3. Backend creates/updates user, sets JWT cookie
4. Frontend reads user from cookie

JWT stored in `access_token` HTTPOnly cookie. User info in `user` cookie (readable by JS).

## Environment Variables

### Backend (.env or docker-compose)
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
REDIS_URL=redis://host:port/0
SECRET_KEY=your-jwt-secret
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

### Frontend
```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=ws://localhost:8001
NEXT_PUBLIC_APP_URL=http://localhost:3002
```

## Database

PostgreSQL 16 with pgvector for future AI embeddings.

### Migrations
```bash
cd packages/backend
alembic upgrade head           # Apply migrations
alembic revision --autogenerate -m "description"  # Generate
```

### Key Models
- `User` - OAuth users
- `Organization` - User organizations
- `Project` - Projects with tasks
- `Task` - Kanban tasks with status, priority, order
- `Agent` - Coding agents (sisyphus, oracle, etc.)
- `Session` - Agent work sessions

## Common Tasks

### Add a new API endpoint

1. Add route in `packages/backend/app/api/v1/`
2. Add types in `packages/web/src/lib/api.ts`
3. Add React Query hook in `packages/web/src/hooks/use-api.ts`

### Add a new UI component

1. Create in `packages/web/src/components/`
2. Use Radix UI primitives from `components/ui/`
3. Style with Tailwind classes

### Task Status Flow
```
backlog -> ready -> in_progress -> in_review -> done
                         |
                         v
                      blocked
```

## Code Style

### TypeScript
- Strict mode enabled
- Use `type` over `interface` for simple types
- Explicit return types on exported functions

### Python
- Type hints on all functions
- async/await for all DB operations
- Pydantic models for request/response validation

### Components
- Functional components with hooks
- Props destructuring
- Use `cn()` for conditional classes
