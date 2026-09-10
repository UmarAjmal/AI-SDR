from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.common.config import settings
from apps.api.routers import auth, workspaces, audit, usage, knowledge, crm, leads, email, campaigns, ai, webhooks, calendar, analytics

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Codenter AI SDR Platform - Multi-Tenant Autonomous Sales Development API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(workspaces.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(usage.router, prefix=settings.API_V1_STR)
app.include_router(knowledge.router, prefix=settings.API_V1_STR)
app.include_router(crm.router, prefix=settings.API_V1_STR)
app.include_router(leads.router, prefix=settings.API_V1_STR)
app.include_router(email.router, prefix=settings.API_V1_STR)
app.include_router(campaigns.router, prefix=settings.API_V1_STR)
app.include_router(ai.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router, prefix=settings.API_V1_STR)
app.include_router(calendar.router, prefix=settings.API_V1_STR)
app.include_router(analytics.router, prefix=settings.API_V1_STR)

@app.get("/", tags=["System"])
async def root():
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "docs_url": "http://127.0.0.1:8000/docs",
        "api_v1_prefix": settings.API_V1_STR,
        "frontend_url": "http://localhost:5173"
    }

@app.get("/healthz", tags=["System"])
async def healthz():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV
    }

@app.get("/live", tags=["System"])
async def live():
    return {"status": "alive"}
