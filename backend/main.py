"""
AutoNegocio FastAPI application entry point.
Car buying/selling business in Bogota, Colombia.
"""

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config.settings import DEFAULT_SECRET_KEY, settings
from backend.models.database import engine, Base
from backend.scheduler import start_scheduler, stop_scheduler
from backend.services import storage

# Import routers
from backend.api.vehiculos import router as vehiculos_router
from backend.api.clientes import router as clientes_router
from backend.api.transacciones import router as transacciones_router
from backend.api.oportunidades import router as oportunidades_router
from backend.api.mercado import router as mercado_router
from backend.api.auth import router as auth_router
from backend.api.agentes import router as agentes_router
from backend.api.auth import require_admin


ON_VERCEL = bool(os.environ.get("VERCEL"))

if not settings.DEBUG and settings.SECRET_KEY == DEFAULT_SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY no configurada: define la variable de entorno SECRET_KEY en producción."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and start the scheduler (long-running servers only)."""
    if not ON_VERCEL:
        # Import all models so SQLAlchemy registers them before create_all.
        # On Vercel tables are created once with `python -m scripts.init_prod`.
        import backend.models  # noqa: F401

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Serverless functions can't run background jobs: there, Vercel Cron
        # calls /scraping/cron instead.
        start_scheduler()

    yield

    if not ON_VERCEL:
        stop_scheduler()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API REST para AutoNegocio — compra y venta de vehículos usados en Bogotá, Colombia. "
        "Gestión de inventario, clientes, transacciones y análisis de mercado."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — origins configurable via CORS_ORIGINS (comma-separated); "*" in dev
# ---------------------------------------------------------------------------
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(vehiculos_router, prefix="/vehiculos", tags=["Vehículos"])
app.include_router(clientes_router, prefix="/clientes", tags=["Clientes"])
app.include_router(transacciones_router, prefix="/transacciones", dependencies=[Depends(require_admin)], tags=["Transacciones"])
app.include_router(oportunidades_router, prefix="/oportunidades", dependencies=[Depends(require_admin)], tags=["Oportunidades"])
app.include_router(mercado_router, prefix="/mercado", dependencies=[Depends(require_admin)], tags=["Mercado"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(agentes_router, prefix="/agentes", dependencies=[Depends(require_admin)], tags=["Agentes IA"])

# ---------------------------------------------------------------------------
# Static files — uploaded vehicle images
# ---------------------------------------------------------------------------
# Only when photos are stored locally (development); in production they live
# in Supabase Storage and have absolute URLs.
if not storage.using_supabase() and not ON_VERCEL:
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------
@app.get("/", tags=["Info"])
async def root():
    """API health-check and general info."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "API REST para compra y venta de vehículos usados en Bogotá",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "vehiculos": "/vehiculos",
            "clientes": "/clientes",
            "transacciones": "/transacciones",
            "oportunidades": "/oportunidades",
            "mercado": "/mercado",
            "auth": "/auth",
            "scraping_trigger": "/scraping/trigger",
            "uploads": "/uploads",
        },
        "currency": "COP",
        "status": "running",
    }


@app.get("/health", tags=["Info"])
async def health():
    """Lightweight health-check for monitoring."""
    return {"status": "ok"}


@app.post(
    "/scraping/trigger",
    tags=["Scraping"],
    summary="Ejecutar scraping manualmente",
    dependencies=[Depends(require_admin)],
)
async def trigger_scraping():
    """Trigger a full scraping scan manually (outside the scheduled interval)."""
    from backend.models.database import ensure_tables
    from backend.scraping.scraper_manager import ScraperManager

    await ensure_tables()

    try:
        manager = ScraperManager()
        oportunidades = await manager.run()
        return {
            "status": "completed",
            "oportunidades_encontradas": len(oportunidades),
            "summary": manager.summary(oportunidades),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ejecutando scraping: {str(exc)}",
        )


@app.get("/scraping/cron", tags=["Scraping"], include_in_schema=False)
async def scraping_cron(authorization: str | None = Header(None)):
    """Entry point for Vercel Cron (see vercel.json). Protected by CRON_SECRET."""
    if not settings.CRON_SECRET or authorization != f"Bearer {settings.CRON_SECRET}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")
    return await trigger_scraping()
