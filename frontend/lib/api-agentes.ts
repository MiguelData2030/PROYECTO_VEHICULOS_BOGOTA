/**
 * API of the marketing strategist and the operations agents
 * (Logística, Alistamiento, Crédito, Atención 24/7).
 */
import { api } from './api-admin';

const LARGO = { timeout: 90000 };

// --- Marketing (estrategia) ---

export interface CanalMarketing {
  red: string;
  nombre: string;
  seguidores: number;
  crecimiento: number;
  alcance: number;
  engagement_pct: number | null;
  leads: number;
  inversion: number;
  costo_por_lead: number | null;
  ventas: number;
  valor_ventas: number;
  conversion_pct: number | null;
  costo_por_venta: number | null;
  ganancia_estimada: number;
  roi_pauta: number | null;
}

export interface PresupuestoRed {
  red: string;
  nombre: string;
  actual: number;
  recomendado: number;
  cambio_pct: number | null;
  leads_esperados: number;
  ventas_esperadas: number;
  motivo: string;
}

export interface CarroImpulsar {
  vehiculo_id: number;
  vehiculo: string;
  precio: number;
  foto: string | null;
  dias_inventario: number;
  margen_pct: number;
  prioridad: number;
  razones: string[];
  publico: string;
  mensaje_clave: string;
  red: string;
  red_nombre: string;
  formato: string;
  cuota_desde: number;
}

export interface PiezaCalendario {
  dia: string;
  orden: number;
  hora: string;
  red: string;
  red_nombre: string;
  formato: string;
  vehiculo: string;
  vehiculo_id: number | null;
  objetivo: string;
  gancho: string;
}

export interface EstrategiaMarketing {
  sin_datos: boolean;
  dias?: number;
  ganancia_por_venta?: number;
  canales?: CanalMarketing[];
  presupuesto?: {
    total: number;
    por_red: PresupuestoRed[];
    leads_esperados: number;
    ventas_esperadas: number;
    canal_prueba: string | null;
  };
  formatos?: { red: string; nombre: string; formato: string; publicaciones: number; leads: number; leads_por_publicacion: number; alcance_por_publicacion: number }[];
  impulsar?: CarroImpulsar[];
  calendario?: PiezaCalendario[];
  alertas?: string[];
  pruebas_ab?: { nombre: string; a: string; b: string; medir: string }[];
  supuestos?: string;
  analisis: string;
  analisis_ia: boolean;
}

export async function ejecutarEstrategia(dias: number, presupuesto: number | null): Promise<EstrategiaMarketing> {
  const params: Record<string, number> = { dias };
  if (presupuesto) params.presupuesto = presupuesto;
  const { data } = await api.post('/agentes/marketing/estrategia', null, { params, ...LARGO });
  return data;
}

// --- Logística ---

export interface Cita {
  id: string;
  tipo: 'peritaje' | 'entrega' | 'test_drive';
  cliente: string;
  zona: string;
  lat?: number;
  lon?: number;
  ventana?: string;
  desde: string;
  hasta: string;
  duracion_min?: number;
}

export interface Parada {
  cita: string;
  tipo: string;
  zona: string;
  cliente: string | null;
  lat: number;
  lon: number;
  llegada: string;
  ventana: string;
  retraso_min: number;
}

export interface RutaConductor {
  conductor: number;
  paradas: Parada[];
  km: number;
  fin: string;
  horas: number;
  espera_min: number;
  citas_tarde: number;
}

export interface ResumenRutas {
  km: number;
  horas_conductor: number;
  citas_tarde: number;
  costo_cop: number;
}

export interface PlanLogistica {
  citas: number;
  conductores: number;
  sede: { nombre: string; lat: number; lon: number };
  zonas: { nombre: string; lat: number; lon: number }[];
  linea_base: ResumenRutas;
  agente: ResumenRutas;
  ahorro: { km: number; km_pct: number; horas: number; costo_cop: number; costo_mes_cop: number; citas_tarde_evitadas: number };
  rutas: RutaConductor[];
  recomendacion: string;
  supuestos: string;
}

export async function fetchAgenda(semilla: number): Promise<{ sede: PlanLogistica['sede']; zonas: string[]; citas: Cita[] }> {
  const { data } = await api.get('/agentes/logistica/agenda', { params: { semilla } });
  return data;
}

export async function planearRutas(citas: Cita[], conductores: number): Promise<PlanLogistica> {
  const { data } = await api.post('/agentes/logistica', { citas, conductores }, LARGO);
  return data;
}

// --- Alistamiento ---

export interface Tramo { area: string; desde: number; hasta: number }

export interface CarroPlan {
  id: string;
  vehiculo: string;
  liquidez: string;
  dia_compra: number;
  dia_listo: number;
  dias_en_taller: number;
  costo_capital: number;
  tramos: Tramo[];
}

export interface ResumenTaller {
  dias_promedio: number;
  dias_promedio_liquidez_alta: number | null;
  ultimo_listo_dia: number;
  costo_capital: number;
}

export interface PlanAlistamiento {
  carros: number;
  capacidad: Record<string, number>;
  areas: { clave: string; nombre: string }[];
  linea_base: ResumenTaller;
  agente: ResumenTaller;
  ahorro: { dias_promedio: number; costo_capital: number };
  escenario_cupo_extra: ResumenTaller & { area: string; ahorro_vs_base_dias: number; ahorro_vs_base_costo_capital: number };
  plan: CarroPlan[];
  sobrecostos: { id: string; vehiculo: string; costo: number; presupuesto: number; exceso: number; tareas: string[] }[];
  cuello_botella: { area: string; dias_de_trabajo_por_cupo: number };
  recomendacion: string;
  supuestos: string;
}

export async function planearTaller(semilla: number, carros: number, capacidad: Record<string, number>): Promise<PlanAlistamiento> {
  const { data } = await api.post('/agentes/alistamiento', { semilla, carros, capacidad }, LARGO);
  return data;
}

// --- Crédito ---

export interface CreditoInput {
  cliente: string;
  empleo: 'empleado' | 'independiente' | 'pensionado';
  ingreso_mensual: number;
  cuotas_actuales: number;
  puntaje_buro: number;
  vehiculo_id: number | null;
  cuota_inicial: number;
}

export interface DecisionCredito {
  id: string;
  cliente: string;
  vehiculo: string;
  precio: number;
  puntaje_buro: number;
  capacidad_cuota: number;
  decision: 'aprobable' | 'aprobable_con_ajuste' | 'alternativa' | 'no_viable';
  linea_base_aprueba: boolean;
  tasa_ea?: number;
  plazo?: number;
  cuota?: number;
  cuota_inicial?: number;
  alternativa?: string;
  precio_alternativa?: number;
  propuesta: string;
  tabla?: { plazo: number; cuota: number }[];
}

export interface SimulacionCredito {
  solicitudes: number;
  decisiones: Record<string, number>;
  linea_base: { ventas_viables: number; valor_cop: number };
  agente: { ventas_viables: number; valor_cop: number };
  ventas_rescatadas: number;
  valor_rescatado_cop: number;
  detalle: DecisionCredito[];
  recomendacion: string;
  supuestos: string;
}

export async function evaluarCredito(input: CreditoInput): Promise<DecisionCredito> {
  const { data } = await api.post('/agentes/credito', input);
  return data;
}

export async function simularCreditos(semilla: number): Promise<SimulacionCredito> {
  const { data } = await api.post('/agentes/credito/simulacion', null, { params: { semilla }, ...LARGO });
  return data;
}

// --- Atención 24/7 ---

export interface RespuestaAtencion {
  intencion: string;
  confianza: 'alta' | 'baja';
  marca: string | null;
  tipo: string | null;
  presupuesto: number | null;
  ingreso: number | null;
  urgente: boolean;
  respuesta: string;
  respuesta_ia?: boolean;
  a_humano: boolean;
  temperatura: string;
  lead_id?: number | null;
  mensaje: string;
  canal: string;
  cliente: string;
  hora?: string;
  acierto?: boolean;
}

export interface SimulacionAtencion {
  mensajes: number;
  precision_intencion_pct: number;
  resueltos_automaticamente: number;
  resueltos_pct: number;
  pasados_a_humano: number;
  fuera_de_horario: number;
  leads_calientes: number;
  por_intencion: Record<string, number>;
  tiempo_respuesta: { agente_min: number; asesor_min: number };
  detalle: RespuestaAtencion[];
  recomendacion: string;
  supuestos: string;
}

export async function enviarMensaje(body: {
  mensaje: string; canal: string; cliente: string; telefono?: string; guardar_lead: boolean;
}): Promise<RespuestaAtencion> {
  const { data } = await api.post('/agentes/atencion', body, LARGO);
  return data;
}

export async function simularAtencion(semilla: number): Promise<SimulacionAtencion> {
  const { data } = await api.post('/agentes/atencion/simulacion', null, { params: { semilla } });
  return data;
}
