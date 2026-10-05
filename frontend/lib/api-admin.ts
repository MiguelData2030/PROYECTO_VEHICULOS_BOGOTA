import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
});

// --- Estadísticas ---

export interface Estadisticas {
  total: number;
  por_estado: Record<string, number>;
  por_marca: Record<string, number>;
  por_tipo: Record<string, number>;
  margen_promedio_cop: number | null;
  margen_promedio_pct: number | null;
  valor_inventario_venta_cop: number;
  valor_inventario_compra_cop: number | null;
  dias_promedio_inventario: number | null;
  score_oportunidad_promedio: number | null;
}

export async function fetchEstadisticas(): Promise<Estadisticas> {
  const { data } = await api.get('/vehiculos/estadisticas');
  return data;
}

// --- Oportunidades ---

export interface Oportunidad {
  id: number;
  titulo: string;
  marca: string;
  modelo: string;
  año: number;
  precio: number;
  precio_mercado: number | null;
  score: number;
  estado: string;
  fuente: string;
  url: string | null;
  ciudad: string | null;
  created_at: string;
}

export async function fetchOportunidadesTop(): Promise<Oportunidad[]> {
  try {
    const { data } = await api.get('/oportunidades/top');
    return data;
  } catch {
    return [];
  }
}

export async function fetchOportunidadesStats() {
  try {
    const { data } = await api.get('/oportunidades/estadisticas');
    return data;
  } catch {
    return null;
  }
}

// --- Transacciones Dashboard ---

export interface DashboardKPIs {
  ventas_mes_actual: number;
  ingresos_mes_actual: number;
  ganancia_mes_actual: number;
  ventas_anio: number;
  ingresos_anio: number;
  ganancia_anio: number;
  margen_promedio_pct: number | null;
  vehiculos_en_inventario: number;
  dias_promedio_inventario: number | null;
  ticket_promedio: number | null;
}

export async function fetchDashboardKPIs(): Promise<DashboardKPIs | null> {
  try {
    const { data } = await api.get('/transacciones/dashboard');
    return data;
  } catch {
    return null;
  }
}

// --- Vehículos (inventario interno) ---

export interface VehiculoAdmin {
  id: number;
  marca: string;
  modelo: string;
  año: number;
  precio_compra: number | null;
  precio_venta: number | null;
  precio_mercado: number | null;
  kilometraje: number;
  estado: string;
  tipo_vehiculo: string;
  ciudad: string;
  fuente: string | null;
  score_oportunidad: number | null;
  margen_bruto_cop: number | null;
  dias_en_inventario: number | null;
  created_at: string;
}

export async function fetchInventario(): Promise<VehiculoAdmin[]> {
  try {
    const { data } = await api.get('/vehiculos?limit=500');
    return data;
  } catch {
    return [];
  }
}

// --- Scraping trigger ---

export async function triggerScraping(): Promise<boolean> {
  try {
    await api.post('/scraping/trigger');
    return true;
  } catch {
    return false;
  }
}
