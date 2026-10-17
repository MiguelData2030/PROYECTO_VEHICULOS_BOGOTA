'use client';

import { useEffect, useState } from 'react';
import { Loader2, Route, Plus, Trash2, Shuffle, MapPin } from 'lucide-react';
import toast from 'react-hot-toast';
import { formatCOP, formatCOPCompact } from '@/lib/data';
import { apiErrorMessage } from '@/lib/api-admin';
import { fetchAgenda, planearRutas, type Cita, type PlanLogistica } from '@/lib/api-agentes';
import { Antes, Box, Cargando, Diagnostico, F } from './ui';

const COLORES = ['#d4a843', '#38bdf8', '#a78bfa', '#4ade80', '#f472b6', '#fb923c'];
const TIPO: Record<Cita['tipo'], string> = { peritaje: 'Peritaje', entrega: 'Entrega', test_drive: 'Test drive' };
const VENTANAS = { mañana: ['08:00', '12:00'], tarde: ['13:00', '17:30'], flexible: ['08:00', '17:30'] } as const;

export default function LogisticaAgente() {
  const [semilla, setSemilla] = useState(2026);
  const [zonas, setZonas] = useState<string[]>([]);
  const [citas, setCitas] = useState<Cita[]>([]);
  const [conductores, setConductores] = useState(2);
  const [nueva, setNueva] = useState({ tipo: 'entrega' as Cita['tipo'], zona: 'Chapinero', ventana: 'tarde' as keyof typeof VENTANAS, cliente: '' });
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState<PlanLogistica | null>(null);

  const cargarAgenda = async (s: number) => {
    try {
      const a = await fetchAgenda(s);
      setZonas(a.zonas);
      setCitas(a.citas);
      setPlan(null);
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo cargar la agenda'));
    }
  };
  useEffect(() => { cargarAgenda(semilla); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const planear = async (lista = citas, n = conductores) => {
    if (!lista.length) return;
    setLoading(true);
    try {
      setPlan(await planearRutas(lista, n));
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudieron planear las rutas'));
    } finally {
      setLoading(false);
    }
  };

  const agregar = () => {
    const [desde, hasta] = VENTANAS[nueva.ventana];
    const id = `N${String(citas.length + 1).padStart(2, '0')}`;
    setCitas([...citas, { id, tipo: nueva.tipo, zona: nueva.zona, cliente: nueva.cliente || 'Cliente nuevo', desde, hasta, ventana: nueva.ventana }]);
    setNueva({ ...nueva, cliente: '' });
    setPlan(null);
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="card p-5 lg:col-span-2 space-y-4 h-fit">
          <div className="flex items-center justify-between">
            <p className="text-white font-semibold">Agenda del sábado · {citas.length} citas</p>
            <button onClick={() => { setSemilla(semilla + 1); cargarAgenda(semilla + 1); }} className="btn-ghost text-xs flex items-center gap-1 px-2 py-1">
              <Shuffle className="w-3 h-3" /> Otra agenda
            </button>
          </div>
          <div className="max-h-72 overflow-y-auto pr-1 space-y-1">
            {citas.map((c) => (
              <div key={c.id} className="flex items-center gap-2 text-xs bg-dark border border-border rounded-lg px-2 py-1.5">
                <span className="text-gray-500 w-8">{c.id}</span>
                <span className="text-white w-20">{TIPO[c.tipo]}</span>
                <span className="text-gray-300 flex-1 truncate">{c.zona} · {c.cliente}</span>
                <span className="text-gray-500">{c.desde}–{c.hasta}</span>
                <button onClick={() => { setCitas(citas.filter((x) => x.id !== c.id)); setPlan(null); }} className="text-gray-500 hover:text-red-400" aria-label={`Quitar ${c.id}`}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
          <div className="border-t border-border pt-3 space-y-2">
            <p className="text-gray-400 text-xs">Agregar una cita</p>
            <div className="grid grid-cols-2 gap-2">
              <select value={nueva.tipo} onChange={(e) => setNueva({ ...nueva, tipo: e.target.value as Cita['tipo'] })} className="select-field py-1.5 text-sm">
                {Object.entries(TIPO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <select value={nueva.zona} onChange={(e) => setNueva({ ...nueva, zona: e.target.value })} className="select-field py-1.5 text-sm">
                {zonas.map((z) => <option key={z}>{z}</option>)}
              </select>
              <select value={nueva.ventana} onChange={(e) => setNueva({ ...nueva, ventana: e.target.value as keyof typeof VENTANAS })} className="select-field py-1.5 text-sm">
                <option value="mañana">Mañana (8–12)</option><option value="tarde">Tarde (13–17:30)</option><option value="flexible">Todo el día</option>
              </select>
              <input value={nueva.cliente} onChange={(e) => setNueva({ ...nueva, cliente: e.target.value })} placeholder="Cliente" className="input-field py-1.5 text-sm" />
            </div>
            <button onClick={agregar} className="btn-ghost text-xs flex items-center gap-1 px-2 py-1"><Plus className="w-3 h-3" /> Agregar</button>
          </div>
          <div className="flex gap-3 items-end">
            <F label="Conductores">
              <select value={conductores} onChange={(e) => { setConductores(Number(e.target.value)); if (plan) planear(citas, Number(e.target.value)); }} className="select-field py-2">
                {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </F>
            <button onClick={() => planear()} disabled={loading || !citas.length} className="btn-primary flex items-center gap-2 disabled:opacity-50 whitespace-nowrap">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Route className="w-4 h-4" />} Planear rutas
            </button>
          </div>
        </div>

        <div className="lg:col-span-3 space-y-4">
          {loading && <Cargando />}
          {!loading && !plan && (
            <div className="card p-10 text-center text-gray-500">
              <MapPin className="w-10 h-10 mx-auto mb-3" />
              Ajusta la agenda (agrega o quita citas) y el agente arma la ruta de cada conductor respetando la hora que pidió cada cliente.
            </div>
          )}
          {!loading && plan && <Resultado plan={plan} />}
        </div>
      </div>
      {!loading && plan && <Itinerarios plan={plan} />}
    </div>
  );
}

function Resultado({ plan }: { plan: PlanLogistica }) {
  const b = plan.linea_base, a = plan.agente;
  return (
    <>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Antes label="Kilómetros del día" antes={`${b.km} km`} despues={`${a.km} km`} mejor={a.km < b.km} />
        <Antes label="Horas de conductor" antes={`${b.horas_conductor} h`} despues={`${a.horas_conductor} h`} mejor={a.horas_conductor < b.horas_conductor} />
        <Antes label="Llegadas tarde" antes={String(b.citas_tarde)} despues={String(a.citas_tarde)} mejor={a.citas_tarde < b.citas_tarde} />
        <Box label="Ahorro al mes" value={formatCOPCompact(Math.max(0, plan.ahorro.costo_mes_cop))} sub={`${plan.ahorro.km_pct}% menos km`} accent="text-green-400" />
      </div>
      <Mapa plan={plan} />
      <Diagnostico titulo="Plan del Agente de Logística" texto={plan.recomendacion} ia={false}
        nota={`Línea base: el despachador asigna las citas en el orden en que llegaron. ${plan.supuestos}`} />
    </>
  );
}

function Mapa({ plan }: { plan: PlanLogistica }) {
  const puntos = [plan.sede, ...plan.rutas.flatMap((r) => r.paradas)];
  const lats = puntos.map((p) => p.lat), lons = puntos.map((p) => p.lon);
  const [minLat, maxLat, minLon, maxLon] = [Math.min(...lats), Math.max(...lats), Math.min(...lons), Math.max(...lons)];
  const W = 640, H = 380, pad = 28;
  // keep the map's proportions: 1° of longitude is ~cos(lat) of 1° of latitude
  const kx = Math.cos((plan.sede.lat * Math.PI) / 180);
  const escala = Math.min((W - 2 * pad) / ((maxLon - minLon) * kx || 1), (H - 2 * pad) / (maxLat - minLat || 1));
  const x = (lon: number) => pad + (lon - minLon) * kx * escala;
  const y = (lat: number) => H - pad - (lat - minLat) * escala;

  return (
    <div className="card p-4">
      <p className="text-white font-semibold text-sm mb-2">Rutas en el mapa de Bogotá</p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto bg-dark rounded-lg" role="img" aria-label="Mapa de rutas de los conductores">
        {plan.zonas
          .filter((z) => z.lat >= minLat && z.lat <= maxLat && z.lon >= minLon && z.lon <= maxLon)
          .map((z) => (
            <text key={z.nombre} x={x(z.lon)} y={y(z.lat) - 14} textAnchor="middle" fontSize={11} fill="#4b5563">{z.nombre}</text>
          ))}
        {plan.rutas.map((r, i) => {
          const pts = [plan.sede, ...r.paradas, plan.sede].map((p) => `${x(p.lon)},${y(p.lat)}`).join(' ');
          return <polyline key={r.conductor} points={pts} fill="none" stroke={COLORES[i % COLORES.length]} strokeWidth={2} strokeOpacity={0.8} />;
        })}
        {plan.rutas.map((r, i) => r.paradas.map((p, k) => (
          <g key={p.cita}>
            <circle cx={x(p.lon)} cy={y(p.lat)} r={9} fill="#0a0a0a" stroke={p.retraso_min ? '#f87171' : COLORES[i % COLORES.length]} strokeWidth={2}>
              <title>{`${p.cita} · ${p.tipo} en ${p.zona} · llega ${p.llegada} (ventana ${p.ventana})`}</title>
            </circle>
            <text x={x(p.lon)} y={y(p.lat) + 3.5} textAnchor="middle" fontSize={10} fill="#fff">{k + 1}</text>
          </g>
        )))}
        <rect x={x(plan.sede.lon) - 8} y={y(plan.sede.lat) - 8} width={16} height={16} rx={3} fill="#d4a843" />
        <text x={x(plan.sede.lon) + 12} y={y(plan.sede.lat) + 4} fontSize={11} fill="#d4a843">Sede</text>
      </svg>
      <div className="flex flex-wrap gap-3 mt-2 text-xs">
        {plan.rutas.map((r, i) => (
          <span key={r.conductor} className="flex items-center gap-1 text-gray-300">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: COLORES[i % COLORES.length] }} />
            Conductor {r.conductor}: {r.paradas.length} citas, {r.km} km, regresa {r.fin}
          </span>
        ))}
      </div>
    </div>
  );
}

function Itinerarios({ plan }: { plan: PlanLogistica }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {plan.rutas.map((r, i) => (
        <div key={r.conductor} className="card p-5 overflow-x-auto">
          <p className="text-white font-semibold mb-3 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: COLORES[i % COLORES.length] }} />
            Conductor {r.conductor} · sale 08:00, regresa {r.fin} · {r.km} km
          </p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase border-b border-border">
                <th className="text-left py-2">#</th><th className="text-left">Llega</th><th className="text-left">Cita</th><th className="text-left">Zona</th><th className="text-left">Ventana</th>
              </tr>
            </thead>
            <tbody>
              {r.paradas.map((p, k) => (
                <tr key={p.cita} className="border-b border-border/50">
                  <td className="py-1.5 text-gray-500">{k + 1}</td>
                  <td className={p.retraso_min ? 'text-red-400 font-medium' : 'text-white'}>{p.llegada}{p.retraso_min ? ` (+${p.retraso_min} min)` : ''}</td>
                  <td className="text-gray-300">{TIPO[p.tipo as Cita['tipo']] ?? p.tipo} · {p.cliente}</td>
                  <td className="text-gray-400">{p.zona}</td>
                  <td className="text-gray-500">{p.ventana}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {r.espera_min > 0 && <p className="text-xs text-gray-500 mt-2">Espera total por llegar antes de la ventana: {r.espera_min} min.</p>}
        </div>
      ))}
      <p className="text-xs text-gray-600 lg:col-span-2">Costo de un día con el plan del agente: {formatCOP(plan.agente.costo_cop)} (antes {formatCOP(plan.linea_base.costo_cop)}).</p>
    </div>
  );
}
