from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import get_settings
from app.database import init_db, close_db
from app.api.v1 import auth, organizations, projects, tasks, agents, sessions
from app.api.websocket import router as websocket_router
from app.services.agent_pool import AgentPoolManager

settings = get_settings()
logger = logging.getLogger(__name__)

# Global agent pool manager
agent_pool: AgentPoolManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    global agent_pool

    # Startup
    logger.info("Starting AutoBan API...")
    await init_db()

    # Initialize agent pool
    agent_pool = AgentPoolManager()
    await agent_pool.start()
    app.state.agent_pool = agent_pool

    logger.info("AutoBan API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down AutoBan API...")
    if agent_pool:
        await agent_pool.stop()
    await close_db()
    logger.info("AutoBan API shut down complete")


app = FastAPI(
    title=settings.app_name,
    description="Autonomous Multi-Agent Kanban Platform",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (routers already define their own prefixes like /auth, /organizations, etc.)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(organizations.router, prefix=settings.api_v1_prefix)
app.include_router(projects.router, prefix=settings.api_v1_prefix)
app.include_router(tasks.router, prefix=settings.api_v1_prefix)
app.include_router(agents.router, prefix=settings.api_v1_prefix)
app.include_router(sessions.router, prefix=settings.api_v1_prefix)

# WebSocket
app.include_router(websocket_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to AutoBan API",
        "docs": "/docs",
        "health": "/health"
    }
