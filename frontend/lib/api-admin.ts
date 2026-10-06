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

// --- Transacciones / KPIs del negocio ---

export interface MesKPI {
  mes: string; // YYYY-MM
  ventas: number;
  ingresos: number;
  ganancia: number;
  compras: number;
  inversion: number;
}

export interface DashboardKPIs {
  ventas_mes_actual: number;
  ingresos_mes_actual: number;
  ganancia_mes_actual: number;
  ventas_12m: number;
  ingresos_12m: number;
  ganancia_12m: number;
  margen_promedio_pct: number | null;
  ticket_promedio: number | null;
  dias_promedio_venta: number | null;
  vehiculos_en_inventario: number;
  valor_inventario_venta: number;
  capital_invertido: number;
  meses: MesKPI[];
  ventas_por_marca: Record<string, number>;
}

export async function fetchDashboardKPIs(): Promise<DashboardKPIs | null> {
  try {
    const { data } = await api.get('/transacciones/dashboard');
    return data;
  } catch {
    return null;
  }
}

export interface Transaccion {
  id: number;
  vehiculo_id: number;
  cliente_id: number;
  tipo: 'compra' | 'venta';
  precio: number;
  comision: number | null;
  gastos_traspaso: number | null;
  gastos_reacondicionamiento: number | null;
  ganancia_neta: number | null;
  margen_pct: number | null;
  fecha: string;
  notas: string | null;
  vehiculo_nombre: string | null;
  cliente_nombre: string | null;
  dias_en_inventario: number | null;
}

export async function fetchTransacciones(params: { tipo?: string; desde?: string; hasta?: string } = {}): Promise<Transaccion[]> {
  const { data } = await api.get('/transacciones', { params: { limit: 1000, ...params } });
  return data;
}

export interface TransaccionInput {
  vehiculo_id: number;
  cliente_id: number;
  tipo: 'compra' | 'venta';
  precio: number;
  comision?: number | null;
  gastos_traspaso?: number | null;
  gastos_reacondicionamiento?: number | null;
  fecha?: string;
  notas?: string | null;
}

export async function createTransaccion(payload: TransaccionInput): Promise<Transaccion> {
  const { data } = await api.post('/transacciones', payload);
  return data;
}

export async function deleteTransaccion(id: number): Promise<void> {
  await api.delete(`/transacciones/${id}`);
}

export async function createCliente(payload: {
  nombre: string; telefono?: string | null; email?: string | null; tipo: string; notas?: string | null;
}): Promise<Cliente> {
  const { data } = await api.post('/clientes', payload);
  return data;
}

// --- Datos de demostración ---

export interface DemoEstado {
  cargado: boolean;
  vehiculos: number;
  clientes: number;
  transacciones: number;
}

export async function fetchDemoEstado(): Promise<DemoEstado | null> {
  try {
    const { data } = await api.get('/demo');
    return data;
  } catch {
    return null;
  }
}

export async function cargarDemo(): Promise<DemoEstado> {
  const { data } = await api.post('/demo', null, { timeout: 120000 });
  return data;
}

export async function borrarDemo(): Promise<void> {
  await api.delete('/demo', { timeout: 120000 });
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

/**
 * Downscale a phone photo to max 1920px JPEG (~300-600 KB) so uploads stay
 * well under Vercel's 4.5 MB request limit and the catalogue loads fast.
 */
async function compressImage(file: File, maxSide = 1920, quality = 0.82): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, 'image/jpeg', quality));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], file.name.replace(/\.[^.]+$/, '') + '.jpg', { type: 'image/jpeg' });
  } catch {
    return file; // unsupported format in this browser: send as-is
  }
}

/** Uploads photos one per request (keeps each request small). */
export async function uploadFotos(id: number, files: File[]): Promise<VehiculoAdmin> {
  let last: VehiculoAdmin | null = null;
  for (const original of files) {
    const form = new FormData();
    form.append('files', await compressImage(original));
    const { data } = await api.post(`/vehiculos/${id}/fotos`, form, { timeout: 60000 });
    last = data;
  }
  return last!;
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

// --- Agentes IA ---

export interface AgentesEstado {
  ia_activa: boolean;
  modelo: string | null;
}

export async function fetchAgentesEstado(): Promise<AgentesEstado | null> {
  try {
    const { data } = await api.get('/agentes/estado');
    return data;
  } catch {
    return null;
  }
}

export interface ValuacionInput {
  marca: string;
  modelo: string;
  año: number;
  kilometraje: number;
  transmision: string;
  combustible: string;
  color: string;
  tipo_vehiculo: string;
  estado_mecanico: string;
  num_dueños: number;
  precio_pedido: number | null;
  url_anuncio?: string | null;
}

export interface Comparable {
  titulo: string;
  año: number;
  kilometraje: number | null;
  precio: number;
  ubicacion: string | null;
  plataforma: string;
  url: string;
}

export interface Valuacion {
  valor_mercado: number | null;
  rango_mercado: [number | null, number | null];
  precio_venta_sugerido: number | null;
  precio_compra_ideal: number | null;
  precio_compra_maximo: number | null;
  costos_estimados: number | null;
  margen_esperado_pct: number | null;
  dias_estimados_venta: number | null;
  liquidez: string;
  semaforo: 'verde' | 'amarillo' | 'rojo' | null;
  veredicto: string | null;
  factores_positivos: string[];
  factores_negativos: string[];
  comparables: Comparable[];
  historial: { ventas: number; precio_promedio: number | null; dias_promedio: number | null; margen_promedio_pct: number | null };
  metodo: string;
  analisis: string;
  analisis_ia: boolean;
}

export async function valuarVehiculo(payload: ValuacionInput): Promise<Valuacion> {
  const { data } = await api.post('/agentes/valuar', payload, { timeout: 90000 });
  return data;
}

export interface OportunidadCazada {
  id: number;
  titulo: string;
  kilometraje: number | null;
  ubicacion: string | null;
  precio: number;
  precio_mercado: number | null;
  descuento_pct: number | null;
  ganancia_potencial: number | null;
  margen_potencial_pct: number | null;
  score: number;
  estado: string;
  url: string;
  plataforma: string;
}

export interface Caceria {
  escaneados: number | null;
  total_mercado: number;
  ultima_actualizacion: string | null;
  oportunidades: OportunidadCazada[];
  resumen: string;
  analisis_ia: boolean;
}

export async function ejecutarCazador(params: {
  escanear: boolean; marca?: string; precio_max?: number; score_min: number;
}): Promise<Caceria> {
  const { data } = await api.post('/agentes/cazar', null, { params, timeout: 240000 });
  return data;
}

export interface TextosMarketing {
  titulo: string;
  descripcion: string;
  instagram: string;
  whatsapp: string;
  analisis_ia: boolean;
}

export async function generarMarketing(vehiculoId: number): Promise<TextosMarketing> {
  const { data } = await api.post(`/agentes/marketing/${vehiculoId}`, null, { timeout: 90000 });
  return data;
}

// --- CRM ---

export const ETAPAS_CRM = ['nuevo', 'contactado', 'cita', 'negociacion', 'ganado', 'perdido'] as const;
export type EtapaCRM = (typeof ETAPAS_CRM)[number];
export const CANALES_CRM = ['instagram', 'facebook', 'tiktok', 'whatsapp', 'web', 'tucarro', 'referido', 'vitrina'] as const;
export const TIPOS_INTERACCION = ['llamada', 'whatsapp', 'mensaje_red', 'email', 'visita', 'test_drive', 'cotizacion', 'nota'] as const;

export interface SeguimientoCRM {
  id: number;
  tipo: 'compra' | 'venta';
  etapa: EtapaCRM;
  canal: string;
  valor_estimado: number | null;
  probabilidad: number | null;
  proxima_accion: string | null;
  fecha_proxima: string | null;
  vencida: boolean;
  responsable: string | null;
  motivo_perdida: string | null;
  notas: string | null;
  created_at: string;
  updated_at: string;
  n_interacciones: number;
  ultima_interaccion: string | null;
  cliente: { id: number; nombre: string; telefono: string | null; email: string | null; presupuesto_max: number | null } | null;
  vehiculo: { id: number; nombre: string; precio: number | null; foto: string | null; estado: string } | null;
  interacciones?: { id: number; tipo: string; resumen: string; fecha: string }[];
}

export interface ResumenCRM {
  por_etapa: Record<EtapaCRM, { cantidad: number; valor: number }>;
  abiertos: number;
  valor_pipeline: number;
  valor_ponderado: number;
  conversion_pct: number | null;
  acciones_vencidas: number;
  acciones_hoy: number;
  por_canal: Record<string, { leads: number; ganados: number; perdidos: number; valor_ganado: number; conversion_pct: number | null }>;
  motivos_perdida: Record<string, number>;
}

export async function fetchPipeline(): Promise<SeguimientoCRM[]> {
  const { data } = await api.get('/crm', { params: { incluir_cerrados_dias: 30 } });
  return data;
}

export async function fetchResumenCRM(): Promise<ResumenCRM> {
  const { data } = await api.get('/crm/resumen');
  return data;
}

export async function fetchSeguimiento(id: number): Promise<SeguimientoCRM> {
  const { data } = await api.get(`/crm/${id}`);
  return data;
}

export async function updateSeguimiento(id: number, payload: Partial<{
  etapa: EtapaCRM; proxima_accion: string | null; fecha_proxima: string | null; responsable: string | null; motivo_perdida: string | null;
}>): Promise<SeguimientoCRM> {
  const { data } = await api.put(`/crm/${id}`, payload);
  return data;
}

export async function addInteraccion(id: number, tipo: string, resumen: string): Promise<SeguimientoCRM> {
  const { data } = await api.post(`/crm/${id}/interacciones`, { tipo, resumen });
  return data;
}

export async function createSeguimiento(payload: {
  cliente_nuevo: { nombre: string; telefono?: string | null; email?: string | null };
  vehiculo_id?: number | null; tipo: 'compra' | 'venta'; canal: string; proxima_accion?: string; responsable?: string | null;
}): Promise<SeguimientoCRM> {
  const { data } = await api.post('/crm', payload);
  return data;
}

// --- Redes sociales ---

export interface RedResumen {
  red: string;
  seguidores: number;
  crecimiento: number;
  crecimiento_pct: number | null;
  alcance: number;
  interacciones: number;
  engagement_pct: number | null;
  mensajes: number;
  leads: number;
  inversion: number;
  costo_por_lead: number | null;
  leads_crm: number;
  ventas: number;
  valor_ventas: number;
}

export interface PublicacionRed {
  id: number;
  red: string;
  tipo: string;
  titulo: string;
  fecha: string;
  alcance: number;
  me_gusta: number;
  comentarios: number;
  compartidos: number;
  guardados: number;
  mensajes: number;
  leads: number;
  engagement_pct: number | null;
  imagen: string | null;
  vehiculo: string | null;
  vehiculo_estado: string | null;
}

export interface ResumenRedes {
  dias: number;
  totales: {
    seguidores: number; crecimiento: number; alcance: number; leads: number; inversion: number;
    costo_por_lead: number | null; ventas_desde_redes: number; valor_ventas_redes: number;
  };
  redes: RedResumen[];
  serie: ({ fecha: string; leads: number; alcance: number } & Record<string, number | string>)[];
  top_publicaciones: PublicacionRed[];
  rendimiento_formato: { formato: string; publicaciones: number; alcance: number; leads: number; leads_por_publicacion: number }[];
}

export async function fetchRedes(dias = 90): Promise<ResumenRedes> {
  const { data } = await api.get('/redes/resumen', { params: { dias } });
  return data;
}

// --- Agentes Financiero y de Ventas ---

export interface Rentabilidad {
  grupo: string; ventas: number; ganancia: number; margen_pct: number; dias_promedio: number; roi_mensual_pct: number;
}

export interface AnalisisFinanciero {
  flujo_caja: { mes: string; ingresos: number; egresos: number; ganancia: number; ventas: number; compras: number; flujo_neto: number }[];
  capital_invertido: number;
  costo_capital_mensual: number;
  antiguedad_stock: { tramo: string; vehiculos: number; capital: number }[];
  rebajas_sugeridas: {
    vehiculo_id: number; vehiculo: string; dias: number; precio_actual: number; precio_sugerido: number;
    rebaja_pct: number; margen_resultante_pct: number; costo_capital_acumulado: number;
  }[];
  rentabilidad_marca: Rentabilidad[];
  rentabilidad_segmento: Rentabilidad[];
  proyeccion: { ventas_mes: number; ganancia_mes: number; ganancia_trimestre: number };
  margen_promedio_pct: number | null;
  alertas: string[];
  supuestos: string;
  analisis: string;
  analisis_ia: boolean;
}

export async function ejecutarFinanciero(): Promise<AnalisisFinanciero> {
  const { data } = await api.post('/agentes/financiero', null, { timeout: 90000 });
  return data;
}

export interface PrioridadVenta {
  seguimiento_id: number;
  cliente: string;
  telefono: string | null;
  tipo: 'compra' | 'venta';
  etapa: string;
  canal: string;
  vehiculo: string | null;
  valor: number | null;
  responsable: string | null;
  puntaje: number;
  razon: string;
  accion: string;
  mensaje: string;
  alternativas: { vehiculo_id: number; vehiculo: string; precio: number; foto: string | null }[];
}

export interface AnalisisVentas {
  abiertos: number;
  vencidos: number;
  sin_responsable: number;
  nuevos_redes: number;
  valor_ponderado: number;
  prioridades: PrioridadVenta[];
  analisis: string;
  analisis_ia: boolean;
}

export async function ejecutarVentas(): Promise<AnalisisVentas> {
  const { data } = await api.post('/agentes/ventas', null, { timeout: 90000 });
  return data;
}

// --- Scraping trigger ---

export async function triggerScraping(): Promise<boolean> {
  try {
    // A full scan takes ~30-60 s (longer if the free API was asleep)
    await api.post('/scraping/trigger', null, { timeout: 180000 });
    return true;
  } catch {
    return false;
  }
}
