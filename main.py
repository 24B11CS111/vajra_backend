import os
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.llm.llm_provider import LLMFactory, LLMConfigurationError
from app.db.session import engine, Base

# Ensure all SQLAlchemy models are registered
import app.models.user
import app.models.chat
import app.models.memory
import app.models.planner
import app.models.notification
import app.models.study
import app.models.calendar

# Create tables if not exist (ensures initial schema availability)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    logging.warning(f"Metadata create_all exception (can happen if DB not ready): {e}")

setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=None if settings.is_production else f"{settings.API_V1_STR}/openapi.json",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

# Reverse proxy / forwarded headers support for cloud deployments (Render, Railway, Fly, Heroku)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Set up CORS
cors_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global structured exception handling for production safety
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error occurred. Please try again later."},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )

from app.api.v1.api import api_router

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": "vajra-api",
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
    }

@app.get("/ready", tags=["Health"])
def readiness_check():
    checks = {
        "database": False,
        "auth_configured": bool(settings.SUPABASE_JWT_SECRET),
        "llm_provider": settings.LLM_PROVIDER,
        "llm_configured": False,
    }

    # Verify live DB connection with lightweight ping
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            checks["database"] = True
    except Exception as e:
        logging.error(f"Database readiness check failed: {e}")
        checks["database"] = False

    try:
        LLMFactory.get_provider().validate_configuration()
        checks["llm_configured"] = True
    except LLMConfigurationError:
        checks["llm_configured"] = False
    except Exception:
        checks["llm_configured"] = False

    ready = checks["database"] and checks["auth_configured"] and checks["llm_configured"]
    status_code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=not settings.is_production)

