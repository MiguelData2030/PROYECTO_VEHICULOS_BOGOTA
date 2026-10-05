"""
Seed the database with sample vehicles for development/demo.
Run: python -m scripts.seed_db
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.database import engine, Base, AsyncSessionLocal
from backend.models.vehiculo import Vehiculo


VEHICULOS = [
    {
        "marca": "Mazda", "modelo": "CX-5 Grand Touring", "año": 2023,
        "precio_compra": 128000000, "precio_venta": 145000000, "precio_mercado": 148000000,
        "kilometraje": 15000, "transmision": "automatica", "combustible": "gasolina",
        "color": "Rojo Cristal", "tipo_vehiculo": "SUV", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "excelente",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 1, "cilindraje": 2500,
        "descripcion": "Mazda CX-5 Grand Touring en excelente estado. Único dueño, todos los mantenimientos en concesionario. Techo panorámico, cuero, sensores de parqueo, cámara de reversa.",
        "fuente": "particular", "score_oportunidad": 78,
    },
    {
        "marca": "Toyota", "modelo": "Fortuner 2.7L", "año": 2022,
        "precio_compra": 162000000, "precio_venta": 185000000, "precio_mercado": 190000000,
        "kilometraje": 32000, "transmision": "automatica", "combustible": "gasolina",
        "color": "Blanco Perlado", "tipo_vehiculo": "SUV", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "excelente",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 2, "cilindraje": 2700,
        "descripcion": "Toyota Fortuner en perfecto estado mecánico y estético. Segundo dueño, vidrios blindados nivel 2. Ideal para familia.",
        "fuente": "particular", "score_oportunidad": 85,
    },
    {
        "marca": "Chevrolet", "modelo": "Tracker LT", "año": 2024,
        "precio_compra": 85000000, "precio_venta": 98000000, "precio_mercado": 102000000,
        "kilometraje": 5200, "transmision": "automatica", "combustible": "gasolina",
        "color": "Gris Oscuro", "tipo_vehiculo": "SUV", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "excelente",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 1, "cilindraje": 1200,
        "descripcion": "Chevrolet Tracker último modelo, prácticamente nueva. Apple CarPlay, Android Auto, asistente de frenado. Garantía de fábrica vigente.",
        "fuente": "tucarro", "score_oportunidad": 72,
    },
    {
        "marca": "Kia", "modelo": "Sportage EX", "año": 2023,
        "precio_compra": 112000000, "precio_venta": 128000000, "precio_mercado": 135000000,
        "kilometraje": 18500, "transmision": "automatica", "combustible": "gasolina",
        "color": "Negro", "tipo_vehiculo": "SUV", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "excelente",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 1, "cilindraje": 2000,
        "descripcion": "Kia Sportage nueva generación. Diseño renovado, pantalla dual, asientos en cuero sintético, sistema de navegación. Impecable.",
        "fuente": "carroya", "score_oportunidad": 75,
    },
    {
        "marca": "Renault", "modelo": "Duster Intens", "año": 2023,
        "precio_compra": 67000000, "precio_venta": 78000000, "precio_mercado": 82000000,
        "kilometraje": 22000, "transmision": "mecanica", "combustible": "gasolina",
        "color": "Azul", "tipo_vehiculo": "SUV", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "bueno",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 1, "cilindraje": 1600,
        "descripcion": "Renault Duster versión Intens con multimedia, cámara de reversa, control crucero. Excelente relación calidad-precio.",
        "fuente": "particular", "score_oportunidad": 68,
    },
    {
        "marca": "Hyundai", "modelo": "Tucson Limited", "año": 2022,
        "precio_compra": 120000000, "precio_venta": 138000000, "precio_mercado": 142000000,
        "kilometraje": 28000, "transmision": "automatica", "combustible": "gasolina",
        "color": "Plata", "tipo_vehiculo": "SUV", "ciudad": "Bogotá",
        "estado": "reservado", "estado_mecanico": "excelente",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 1, "cilindraje": 2000,
        "descripcion": "Hyundai Tucson versión full equipo. Techo panorámico, asientos ventilados, sistema Bluelink, cargador inalámbrico.",
        "fuente": "particular", "score_oportunidad": 80,
    },
    {
        "marca": "Mazda", "modelo": "3 Sedán Touring", "año": 2023,
        "precio_compra": 82000000, "precio_venta": 95000000, "precio_mercado": 98000000,
        "kilometraje": 12000, "transmision": "automatica", "combustible": "gasolina",
        "color": "Blanco Nieve", "tipo_vehiculo": "Sedan", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "excelente",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 1, "cilindraje": 2000,
        "descripcion": "Mazda 3 con el reconocido motor Skyactiv. Interior premium, excelente consumo de combustible, todos los sistemas de seguridad activos.",
        "fuente": "tucarro", "score_oportunidad": 74,
    },
    {
        "marca": "Toyota", "modelo": "Corolla SEG Hybrid", "año": 2024,
        "precio_compra": 118000000, "precio_venta": 135000000, "precio_mercado": 140000000,
        "kilometraje": 3800, "transmision": "automatica", "combustible": "hibrido",
        "color": "Gris Metálico", "tipo_vehiculo": "Sedan", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "excelente",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 1, "cilindraje": 1800,
        "descripcion": "Toyota Corolla Hybrid última generación. Consumo excepcional, Toyota Safety Sense completo, pantalla 10.5 pulgadas.",
        "fuente": "particular", "score_oportunidad": 82,
    },
    {
        "marca": "Chevrolet", "modelo": "Onix Turbo Premier", "año": 2023,
        "precio_compra": 62000000, "precio_venta": 72000000, "precio_mercado": 75000000,
        "kilometraje": 19000, "transmision": "automatica", "combustible": "gasolina",
        "color": "Rojo", "tipo_vehiculo": "Sedan", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "bueno",
        "soat_vigente": True, "tecnicomecanica_vigente": False, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 2, "cilindraje": 1000,
        "descripcion": "Chevrolet Onix Turbo versión Premier. Motor 1.0 turbo eficiente, Wi-Fi integrado, 6 airbags, control de estabilidad.",
        "fuente": "carroya", "score_oportunidad": 65,
    },
    {
        "marca": "Kia", "modelo": "Seltos Zenith", "año": 2023,
        "precio_compra": 94000000, "precio_venta": 108000000, "precio_mercado": 115000000,
        "kilometraje": 14500, "transmision": "automatica", "combustible": "gasolina",
        "color": "Verde Oliva", "tipo_vehiculo": "SUV", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "excelente",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 1, "cilindraje": 1600,
        "descripcion": "Kia Seltos versión tope de línea. Sistema UVO, pantalla 10.25\", sistema de sonido Bose, asistente de punto ciego.",
        "fuente": "tucarro", "score_oportunidad": 70,
    },
    {
        "marca": "Renault", "modelo": "Koleos Intens", "año": 2022,
        "precio_compra": 102000000, "precio_venta": 118000000, "precio_mercado": 122000000,
        "kilometraje": 35000, "transmision": "automatica", "combustible": "gasolina",
        "color": "Negro Estrella", "tipo_vehiculo": "SUV", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "bueno",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": False,
        "libre_prendas": True, "num_dueños": 2, "cilindraje": 2500,
        "descripcion": "Renault Koleos espaciosa y confortable. Tracción 4x4 disponible, asientos en cuero, techo panorámico, sistema R-Link.",
        "fuente": "particular", "score_oportunidad": 62,
    },
    {
        "marca": "Hyundai", "modelo": "Creta Premium", "año": 2024,
        "precio_compra": 91000000, "precio_venta": 105000000, "precio_mercado": 110000000,
        "kilometraje": 6800, "transmision": "automatica", "combustible": "gasolina",
        "color": "Azul Phantom", "tipo_vehiculo": "SUV", "ciudad": "Bogotá",
        "estado": "disponible", "estado_mecanico": "excelente",
        "soat_vigente": True, "tecnicomecanica_vigente": True, "impuestos_al_dia": True,
        "libre_prendas": True, "num_dueños": 1, "cilindraje": 1500,
        "descripcion": "Hyundai Creta nueva generación, versión Premium. Diseño moderno, pantalla flotante, sistema BlueLink, asistente de estacionamiento.",
        "fuente": "carroya", "score_oportunidad": 76,
    },
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        from sqlalchemy import select, func
        result = await session.execute(select(func.count()).select_from(Vehiculo))
        count = result.scalar()
        if count and count > 0:
            print(f"Database already has {count} vehicles. Skipping seed.")
            return

        for v_data in VEHICULOS:
            session.add(Vehiculo(**v_data))

        await session.commit()
        print(f"Seeded {len(VEHICULOS)} vehicles successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
