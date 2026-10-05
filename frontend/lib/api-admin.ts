import axios from 'axios';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 15000,
});

// Attach the admin JWT to every request
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Expired/invalid session → back to login
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (typeof window !== 'undefined' && error?.response?.status === 401) {
      localStorage.removeItem('token');
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

/** Extract a readable message from a FastAPI error response. */
export function apiErrorMessage(error: unknown, fallback = 'Ocurrió un error'): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((d: { loc?: string[]; msg?: string }) => `${d.loc?.slice(-1)[0] ?? ''}: ${d.msg ?? ''}`)
        .join(' · ');
    }
  }
  return fallback;
}

export function fotoUrl(path: string): string {
  return path.startsWith('http') ? path : `${API_URL}${path}`;
}

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

export const ESTADOS_OPORTUNIDAD = [
  'nueva', 'contactada', 'negociando', 'comprada', 'descartada', 'expirada',
] as const;
export type EstadoOportunidad = (typeof ESTADOS_OPORTUNIDAD)[number];

export interface Oportunidad {
  id: number;
  url: string;
  plataforma: string;
  marca: string;
  modelo: string;
  año: number;
  kilometraje: number | null;
  ubicacion: string | null;
  precio_publicado: number;
  precio_mercado_estimado: number | null;
  descuento_porcentaje: number | null;
  score: number | null;
  descripcion_corta: string | null;
  estado: EstadoOportunidad;
  notas: string | null;
  detectada_en: string | null;
}

export async function fetchOportunidadesTop(): Promise<Oportunidad[]> {
  try {
    const { data } = await api.get('/oportunidades/top');
    return data;
  } catch {
    return [];
  }
}

export async function fetchOportunidades(params: {
  estado?: string;
  score_min?: number;
  marca?: string;
} = {}): Promise<Oportunidad[]> {
  const { data } = await api.get('/oportunidades', { params: { limit: 500, ...params } });
  return data;
}

export async function updateOportunidadEstado(
  id: number,
  estado: EstadoOportunidad,
  notas?: string,
): Promise<Oportunidad> {
  const { data } = await api.put(`/oportunidades/${id}/estado`, { estado, notas: notas || null });
  return data;
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

export const ESTADOS_VEHICULO = ['disponible', 'reservado', 'en_proceso', 'vendido'] as const;
export const TRANSMISIONES = ['automatica', 'mecanica', 'cvt', 'semiautomatica'] as const;
export const COMBUSTIBLES = ['gasolina', 'diesel', 'hibrido', 'electrico', 'gas'] as const;
export const TIPOS_VEHICULO = ['SUV', 'Sedan', 'Hatchback', 'Camioneta', 'Pick-up', 'Van'] as const;

export interface VehiculoInput {
  marca: string;
  modelo: string;
  año: number;
  tipo_vehiculo: string;
  placa: string | null;
  color: string;
  kilometraje: number;
  transmision: string;
  combustible: string;
  cilindraje: number | null;
  num_dueños: number | null;
  ciudad: string;
  precio_compra: number | null;
  precio_venta: number | null;
  precio_mercado: number | null;
  estado: string;
  estado_mecanico: string | null;
  soat_vigente: boolean;
  tecnicomecanica_vigente: boolean;
  impuestos_al_dia: boolean;
  libre_prendas: boolean;
  descripcion: string | null;
  fuente: string | null;
  fecha_compra: string | null;
}

export interface VehiculoAdmin extends VehiculoInput {
  id: number;
  fotos: string[] | null;
  url_fuente: string | null;
  margen_estimado: number | null;
  score_oportunidad: number | null;
  margen_bruto_cop: number | null;
  dias_en_inventario: number | null;
  fecha_venta: string | null;
  created_at: string;
}

export async function fetchInventario(): Promise<VehiculoAdmin[]> {
  try {
    const { data } = await api.get('/vehiculos', { params: { limit: 500 } });
    return data;
  } catch {
    return [];
  }
}

export async function createVehiculo(payload: VehiculoInput): Promise<VehiculoAdmin> {
  const { data } = await api.post('/vehiculos', payload);
  return data;
}

export async function updateVehiculo(id: number, payload: Partial<VehiculoInput>): Promise<VehiculoAdmin> {
  const { data } = await api.put(`/vehiculos/${id}`, payload);
  return data;
}

export async function deleteVehiculo(id: number): Promise<void> {
  await api.delete(`/vehiculos/${id}`);
}

export async function uploadFotos(id: number, files: File[]): Promise<VehiculoAdmin> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  const { data } = await api.post(`/vehiculos/${id}/fotos`, form, { timeout: 60000 });
  return data;
}

export async function deleteFoto(id: number, url: string): Promise<VehiculoAdmin> {
  const { data } = await api.delete(`/vehiculos/${id}/fotos`, { params: { url } });
  return data;
}

// --- Clientes / Leads ---

export interface Cliente {
  id: number;
  nombre: string;
  telefono: string | null;
  email: string | null;
  cedula: string | null;
  tipo: string;
  vehiculos_interes: Record<string, unknown>[] | null;
  presupuesto_min: number | null;
  presupuesto_max: number | null;
  notas: string | null;
  created_at: string | null;
}

export async function fetchClientes(tipo?: string): Promise<Cliente[]> {
  const { data } = await api.get<Cliente[]>('/clientes', {
    params: { limit: 500, ...(tipo ? { tipo } : {}) },
  });
  return data;
}

export async function deleteCliente(id: number): Promise<void> {
  await api.delete(`/clientes/${id}`);
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
