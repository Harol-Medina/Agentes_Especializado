"""Software Archaeologist Analyzer — FastAPI application entrypoint.

Starts the FastAPI app, registers routers for every public endpoint,
adds CORS middleware for internal service communication, and exposes a
simple health check at GET /health.

Run locally (not recommended — use Docker):
    uvicorn src.main:app --reload --port 8000

Via Docker Compose:
    docker compose up analyzer
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import analyze, graph, jobs, query, report, kiro_spec
from src.api.schemas import HealthResponse
from src.config import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup → yield → shutdown."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Analyzer starting up (log_level=%s)", settings.log_level)
    # TODO (task 7.1): initialise asyncpg connection pool here
    yield
    # TODO (task 7.1): close asyncpg connection pool here
    logger.info("Analyzer shutting down")


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Software Archaeologist Analyzer",
    description=(
        "FastAPI service that executes the agent pipeline, builds dependency graphs, "
        "generates embeddings, and serves RAG-based chat for analysed repositories."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Allow calls from the Backend container and any local dev tooling.
# In production, restrict origins to the Backend service's internal hostname.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tightened via settings in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(analyze.router)
app.include_router(jobs.router)
app.include_router(query.router)
app.include_router(graph.router)
app.include_router(report.router)
app.include_router(kiro_spec.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Service health check",
)
async def health_check() -> HealthResponse:
    """Return a 200 OK confirming the service is running."""
    return HealthResponse(status="ok", service="analyzer")
