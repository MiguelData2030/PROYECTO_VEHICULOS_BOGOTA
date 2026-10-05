"""
AutoNegocio FastAPI application entry point.
Car buying/selling business in Bogota, Colombia.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config.settings import settings
from backend.models.database import engine, Base
from backend.scheduler import start_scheduler, stop_scheduler

# Import routers
from backend.api.vehiculos import router as vehiculos_router
from backend.api.clientes import router as clientes_router
from backend.api.transacciones import router as transacciones_router
from backend.api.oportunidades import router as oportunidades_router
from backend.api.mercado import router as mercado_router
from backend.api.auth import router as auth_router
from backend.api.agentes import router as agentes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup; clean up on shutdown."""
    # Import all models so SQLAlchemy registers them before create_all
    import backend.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure uploads directory exists
    os.makedirs("uploads", exist_ok=True)

    # Start scraping scheduler
    start_scheduler()

    yield

    # Stop scheduler
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
# CORS — allow all origins for local development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(vehiculos_router, prefix="/vehiculos", tags=["Vehículos"])
app.include_router(clientes_router, prefix="/clientes", tags=["Clientes"])
app.include_router(transacciones_router, prefix="/transacciones", tags=["Transacciones"])
app.include_router(oportunidades_router, prefix="/oportunidades", tags=["Oportunidades"])
app.include_router(mercado_router, prefix="/mercado", tags=["Mercado"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(agentes_router, prefix="/agentes", tags=["Agentes IA"])

# ---------------------------------------------------------------------------
# Static files — uploaded vehicle images
# ---------------------------------------------------------------------------
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


@app.post("/scraping/trigger", tags=["Scraping"], summary="Ejecutar scraping manualmente")
async def trigger_scraping():
    """Trigger a full scraping scan manually (outside the scheduled interval)."""
    from backend.scraping.scraper_manager import ScraperManager

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
