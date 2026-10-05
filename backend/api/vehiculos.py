"""
Router: /vehiculos
Full CRUD for the Vehiculo model plus statistics and public catalogue endpoints.
All prices in COP.

Vehiculo column reference (from backend.models.vehiculo):
  id, marca, modelo, año, placa,
  precio_compra, precio_venta, precio_mercado,
  kilometraje, transmision, combustible, color, cilindraje, num_dueños, tipo_vehiculo,
  ciudad, estado, estado_mecanico,
  soat_vigente, tecnicomecanica_vigente, impuestos_al_dia, libre_prendas,
  descripcion, fotos (JSON list), fuente, url_fuente,
  margen_estimado (%), score_oportunidad (0-100),
  fecha_compra, fecha_venta, fecha_publicacion,
  created_at, updated_at
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import os
import shutil
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import require_admin
from backend.models.database import get_db
from backend.models import Vehiculo

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

ESTADOS_VALIDOS = {"disponible", "vendido", "en_proceso", "reservado"}
TRANSMISIONES_VALIDAS = {"automatica", "mecanica", "cvt", "semiautomatica"}
COMBUSTIBLES_VALIDOS = {"gasolina", "diesel", "hibrido", "electrico", "gas"}


class VehiculoBase(BaseModel):
    marca: str = Field(..., min_length=1, max_length=100, examples=["Toyota"])
    modelo: str = Field(..., min_length=1, max_length=100, examples=["Corolla"])
    año: int = Field(..., ge=1990, le=2030, examples=[2020])
    tipo_vehiculo: str = Field(..., examples=["Sedan"], description="SUV | Sedan | Hatchback | Camioneta | Pick-up")
    placa: Optional[str] = Field(None, max_length=20)
    color: str = Field(..., max_length=50, examples=["Blanco"])
    kilometraje: int = Field(..., ge=0, examples=[45000])
    transmision: str = Field(..., examples=["automatica"], description="automatica | mecanica | cvt | semiautomatica")
    combustible: str = Field(..., examples=["gasolina"], description="gasolina | diesel | hibrido | electrico | gas")
    cilindraje: Optional[int] = Field(None, ge=0, description="Cilindrada en cc")
    num_dueños: Optional[int] = Field(None, ge=1)
    ciudad: str = Field("Bogotá", max_length=100)
    precio_compra: Optional[float] = Field(None, ge=0, description="Precio de compra en COP")
    precio_venta: Optional[float] = Field(None, ge=0, description="Precio de venta en COP")
    precio_mercado: Optional[float] = Field(None, ge=0, description="Precio referencia de mercado en COP")
    estado: str = Field("disponible", examples=["disponible"])
    estado_mecanico: Optional[str] = Field(None, description="excelente | bueno | regular")
    soat_vigente: bool = False
    tecnicomecanica_vigente: bool = False
    impuestos_al_dia: bool = False
    libre_prendas: bool = True
    descripcion: Optional[str] = None
    fotos: Optional[list[str]] = Field(default_factory=list, description="URLs de fotos")
    fuente: Optional[str] = Field(None, max_length=50, description="tucarro | carroya | particular | subasta")
    url_fuente: Optional[str] = Field(None, max_length=500)
    margen_estimado: Optional[float] = Field(None, description="Margen estimado en %")
    score_oportunidad: Optional[float] = Field(None, ge=0, le=100, description="Score de oportunidad 0-100")
    fecha_compra: Optional[datetime] = None
    fecha_venta: Optional[datetime] = None
    fecha_publicacion: Optional[datetime] = None

    @field_validator("estado")
    @classmethod
    def estado_valido(cls, v: str) -> str:
        if v not in ESTADOS_VALIDOS:
            raise ValueError(f"estado debe ser uno de: {ESTADOS_VALIDOS}")
        return v

    @field_validator("transmision")
    @classmethod
    def transmision_valida(cls, v: str) -> str:
        if v.lower() not in TRANSMISIONES_VALIDAS:
            raise ValueError(f"transmision debe ser uno de: {TRANSMISIONES_VALIDAS}")
        return v.lower()

    @field_validator("combustible")
    @classmethod
    def combustible_valido(cls, v: str) -> str:
        if v.lower() not in COMBUSTIBLES_VALIDOS:
            raise ValueError(f"combustible debe ser uno de: {COMBUSTIBLES_VALIDOS}")
        return v.lower()


class VehiculoCreate(VehiculoBase):
    pass


class VehiculoUpdate(BaseModel):
    """All fields optional — PATCH-style update via PUT."""
    marca: Optional[str] = Field(None, min_length=1, max_length=100)
    modelo: Optional[str] = Field(None, min_length=1, max_length=100)
    año: Optional[int] = Field(None, ge=1990, le=2030)
    tipo_vehiculo: Optional[str] = None
    placa: Optional[str] = Field(None, max_length=20)
    color: Optional[str] = Field(None, max_length=50)
    kilometraje: Optional[int] = Field(None, ge=0)
    transmision: Optional[str] = None
    combustible: Optional[str] = None
    cilindraje: Optional[int] = Field(None, ge=0)
    num_dueños: Optional[int] = Field(None, ge=1)
    ciudad: Optional[str] = Field(None, max_length=100)
    precio_compra: Optional[float] = Field(None, ge=0)
    precio_venta: Optional[float] = Field(None, ge=0)
    precio_mercado: Optional[float] = Field(None, ge=0)
    estado: Optional[str] = None
    estado_mecanico: Optional[str] = None
    soat_vigente: Optional[bool] = None
    tecnicomecanica_vigente: Optional[bool] = None
    impuestos_al_dia: Optional[bool] = None
    libre_prendas: Optional[bool] = None
    descripcion: Optional[str] = None
    fotos: Optional[list[str]] = None
    fuente: Optional[str] = Field(None, max_length=50)
    url_fuente: Optional[str] = Field(None, max_length=500)
    margen_estimado: Optional[float] = None
    score_oportunidad: Optional[float] = Field(None, ge=0, le=100)
    fecha_compra: Optional[datetime] = None
    fecha_venta: Optional[datetime] = None
    fecha_publicacion: Optional[datetime] = None


class VehiculoOut(VehiculoBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Computed fields (not stored in DB)
    margen_bruto_cop: Optional[float] = None
    dias_en_inventario: Optional[int] = None

    model_config = {"from_attributes": True}


class VehiculoCatalogoOut(BaseModel):
    """Public-facing catalogue — purchase prices and internal info omitted."""
    id: int
    marca: str
    modelo: str
    año: int
    tipo_vehiculo: str
    color: str
    kilometraje: int
    transmision: str
    combustible: str
    cilindraje: Optional[int] = None
    ciudad: str
    precio_venta: Optional[float] = None
    descripcion: Optional[str] = None
    fotos: Optional[list[str]] = Field(default_factory=list)
    soat_vigente: bool
    tecnicomecanica_vigente: bool
    impuestos_al_dia: bool
    libre_prendas: bool
    estado: str

    model_config = {"from_attributes": True}


class VehiculoEstadisticas(BaseModel):
    total: int
    por_estado: dict[str, int]
    por_marca: dict[str, int]
    por_tipo: dict[str, int]
    margen_promedio_cop: Optional[float]
    margen_promedio_pct: Optional[float]
    valor_inventario_venta_cop: float
    valor_inventario_compra_cop: Optional[float]
    dias_promedio_inventario: Optional[float]
    score_oportunidad_promedio: Optional[float]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _compute_extras(v: Vehiculo) -> dict:
    """Compute derived fields not persisted in the DB."""
    # Gross margin in COP
    margen_bruto_cop: Optional[float] = None
    if v.precio_compra is not None and v.precio_venta is not None:
        margen_bruto_cop = v.precio_venta - v.precio_compra

    # Days in inventory
    dias_en_inventario: Optional[int] = None
    if v.fecha_compra:
        ref_date = (
            v.fecha_venta.date() if (v.estado == "vendido" and v.fecha_venta) else date.today()
        )
        compra_date = v.fecha_compra.date() if isinstance(v.fecha_compra, datetime) else v.fecha_compra
        dias_en_inventario = (ref_date - compra_date).days

    return {
        "margen_bruto_cop": margen_bruto_cop,
        "dias_en_inventario": dias_en_inventario,
    }


def _vehiculo_to_out(v: Vehiculo) -> dict:
    data = {c.name: getattr(v, c.name) for c in v.__table__.columns}
    data.update(_compute_extras(v))
    return data


# ---------------------------------------------------------------------------
# Endpoints — fixed-path routes MUST come before /{id} to avoid conflicts
# ---------------------------------------------------------------------------

@router.get(
    "/estadisticas",
    response_model=VehiculoEstadisticas,
    summary="Estadísticas del inventario",
    dependencies=[Depends(require_admin)],
)
async def estadisticas(db: AsyncSession = Depends(get_db)):
    """
    Aggregated inventory stats: total count, breakdown by estado / marca / tipo,
    average gross margin (COP and %), total inventory value, avg days on lot.
    """
    result = await db.execute(select(Vehiculo))
    vehiculos: list[Vehiculo] = result.scalars().all()

    total = len(vehiculos)
    por_estado: dict[str, int] = {}
    por_marca: dict[str, int] = {}
    por_tipo: dict[str, int] = {}
    valor_venta = 0.0
    valor_compra = 0.0
    margenes_cop: list[float] = []
    margenes_pct: list[float] = []
    dias_list: list[int] = []
    scores: list[float] = []

    for v in vehiculos:
        por_estado[v.estado] = por_estado.get(v.estado, 0) + 1
        por_marca[v.marca] = por_marca.get(v.marca, 0) + 1
        por_tipo[v.tipo_vehiculo] = por_tipo.get(v.tipo_vehiculo, 0) + 1

        if v.precio_venta:
            valor_venta += v.precio_venta
        if v.precio_compra:
            valor_compra += v.precio_compra
            if v.precio_venta:
                margen = v.precio_venta - v.precio_compra
                margenes_cop.append(margen)
                if v.precio_compra > 0:
                    margenes_pct.append(margen / v.precio_compra * 100)
        if v.score_oportunidad is not None:
            scores.append(v.score_oportunidad)

        extras = _compute_extras(v)
        if extras["dias_en_inventario"] is not None:
            dias_list.append(extras["dias_en_inventario"])

    return VehiculoEstadisticas(
        total=total,
        por_estado=por_estado,
        por_marca=por_marca,
        por_tipo=por_tipo,
        margen_promedio_cop=sum(margenes_cop) / len(margenes_cop) if margenes_cop else None,
        margen_promedio_pct=sum(margenes_pct) / len(margenes_pct) if margenes_pct else None,
        valor_inventario_venta_cop=valor_venta,
        valor_inventario_compra_cop=valor_compra if valor_compra > 0 else None,
        dias_promedio_inventario=sum(dias_list) / len(dias_list) if dias_list else None,
        score_oportunidad_promedio=sum(scores) / len(scores) if scores else None,
    )


@router.get(
    "/catalogo",
    response_model=list[VehiculoCatalogoOut],
    summary="Catálogo público (solo disponibles, sin precios de compra)",
)
async def catalogo(
    marca: Optional[str] = Query(None),
    tipo_vehiculo: Optional[str] = Query(None),
    anio_min: Optional[int] = Query(None, alias="anio_min"),
    anio_max: Optional[int] = Query(None, alias="anio_max"),
    precio_min: Optional[float] = Query(None),
    precio_max: Optional[float] = Query(None),
    km_max: Optional[int] = Query(None),
    ciudad: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Public vehicle catalogue — only 'disponible' vehicles are shown.
    Purchase prices, internal notes and scores are NOT included.
    """
    conditions = [Vehiculo.estado == "disponible"]
    if marca:
        conditions.append(func.lower(Vehiculo.marca) == marca.lower())
    if tipo_vehiculo:
        conditions.append(func.lower(Vehiculo.tipo_vehiculo) == tipo_vehiculo.lower())
    if anio_min:
        conditions.append(Vehiculo.año >= anio_min)
    if anio_max:
        conditions.append(Vehiculo.año <= anio_max)
    if precio_min is not None:
        conditions.append(Vehiculo.precio_venta >= precio_min)
    if precio_max is not None:
        conditions.append(Vehiculo.precio_venta <= precio_max)
    if km_max is not None:
        conditions.append(Vehiculo.kilometraje <= km_max)
    if ciudad:
        conditions.append(func.lower(Vehiculo.ciudad) == ciudad.lower())

    result = await db.execute(
        select(Vehiculo)
        .where(and_(*conditions))
        .order_by(Vehiculo.precio_venta)
    )
    return result.scalars().all()


@router.get(
    "/catalogo/{vehiculo_id}",
    response_model=VehiculoCatalogoOut,
    summary="Detalle público de un vehículo (sin precios de compra)",
)
async def catalogo_detalle(vehiculo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Vehiculo).where(Vehiculo.id == vehiculo_id, Vehiculo.estado != "vendido")
    )
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    return v


@router.get(
    "",
    response_model=list[VehiculoOut],
    summary="Listar vehículos (inventario interno)",
    dependencies=[Depends(require_admin)],
)
async def listar_vehiculos(
    marca: Optional[str] = Query(None),
    anio: Optional[int] = Query(None),
    precio_min: Optional[float] = Query(None),
    precio_max: Optional[float] = Query(None),
    tipo_vehiculo: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    km_max: Optional[int] = Query(None),
    ciudad: Optional[str] = Query(None),
    fuente: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Internal inventory list with all filters. Includes purchase prices and scores."""
    conditions = []
    if marca:
        conditions.append(func.lower(Vehiculo.marca) == marca.lower())
    if anio:
        conditions.append(Vehiculo.año == anio)
    if precio_min is not None:
        conditions.append(Vehiculo.precio_venta >= precio_min)
    if precio_max is not None:
        conditions.append(Vehiculo.precio_venta <= precio_max)
    if tipo_vehiculo:
        conditions.append(func.lower(Vehiculo.tipo_vehiculo) == tipo_vehiculo.lower())
    if estado:
        conditions.append(Vehiculo.estado == estado)
    if km_max is not None:
        conditions.append(Vehiculo.kilometraje <= km_max)
    if ciudad:
        conditions.append(func.lower(Vehiculo.ciudad) == ciudad.lower())
    if fuente:
        conditions.append(Vehiculo.fuente == fuente)

    stmt = select(Vehiculo)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.offset(skip).limit(limit).order_by(Vehiculo.id.desc())

    result = await db.execute(stmt)
    return [_vehiculo_to_out(v) for v in result.scalars().all()]


@router.get(
    "/{vehiculo_id}",
    response_model=VehiculoOut,
    summary="Obtener vehículo por ID",
    dependencies=[Depends(require_admin)],
)
async def obtener_vehiculo(vehiculo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehiculo).where(Vehiculo.id == vehiculo_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    return _vehiculo_to_out(v)


@router.post(
    "",
    response_model=VehiculoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear vehículo",
    dependencies=[Depends(require_admin)],
)
async def crear_vehiculo(payload: VehiculoCreate, db: AsyncSession = Depends(get_db)):
    # Check for duplicate placa if provided
    if payload.placa:
        dup = await db.execute(select(Vehiculo).where(Vehiculo.placa == payload.placa))
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un vehículo con la placa {payload.placa}",
            )
    v = Vehiculo(**payload.model_dump())
    db.add(v)
    await db.flush()
    await db.refresh(v)
    return _vehiculo_to_out(v)


@router.put(
    "/{vehiculo_id}",
    response_model=VehiculoOut,
    summary="Actualizar vehículo",
    dependencies=[Depends(require_admin)],
)
async def actualizar_vehiculo(
    vehiculo_id: int,
    payload: VehiculoUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Vehiculo).where(Vehiculo.id == vehiculo_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")

    updates = payload.model_dump(exclude_unset=True)

    # Check placa uniqueness if changing it
    if "placa" in updates and updates["placa"] and updates["placa"] != v.placa:
        dup = await db.execute(select(Vehiculo).where(Vehiculo.placa == updates["placa"]))
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un vehículo con la placa {updates['placa']}",
            )

    for field, value in updates.items():
        setattr(v, field, value)

    await db.flush()
    await db.refresh(v)
    return _vehiculo_to_out(v)


@router.post(
    "/{vehiculo_id}/fotos",
    response_model=VehiculoOut,
    summary="Subir fotos de un vehículo",
    dependencies=[Depends(require_admin)],
)
async def subir_fotos(
    vehiculo_id: int,
    files: list[UploadFile],
    db: AsyncSession = Depends(get_db),
):
    """
    Upload photos for a vehicle.

    - Accepted formats: jpg, jpeg, png, webp
    - Maximum 10 photos per vehicle (including existing ones)
    """
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    MAX_PHOTOS = 10

    # Fetch vehicle
    result = await db.execute(select(Vehiculo).where(Vehiculo.id == vehiculo_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")

    # Validate file types
    for f in files:
        ext = (f.filename or "").rsplit(".", 1)[-1].lower() if f.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido: '{f.filename}'. Solo se aceptan: {', '.join(ALLOWED_EXTENSIONS)}",
            )

    # Check max photos limit
    existing_photos: list[str] = v.fotos or []
    if len(existing_photos) + len(files) > MAX_PHOTOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Máximo {MAX_PHOTOS} fotos por vehículo. Actualmente hay {len(existing_photos)}, intentas subir {len(files)}.",
        )

    # Save files to disk
    upload_dir = os.path.join("uploads", "vehiculos", str(vehiculo_id))
    os.makedirs(upload_dir, exist_ok=True)

    new_urls: list[str] = []
    for f in files:
        # Never trust the client filename: generate our own to avoid path
        # traversal and accidental overwrites.
        ext = f.filename.rsplit(".", 1)[-1].lower()
        safe_name = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(upload_dir, safe_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
        url_path = f"/uploads/vehiculos/{vehiculo_id}/{safe_name}"
        new_urls.append(url_path)

    # Update vehicle's fotos field
    v.fotos = existing_photos + new_urls
    await db.flush()
    await db.refresh(v)
    return _vehiculo_to_out(v)


@router.delete(
    "/{vehiculo_id}/fotos",
    response_model=VehiculoOut,
    summary="Eliminar una foto de un vehículo",
    dependencies=[Depends(require_admin)],
)
async def eliminar_foto(
    vehiculo_id: int,
    url: str = Query(..., description="URL de la foto tal como aparece en `fotos`"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Vehiculo).where(Vehiculo.id == vehiculo_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")

    fotos: list[str] = list(v.fotos or [])
    if url not in fotos:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foto no encontrada")

    # Only delete files we own (inside this vehicle's upload folder)
    prefix = f"/uploads/vehiculos/{vehiculo_id}/"
    if url.startswith(prefix):
        file_path = os.path.join("uploads", "vehiculos", str(vehiculo_id), os.path.basename(url))
        if os.path.isfile(file_path):
            os.remove(file_path)

    fotos.remove(url)
    v.fotos = fotos
    await db.flush()
    await db.refresh(v)
    return _vehiculo_to_out(v)


@router.delete(
    "/{vehiculo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar vehículo",
    dependencies=[Depends(require_admin)],
)
async def eliminar_vehiculo(vehiculo_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vehiculo).where(Vehiculo.id == vehiculo_id))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehículo no encontrado")
    await db.delete(v)
