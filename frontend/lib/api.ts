import axios from 'axios';
import type { Vehicle } from './data';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
});

// --- Types matching backend Pydantic schemas ---

export interface VehiculoCatalogo {
  id: number;
  marca: string;
  modelo: string;
  año: number;
  tipo_vehiculo: string;
  color: string;
  kilometraje: number;
  transmision: string;
  combustible: string;
  cilindraje: number | null;
  ciudad: string;
  precio_venta: number | null;
  descripcion: string | null;
  fotos: string[] | null;
  soat_vigente: boolean;
  tecnicomecanica_vigente: boolean;
  impuestos_al_dia: boolean;
  libre_prendas: boolean;
  estado: string;
}

export interface CatalogoFilters {
  marca?: string;
  tipo_vehiculo?: string;
  anio_min?: number;
  anio_max?: number;
  precio_min?: number;
  precio_max?: number;
  km_max?: number;
  ciudad?: string;
}

// --- Transform backend response to frontend Vehicle type ---

export function catalogoToVehicle(v: VehiculoCatalogo): Vehicle {
  return {
    id: v.id,
    marca: v.marca,
    modelo: v.modelo,
    anio: v.año,
    precio: v.precio_venta ?? 0,
    kilometraje: v.kilometraje,
    transmision: v.transmision === 'mecanica' ? 'Manual' : 'Automática',
    combustible: mapCombustible(v.combustible),
    tipo: mapTipo(v.tipo_vehiculo),
    color: v.color,
    ubicacion: v.ciudad,
    estado: mapEstado(v.estado),
    imagen: v.fotos && v.fotos.length > 0 ? v.fotos[0] : '/placeholder-car.jpg',
    descripcion: v.descripcion ?? '',
    soat: v.soat_vigente,
    tecnicomecanica: v.tecnicomecanica_vigente,
    impuestos: v.impuestos_al_dia,
  };
}

function mapCombustible(c: string): Vehicle['combustible'] {
  const map: Record<string, Vehicle['combustible']> = {
    gasolina: 'Gasolina',
    diesel: 'Diésel',
    hibrido: 'Híbrido',
    electrico: 'Eléctrico',
  };
  return map[c.toLowerCase()] ?? 'Gasolina';
}

function mapTipo(t: string): Vehicle['tipo'] {
  const map: Record<string, Vehicle['tipo']> = {
    suv: 'SUV',
    sedan: 'Sedán',
    hatchback: 'Hatchback',
    'pick-up': 'Pickup',
    pickup: 'Pickup',
    camioneta: 'Pickup',
    van: 'Van',
  };
  return map[t.toLowerCase()] ?? 'SUV';
}

function mapEstado(e: string): Vehicle['estado'] {
  const map: Record<string, Vehicle['estado']> = {
    disponible: 'Disponible',
    reservado: 'Reservado',
    vendido: 'Vendido',
    en_proceso: 'Reservado',
  };
  return map[e.toLowerCase()] ?? 'Disponible';
}

// --- API calls ---

export async function fetchCatalogo(filters: CatalogoFilters = {}): Promise<Vehicle[]> {
  const params: Record<string, string | number> = {};
  if (filters.marca) params.marca = filters.marca;
  if (filters.tipo_vehiculo) params.tipo_vehiculo = filters.tipo_vehiculo;
  if (filters.anio_min) params.anio_min = filters.anio_min;
  if (filters.anio_max) params.anio_max = filters.anio_max;
  if (filters.precio_min) params.precio_min = filters.precio_min;
  if (filters.precio_max) params.precio_max = filters.precio_max;
  if (filters.km_max) params.km_max = filters.km_max;
  if (filters.ciudad) params.ciudad = filters.ciudad;

  const { data } = await api.get<VehiculoCatalogo[]>('/vehiculos/catalogo', { params });
  return data.map(catalogoToVehicle);
}

export async function fetchVehiculo(id: number): Promise<Vehicle | null> {
  try {
    const { data } = await api.get<VehiculoCatalogo>(`/vehiculos/${id}`);
    return catalogoToVehicle(data);
  } catch {
    return null;
  }
}

export async function fetchEstadisticas() {
  const { data } = await api.get('/vehiculos/estadisticas');
  return data;
}
