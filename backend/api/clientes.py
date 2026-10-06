"""
Router: /clientes
CRUD for the Cliente model + text search.

Cliente column reference (from backend.models.cliente):
  id, nombre, telefono, email, cedula,
  tipo (comprador | vendedor | ambos),
  vehiculos_interes (JSON), presupuesto_min, presupuesto_max,
  notas, created_at, updated_at
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.auth import require_admin
from backend.models.database import get_db
from backend.models import Cliente

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

TIPOS_CLIENTE = {"comprador", "vendedor", "ambos"}


class ClienteBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=200, examples=["Carlos Pérez"])
    telefono: Optional[str] = Field(None, max_length=30, examples=["+57 300 123 4567"])
    email: Optional[EmailStr] = None
    cedula: Optional[str] = Field(None, max_length=30, description="Cédula o NIT")
    tipo: str = Field(
        "comprador",
        description="comprador | vendedor | ambos",
        examples=["comprador"],
    )
    vehiculos_interes: Optional[list[Any]] = Field(
        default_factory=list,
        description="Lista de criterios de búsqueda del cliente (dicts con marca, modelo, etc.)",
    )
    presupuesto_min: Optional[float] = Field(None, ge=0, description="Presupuesto mínimo en COP")
    presupuesto_max: Optional[float] = Field(None, ge=0, description="Presupuesto máximo en COP")
    notas: Optional[str] = None


class ClienteCreate(ClienteBase):
    # Set by the public website forms (web_vender | web_contacto): the lead is
    # also added to the CRM pipeline. Not stored on the client.
    origen: Optional[str] = Field(None, max_length=30)


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=200)
    telefono: Optional[str] = Field(None, max_length=30)
    email: Optional[EmailStr] = None
    cedula: Optional[str] = Field(None, max_length=30)
    tipo: Optional[str] = None
    vehiculos_interes: Optional[list[Any]] = None
    presupuesto_min: Optional[float] = Field(None, ge=0)
    presupuesto_max: Optional[float] = Field(None, ge=0)
    notas: Optional[str] = None


class ClienteOut(ClienteBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ClienteResumen(BaseModel):
    """Lightweight representation for lists and search results."""
    id: int
    nombre: str
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None
    cedula: Optional[str] = None
    tipo: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints — /buscar must be declared before /{id}
# ---------------------------------------------------------------------------

@router.get("/buscar", dependencies=[Depends(require_admin)], response_model=list[ClienteResumen], summary="Buscar clientes")
async def buscar_clientes(
    q: str = Query(..., min_length=2, description="Busca por nombre, teléfono o email"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Full-text search across nombre, telefono and email.
    Useful for frontend autocomplete / lookup.
    """
    term = f"%{q.lower()}%"
    stmt = (
        select(Cliente)
        .where(
            or_(
                func.lower(Cliente.nombre).like(term),
                Cliente.telefono.like(term),
                func.lower(Cliente.email).like(term),
            )
        )
        .limit(limit)
        .order_by(Cliente.nombre)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("", dependencies=[Depends(require_admin)], response_model=list[ClienteOut], summary="Listar clientes (más recientes primero)")
async def listar_clientes(
    tipo: Optional[str] = Query(None, description="comprador | vendedor | ambos"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if tipo:
        if tipo not in TIPOS_CLIENTE:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"tipo debe ser uno de: {TIPOS_CLIENTE}",
            )
        conditions.append(Cliente.tipo == tipo)

    stmt = select(Cliente)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(Cliente.created_at.desc(), Cliente.id.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{cliente_id}", dependencies=[Depends(require_admin)], response_model=ClienteOut, summary="Obtener cliente por ID")
async def obtener_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return c


@router.post(
    "",
    response_model=ClienteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crear cliente",
)
async def crear_cliente(payload: ClienteCreate, db: AsyncSession = Depends(get_db)):
    if payload.tipo not in TIPOS_CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tipo debe ser uno de: {TIPOS_CLIENTE}",
        )

    # Same phone → returning lead (e.g. the public /vender form submitted again).
    # Merge the new info into the existing record instead of rejecting it.
    if payload.telefono:
        dup = await db.execute(select(Cliente).where(Cliente.telefono == payload.telefono))
        existing = dup.scalar_one_or_none()
        if existing:
            if payload.notas:
                stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
                existing.notas = ((existing.notas or "") + f"\n[{stamp}] {payload.notas}").strip()
            if payload.vehiculos_interes:
                existing.vehiculos_interes = list(existing.vehiculos_interes or []) + payload.vehiculos_interes
            if payload.email and not existing.email:
                existing.email = payload.email
            if existing.tipo != payload.tipo and existing.tipo != "ambos":
                existing.tipo = "ambos"
            if payload.origen:
                from backend.api.crm import crear_seguimiento_web
                await crear_seguimiento_web(db, existing, payload.origen)
            await db.flush()
            await db.refresh(existing)
            return existing

    # Unique cedula check
    if payload.cedula:
        dup = await db.execute(select(Cliente).where(Cliente.cedula == payload.cedula))
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un cliente con la cédula {payload.cedula}",
            )

    c = Cliente(**payload.model_dump(exclude={"origen"}))
    db.add(c)
    await db.flush()
    if payload.origen:
        from backend.api.crm import crear_seguimiento_web
        await crear_seguimiento_web(db, c, payload.origen)
        await db.flush()
    await db.refresh(c)
    return c


@router.put("/{cliente_id}", dependencies=[Depends(require_admin)], response_model=ClienteOut, summary="Actualizar cliente")
async def actualizar_cliente(
    cliente_id: int,
    payload: ClienteUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")

    updates = payload.model_dump(exclude_unset=True)

    if "tipo" in updates and updates["tipo"] not in TIPOS_CLIENTE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tipo debe ser uno de: {TIPOS_CLIENTE}",
        )

    # Unique phone check if changing
    if "telefono" in updates and updates["telefono"] and updates["telefono"] != c.telefono:
        dup = await db.execute(select(Cliente).where(Cliente.telefono == updates["telefono"]))
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un cliente con el teléfono {updates['telefono']}",
            )

    # Unique cedula check if changing
    if "cedula" in updates and updates["cedula"] and updates["cedula"] != c.cedula:
        dup = await db.execute(select(Cliente).where(Cliente.cedula == updates["cedula"]))
        if dup.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un cliente con la cédula {updates['cedula']}",
            )

    for field, value in updates.items():
        setattr(c, field, value)

    await db.flush()
    await db.refresh(c)
    return c


@router.delete(
    "/{cliente_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar cliente",
    dependencies=[Depends(require_admin)],
)
async def eliminar_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cliente).where(Cliente.id == cliente_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    await db.delete(c)
