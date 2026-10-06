"""
Router: /redes (admin only) — social media performance and its impact on sales.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Publicacion, RedMetrica, Seguimiento, Vehiculo
from backend.models.crm import REDES
from backend.models.database import get_db

router = APIRouter()


@router.get("/resumen", summary="Desempeño de redes sociales")
async def resumen(dias: int = Query(90, ge=7, le=365), db: AsyncSession = Depends(get_db)):
    hoy = date.today()
    desde = hoy - timedelta(days=dias - 1)
    filas = (await db.execute(
        select(RedMetrica).where(RedMetrica.fecha >= desde).order_by(RedMetrica.fecha)
    )).scalars().all()

    por_red: dict[str, list[RedMetrica]] = defaultdict(list)
    for f in filas:
        por_red[f.red].append(f)

    # Sales and leads that started on each social channel (from the CRM)
    segs = (await db.execute(select(Seguimiento).where(Seguimiento.canal.in_(REDES)))).scalars().all()
    limite = datetime.combine(desde, datetime.min.time(), tzinfo=timezone.utc)

    def creado(s):
        c = s.created_at
        return c if c.tzinfo else c.replace(tzinfo=timezone.utc)

    crm = defaultdict(lambda: {"leads_crm": 0, "ventas": 0, "valor_ventas": 0.0})
    for s in segs:
        if creado(s) >= limite:
            crm[s.canal]["leads_crm"] += 1
            if s.etapa == "ganado":
                crm[s.canal]["ventas"] += 1
                crm[s.canal]["valor_ventas"] += s.valor_estimado or 0

    redes = []
    for red in REDES:
        datos = por_red.get(red, [])
        if not datos:
            continue
        ini, fin = datos[0].seguidores, datos[-1].seguidores
        alcance = sum(d.alcance for d in datos)
        inter = sum(d.interacciones for d in datos)
        leads = sum(d.leads for d in datos)
        inversion = sum(d.inversion for d in datos)
        redes.append({
            "red": red,
            "seguidores": fin,
            "crecimiento": fin - ini,
            "crecimiento_pct": round((fin - ini) / ini * 100, 1) if ini else None,
            "alcance": alcance,
            "interacciones": inter,
            "engagement_pct": round(inter / alcance * 100, 2) if alcance else None,
            "mensajes": sum(d.mensajes for d in datos),
            "leads": leads,
            "inversion": inversion,
            "costo_por_lead": round(inversion / leads) if inversion and leads else None,
            **crm[red],
        })

    serie: dict[date, dict] = {}
    for f in filas:
        punto = serie.setdefault(f.fecha, {"fecha": f.fecha.isoformat(), "leads": 0, "alcance": 0})
        punto[f.red] = f.seguidores
        punto["leads"] += f.leads
        punto["alcance"] += f.alcance

    pubs = (await db.execute(
        select(Publicacion).where(Publicacion.fecha >= desde)
    )).scalars().all()
    v_ids = {p.vehiculo_id for p in pubs if p.vehiculo_id}
    vehiculos = {v.id: v for v in (await db.execute(select(Vehiculo).where(Vehiculo.id.in_(v_ids)))).scalars().all()} if v_ids else {}

    def pub_out(p: Publicacion) -> dict:
        v = vehiculos.get(p.vehiculo_id)
        inter = p.me_gusta + p.comentarios + p.compartidos + p.guardados
        return {
            "id": p.id, "red": p.red, "tipo": p.tipo, "titulo": p.titulo, "fecha": p.fecha.isoformat(),
            "alcance": p.alcance, "me_gusta": p.me_gusta, "comentarios": p.comentarios,
            "compartidos": p.compartidos, "guardados": p.guardados, "mensajes": p.mensajes, "leads": p.leads,
            "engagement_pct": round(inter / p.alcance * 100, 2) if p.alcance else None,
            "imagen": p.imagen, "vehiculo": f"{v.marca} {v.modelo} {v.año}" if v else None,
            "vehiculo_estado": v.estado if v else None,
        }

    top = sorted(pubs, key=lambda p: (p.leads, p.alcance), reverse=True)[:12]
    tipos = defaultdict(lambda: {"publicaciones": 0, "alcance": 0, "leads": 0})
    for p in pubs:
        t = tipos[f"{p.red}:{p.tipo}"]
        t["publicaciones"] += 1
        t["alcance"] += p.alcance
        t["leads"] += p.leads

    total_leads = sum(r["leads"] for r in redes)
    total_inv = sum(r["inversion"] for r in redes)
    return {
        "dias": dias,
        "totales": {
            "seguidores": sum(r["seguidores"] for r in redes),
            "crecimiento": sum(r["crecimiento"] for r in redes),
            "alcance": sum(r["alcance"] for r in redes),
            "leads": total_leads,
            "inversion": total_inv,
            "costo_por_lead": round(total_inv / total_leads) if total_inv and total_leads else None,
            "ventas_desde_redes": sum(r["ventas"] for r in redes),
            "valor_ventas_redes": sum(r["valor_ventas"] for r in redes),
        },
        "redes": redes,
        "serie": [serie[k] for k in sorted(serie)],
        "top_publicaciones": [pub_out(p) for p in top],
        "rendimiento_formato": sorted(
            ({"formato": k, **v, "leads_por_publicacion": round(v["leads"] / v["publicaciones"], 1)} for k, v in tipos.items()),
            key=lambda x: -x["leads_por_publicacion"],
        ),
    }
