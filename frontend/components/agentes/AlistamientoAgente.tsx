'use client';

import { useEffect, useState } from 'react';
import { Loader2, Wrench, Shuffle, Minus, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { formatCOP, formatCOPCompact } from '@/lib/data';
import { apiErrorMessage } from '@/lib/api-admin';
import { planearTaller, type PlanAlistamiento } from '@/lib/api-agentes';
import { Antes, Box, Cargando, Diagnostico } from './ui';

const COLOR_AREA: Record<string, string> = {
  'mecánica': '#38bdf8', 'latonería y pintura': '#f472b6', 'llantas': '#a78bfa', 'lavado': '#4ade80', 'fotos': '#d4a843',
};
const AREAS = [
  ['mecanica', 'Mecánica'], ['latoneria_pintura', 'Latonería y pintura'], ['llantas_alineacion', 'Llantas'],
  ['lavado_detallado', 'Lavado'], ['fotos_publicacion', 'Fotos'],
] as const;

export default function AlistamientoAgente() {
  const [semilla, setSemilla] = useState(2026);
  const [carros, setCarros] = useState(14);
  const [capacidad, setCapacidad] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState<PlanAlistamiento | null>(null);

  const run = async (s = semilla, cap = capacidad, n = carros) => {
    setLoading(true);
    try {
      const p = await planearTaller(s, n, cap);
      setPlan(p);
      setCapacidad(p.capacidad);
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo planear el taller'));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { run(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const cambiarCupo = (area: string, delta: number) => {
    const cap = { ...capacidad, [area]: Math.max(1, Math.min(6, (capacidad[area] ?? 1) + delta)) };
    setCapacidad(cap);
    run(semilla, cap);
  };

  return (
    <div className="space-y-6">
      <div className="card p-5 flex flex-col xl:flex-row gap-5 xl:items-end">
        <div className="flex-1">
          <p className="text-white font-semibold mb-1">Cupos del taller (carros a la vez)</p>
          <p className="text-gray-500 text-xs mb-3">Cambia un cupo y el agente recalcula el plan al instante.</p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {AREAS.map(([k, label]) => (
              <div key={k} className="bg-dark border border-border rounded-lg p-2">
                <p className="text-xs text-gray-400 mb-1">{label}</p>
                <div className="flex items-center justify-between">
                  <button onClick={() => cambiarCupo(k, -1)} disabled={loading} className="text-gray-400 hover:text-white disabled:opacity-40" aria-label={`Quitar cupo de ${label}`}><Minus className="w-4 h-4" /></button>
                  <span className="text-white font-bold">{capacidad[k] ?? '-'}</span>
                  <button onClick={() => cambiarCupo(k, 1)} disabled={loading} className="text-gray-400 hover:text-white disabled:opacity-40" aria-label={`Agregar cupo de ${label}`}><Plus className="w-4 h-4" /></button>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="flex gap-2 items-end">
          <div>
            <label className="block text-gray-400 text-xs mb-1">Carros por alistar</label>
            <select value={carros} onChange={(e) => { setCarros(Number(e.target.value)); run(semilla, capacidad, Number(e.target.value)); }} className="select-field py-2">
              {[8, 14, 20, 30].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <button onClick={() => { setSemilla(semilla + 1); run(semilla + 1); }} disabled={loading} className="btn-ghost flex items-center gap-1 text-sm whitespace-nowrap">
            <Shuffle className="w-4 h-4" /> Otra tanda
          </button>
          <button onClick={() => run()} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50 whitespace-nowrap">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wrench className="w-4 h-4" />} Planear
          </button>
        </div>
      </div>

      {loading && !plan && <Cargando />}
      {plan && <Plan plan={plan} />}
    </div>
  );
}

function Plan({ plan }: { plan: PlanAlistamiento }) {
  const b = plan.linea_base, a = plan.agente, e = plan.escenario_cupo_extra;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Antes label="Días promedio en taller" antes={`${b.dias_promedio} por orden de llegada`} despues={`${a.dias_promedio} con el agente`} mejor={a.dias_promedio < b.dias_promedio} />
        <Antes label="Costo del capital parado" antes={formatCOPCompact(b.costo_capital)} despues={formatCOPCompact(a.costo_capital)} mejor={a.costo_capital < b.costo_capital} />
        <Box label="Cuello de botella" value={plan.cuello_botella.area} sub={`${plan.cuello_botella.dias_de_trabajo_por_cupo} días de trabajo por cupo`} accent="text-red-300" />
        <Box label={`Con 1 cupo más en ${e.area}`} value={`${e.dias_promedio} días`} sub={`ahorra ${formatCOPCompact(Math.max(0, e.ahorro_vs_base_costo_capital))} de capital`} accent="text-green-400" />
      </div>

      <Diagnostico titulo="Plan del Agente de Alistamiento" texto={plan.recomendacion} ia={false} nota={plan.supuestos} />

      <Gantt plan={plan} />

      {plan.sobrecostos.length > 0 && (
        <div className="card p-5 overflow-x-auto">
          <p className="text-white font-semibold mb-1">Carros que gastaron más de lo presupuestado al comprarlos</p>
          <p className="text-gray-500 text-xs mb-3">Presupuesto = costos de alistamiento que estimó el Agente Valuador. Un exceso grande indica un peritaje de compra flojo.</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase border-b border-border">
                <th className="text-left py-2">Vehículo</th><th className="text-left">Trabajos</th><th className="text-right">Presupuesto</th>
                <th className="text-right">Costo real</th><th className="text-right">Exceso</th>
              </tr>
            </thead>
            <tbody>
              {plan.sobrecostos.map((s) => (
                <tr key={s.id} className="border-b border-border/50">
                  <td className="py-2 text-white">{s.vehiculo}</td>
                  <td className="text-gray-400">{s.tareas.join(', ')}</td>
                  <td className="text-right text-gray-400">{formatCOP(s.presupuesto)}</td>
                  <td className="text-right text-gray-200">{formatCOP(s.costo)}</td>
                  <td className="text-right text-red-400 font-medium">{formatCOP(s.exceso)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Gantt({ plan }: { plan: PlanAlistamiento }) {
  const filas = plan.plan;
  const dias = Math.max(...filas.map((f) => f.dia_listo), 1);
  const izq = 170, fila = 24, W = 760, top = 26;
  const H = top + filas.length * fila + 10;
  const x = (d: number) => izq + (d / dias) * (W - izq - 16);
  return (
    <div className="card p-5 overflow-x-auto">
      <p className="text-white font-semibold mb-1">Plan del taller, día por día</p>
      <p className="text-gray-500 text-xs mb-3">Cada barra es un trabajo; el punto gris es el día en que se compró el carro. Orden de arriba abajo: el que queda listo primero.</p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[640px] h-auto" role="img" aria-label="Cronograma del taller">
        {Array.from({ length: dias + 1 }, (_, d) => d).filter((d) => d % 2 === 0).map((d) => (
          <g key={d}>
            <line x1={x(d)} x2={x(d)} y1={top - 6} y2={H - 6} stroke="#1f1f1f" />
            <text x={x(d)} y={14} textAnchor="middle" fontSize={10} fill="#6b7280">día {d}</text>
          </g>
        ))}
        {filas.map((f, i) => {
          const yy = top + i * fila;
          return (
            <g key={f.id}>
              <text x={0} y={yy + 14} fontSize={11} fill="#e5e7eb">{f.vehiculo.length > 24 ? `${f.vehiculo.slice(0, 23)}…` : f.vehiculo}</text>
              <circle cx={x(f.dia_compra)} cy={yy + 10} r={3} fill="#6b7280" />
              {f.tramos.map((t, k) => (
                <rect key={k} x={x(t.desde)} y={yy + 3} width={Math.max(2, x(t.hasta) - x(t.desde) - 1)} height={14} rx={3}
                  fill={COLOR_AREA[t.area] ?? '#9ca3af'} fillOpacity={0.85}>
                  <title>{`${f.vehiculo}: ${t.area}, día ${t.desde} a ${t.hasta}`}</title>
                </rect>
              ))}
              <text x={x(f.dia_listo) + 4} y={yy + 14} fontSize={10} fill="#9ca3af">listo día {f.dia_listo}</text>
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-3 mt-2 text-xs text-gray-300">
        {Object.entries(COLOR_AREA).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1"><span className="w-3 h-3 rounded-sm inline-block" style={{ background: c }} />{k}</span>
        ))}
      </div>
    </div>
  );
}
