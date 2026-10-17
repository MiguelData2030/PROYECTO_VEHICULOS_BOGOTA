'use client';

import { useEffect, useState } from 'react';
import {
  Megaphone, Loader2, Target, CalendarDays, FlaskConical, Wand2, ArrowRight, Sparkles, Cpu, Users, TrendingUp,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import toast from 'react-hot-toast';
import { canalInfo } from '@/lib/canales';
import { formatCOP, formatCOPCompact, formatNumber } from '@/lib/data';
import {
  fetchInventario, generarMarketing, updateVehiculo, apiErrorMessage, fotoUrl,
  type TextosMarketing, type VehiculoAdmin, type VehiculoInput,
} from '@/lib/api-admin';
import { ejecutarEstrategia, type EstrategiaMarketing, type CarroImpulsar } from '@/lib/api-agentes';
import { Alertas, Box, Cargando, CopyBtn, Diagnostico, F, Num, Texto } from './ui';

const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

export default function MarketingAgente({ vehiculoInicial }: { vehiculoInicial: number | null }) {
  const [vista, setVista] = useState<'estrategia' | 'anuncios'>(vehiculoInicial ? 'anuncios' : 'estrategia');
  const [carro, setCarro] = useState<number | null>(vehiculoInicial);

  const crearPiezas = (c: CarroImpulsar) => {
    setCarro(c.vehiculo_id);
    setVista('anuncios');
  };

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        {([['estrategia', 'Estrategia y presupuesto', Target], ['anuncios', 'Crear anuncios de un carro', Wand2]] as const).map(([k, label, Icon]) => (
          <button
            key={k}
            onClick={() => setVista(k)}
            className={`px-4 py-2 rounded-lg text-sm flex items-center gap-2 border ${vista === k ? 'border-primary bg-primary/10 text-white' : 'border-border text-gray-400 hover:text-white'}`}
          >
            <Icon className="w-4 h-4" /> {label}
          </button>
        ))}
      </div>
      {vista === 'estrategia' ? <Estrategia onCrearPiezas={crearPiezas} /> : <Anuncios vehiculo={carro} setVehiculo={setCarro} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Estrategia
// ---------------------------------------------------------------------------

function Estrategia({ onCrearPiezas }: { onCrearPiezas: (c: CarroImpulsar) => void }) {
  const [dias, setDias] = useState(90);
  const [presupuesto, setPresupuesto] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [r, setR] = useState<EstrategiaMarketing | null>(null);

  const run = async () => {
    setLoading(true);
    try {
      setR(await ejecutarEstrategia(dias, presupuesto));
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo armar la estrategia'));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { run(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="space-y-6">
      <div className="card p-5 flex flex-col md:flex-row gap-3 md:items-end">
        <F label="Analizar los últimos">
          <select value={dias} onChange={(e) => setDias(Number(e.target.value))} className="select-field py-2">
            {[30, 60, 90, 180].map((d) => <option key={d} value={d}>{d} días</option>)}
          </select>
        </F>
        <F label="Pauta del próximo mes (vacío = la de hoy)">
          <Num value={presupuesto} onChange={setPresupuesto} money />
        </F>
        <button onClick={run} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50 whitespace-nowrap">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Megaphone className="w-4 h-4" />} Armar estrategia
        </button>
      </div>

      {loading && <Cargando />}
      {!loading && r?.sin_datos && <div className="card p-8 text-center text-gray-400">{r.analisis}</div>}
      {!loading && r && !r.sin_datos && <Plan r={r} onCrearPiezas={onCrearPiezas} />}
    </div>
  );
}

function Plan({ r, onCrearPiezas }: { r: EstrategiaMarketing; onCrearPiezas: (c: CarroImpulsar) => void }) {
  const p = r.presupuesto!;
  const datosPresupuesto = p.por_red.map((x) => ({
    red: x.nombre,
    'Hoy': Math.round(x.actual / 1000),
    'Recomendado': Math.round(x.recomendado / 1000),
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Box label="Pauta del próximo mes" value={formatCOPCompact(p.total)} sub={p.canal_prueba ? `incluye prueba en ${p.canal_prueba}` : undefined} />
        <Box label="Leads esperados" value={formatNumber(p.leads_esperados)} sub="desde redes, con esa pauta" accent="text-primary" />
        <Box label="Ventas esperadas" value={p.ventas_esperadas.toLocaleString('es-CO')} sub="según la conversión de cada red" accent="text-green-400" />
        <Box label="Ganancia por carro vendido" value={formatCOPCompact(r.ganancia_por_venta!)} sub="promedio de 12 meses" />
      </div>

      <Diagnostico titulo="Plan del Agente de Marketing" texto={r.analisis} ia={r.analisis_ia} nota={r.supuestos} />

      {r.alertas!.length > 0 && (
        <div className="card p-5">
          <p className="text-white font-semibold mb-3">Alertas</p>
          <Alertas items={r.alertas!} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="card p-5 lg:col-span-3 overflow-x-auto">
          <p className="text-white font-semibold mb-1 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-primary" /> Qué red vende de verdad</p>
          <p className="text-gray-500 text-xs mb-3">Últimos {r.dias} días: del alcance al carro vendido. Retorno = ganancia de los carros vendidos por cada peso de pauta.</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase border-b border-border">
                <th className="text-left py-2">Red</th><th className="text-right">Alcance</th><th className="text-right">Leads</th>
                <th className="text-right">Costo/lead</th><th className="text-right">Ventas</th><th className="text-right">Conversión</th><th className="text-right">Retorno</th>
              </tr>
            </thead>
            <tbody>
              {r.canales!.map((c) => (
                <tr key={c.red} className="border-b border-border/50">
                  <td className="py-2"><span className={`px-2 py-0.5 rounded text-xs ${canalInfo(c.red).cls}`}>{c.nombre}</span></td>
                  <td className="text-right text-gray-400">{formatNumber(c.alcance)}</td>
                  <td className="text-right text-gray-200">{formatNumber(c.leads)}</td>
                  <td className="text-right text-gray-300">{c.costo_por_lead ? formatCOP(c.costo_por_lead) : <span className="text-gray-500">orgánico</span>}</td>
                  <td className="text-right text-white font-medium">{c.ventas}</td>
                  <td className="text-right text-gray-300">{c.conversion_pct != null ? `${c.conversion_pct}%` : '-'}</td>
                  <td className={`text-right font-medium ${c.roi_pauta == null ? 'text-gray-500' : c.roi_pauta >= 3 ? 'text-green-400' : c.roi_pauta >= 0 ? 'text-primary' : 'text-red-400'}`}>
                    {c.roi_pauta == null ? '-' : `${(c.roi_pauta + 1).toFixed(1)}x`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card p-5 lg:col-span-2">
          <p className="text-white font-semibold mb-1">Presupuesto de pauta (miles COP/mes)</p>
          <p className="text-gray-500 text-xs mb-3">El dinero se mueve hacia las redes que más venden por cada millón invertido.</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={datosPresupuesto}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
              <XAxis dataKey="red" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8 }} labelStyle={{ color: '#fff' }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Hoy" fill="#6b7280" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Recomendado" fill="#d4a843" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-2 space-y-1">
            {p.por_red.map((x) => (
              <p key={x.red} className="text-xs text-gray-400">
                <span className="text-white">{x.nombre}:</span> {formatCOP(x.recomendado)}
                {x.cambio_pct != null && <span className={x.cambio_pct >= 0 ? 'text-green-400' : 'text-red-400'}> ({x.cambio_pct > 0 ? '+' : ''}{x.cambio_pct}%)</span>} — {x.motivo}
              </p>
            ))}
          </div>
        </div>
      </div>

      <div>
        <p className="text-white font-semibold mb-3 flex items-center gap-2"><Users className="w-4 h-4 text-primary" /> Carros a impulsar esta semana</p>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {r.impulsar!.map((c) => (
            <div key={c.vehiculo_id} className="card overflow-hidden flex flex-col">
              {c.foto && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={fotoUrl(c.foto)} alt={c.vehiculo} className="h-32 w-full object-cover" />
              )}
              <div className="p-4 flex-1 flex flex-col gap-2">
                <div className="flex justify-between items-start gap-2">
                  <p className="text-white font-semibold">{c.vehiculo}</p>
                  <span className="text-xs text-primary whitespace-nowrap">prioridad {c.prioridad}</span>
                </div>
                <p className="text-xs text-gray-400">{formatCOP(c.precio)} · cuota desde {formatCOP(c.cuota_desde)}/mes</p>
                <p className="text-xs text-yellow-300">{c.razones.join(' · ')}</p>
                <p className="text-xs text-gray-300"><span className="text-gray-500">Público:</span> {c.publico}</p>
                <p className="text-xs text-gray-300"><span className="text-gray-500">Mensaje:</span> {c.mensaje_clave}</p>
                <p className="text-xs"><span className={`px-2 py-0.5 rounded ${canalInfo(c.red).cls}`}>{c.red_nombre} · {c.formato}</span></p>
                <button onClick={() => onCrearPiezas(c)} className="btn-ghost text-xs mt-auto self-start flex items-center gap-1 px-2 py-1">
                  <Wand2 className="w-3 h-3" /> Crear las piezas
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-5 overflow-x-auto">
        <p className="text-white font-semibold mb-1 flex items-center gap-2"><CalendarDays className="w-4 h-4 text-primary" /> Calendario de contenido de la semana</p>
        <p className="text-gray-500 text-xs mb-4">Cada red recibe piezas según los leads que trae; formato y día salen de lo que mejor le ha funcionado.</p>
        <div className="grid grid-cols-7 gap-2 min-w-[900px]">
          {DIAS.map((d) => (
            <div key={d}>
              <p className="text-xs text-gray-400 font-semibold mb-2 text-center">{d}</p>
              <div className="space-y-2">
                {r.calendario!.filter((x) => x.dia === d).map((x, i) => (
                  <div key={i} className="bg-dark border border-border rounded-lg p-2 text-xs">
                    <div className="flex items-center justify-between mb-1">
                      <span className={`px-1.5 py-0.5 rounded ${canalInfo(x.red).cls}`}>{x.red_nombre}</span>
                      <span className="text-gray-500">{x.hora}</span>
                    </div>
                    <p className="text-white font-medium">{x.formato} · {x.vehiculo}</p>
                    <p className="text-gray-400 mt-1 leading-snug">{x.gancho}</p>
                    <div className="flex justify-end"><CopyBtn texto={x.gancho} /></div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-5">
          <p className="text-white font-semibold mb-3 flex items-center gap-2"><FlaskConical className="w-4 h-4 text-primary" /> Pruebas A/B para este mes</p>
          <div className="space-y-4">
            {r.pruebas_ab!.map((t) => (
              <div key={t.nombre} className="text-sm">
                <p className="text-white font-medium mb-1">{t.nombre}</p>
                <p className="text-gray-300"><span className="text-primary font-semibold">A:</span> {t.a}</p>
                <p className="text-gray-300"><span className="text-primary font-semibold">B:</span> {t.b}</p>
                <p className="text-gray-500 text-xs mt-1">Medir: {t.medir}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="card p-5 overflow-x-auto">
          <p className="text-white font-semibold mb-3">Formatos que más clientes traen (90 días)</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 text-xs uppercase border-b border-border">
                <th className="text-left py-2">Red y formato</th><th className="text-right">Publicaciones</th><th className="text-right">Leads/post</th><th className="text-right">Alcance/post</th>
              </tr>
            </thead>
            <tbody>
              {r.formatos!.map((f) => (
                <tr key={`${f.red}-${f.formato}`} className="border-b border-border/50">
                  <td className="py-2 text-white">{f.nombre} · {f.formato}</td>
                  <td className="text-right text-gray-400">{f.publicaciones}</td>
                  <td className="text-right text-primary font-medium">{f.leads_por_publicacion}</td>
                  <td className="text-right text-gray-400">{formatNumber(f.alcance_por_publicacion)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Anuncios (copywriting skill)
// ---------------------------------------------------------------------------

function Anuncios({ vehiculo, setVehiculo }: { vehiculo: number | null; setVehiculo: (id: number) => void }) {
  const [vehiculos, setVehiculos] = useState<VehiculoAdmin[]>([]);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<TextosMarketing | null>(null);

  useEffect(() => { fetchInventario().then((all) => setVehiculos(all.filter((v) => v.estado !== 'vendido'))); }, []);
  useEffect(() => { if (vehiculo) run(vehiculo); }, [vehiculo]); // eslint-disable-line react-hooks/exhaustive-deps

  async function run(id = vehiculo) {
    if (!id) return;
    setLoading(true);
    try {
      setRes(await generarMarketing(id));
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudieron generar los textos'));
    } finally {
      setLoading(false);
    }
  }

  const usarDescripcion = async () => {
    if (!vehiculo || !res) return;
    try {
      await updateVehiculo(vehiculo, { descripcion: res.descripcion } as Partial<VehiculoInput>);
      toast.success('Descripción actualizada en el catálogo');
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo guardar'));
    }
  };

  return (
    <div className="space-y-6">
      <div className="card p-5 flex flex-col md:flex-row gap-3 md:items-end">
        <F label="Vehículo del inventario">
          <select value={vehiculo ?? ''} onChange={(e) => setVehiculo(Number(e.target.value))} className="select-field py-2 md:min-w-[420px]">
            <option value="" disabled>Elige un vehículo</option>
            {vehiculos.map((v) => <option key={v.id} value={v.id}>{v.marca} {v.modelo} {v.año} — {v.precio_venta ? formatCOP(v.precio_venta) : 's/precio'}</option>)}
          </select>
        </F>
        <button onClick={() => run()} disabled={!vehiculo || loading} className="btn-primary flex items-center gap-2 disabled:opacity-50 whitespace-nowrap">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Generar piezas
        </button>
      </div>

      {res && !loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Texto titulo="Título para TuCarro / Carroya" texto={res.titulo} />
          <Texto titulo="Mensaje de WhatsApp" texto={res.whatsapp} />
          <Texto
            titulo="Descripción para el catálogo"
            texto={res.descripcion}
            extra={<button onClick={usarDescripcion} className="btn-ghost text-xs flex items-center gap-1 px-2 py-1"><ArrowRight className="w-3 h-3" /> Usar en el catálogo</button>}
          />
          <Texto titulo="Post de Instagram" texto={res.instagram} />
          <p className="text-xs text-gray-500 lg:col-span-2 flex items-center gap-1">
            {res.analisis_ia ? <><Sparkles className="w-3 h-3 text-green-400" /> Redactado por Claude.</> : <><Cpu className="w-3 h-3" /> Plantilla con los datos reales del vehículo (activa Claude para textos más persuasivos).</>}
          </p>
        </div>
      )}
      {loading && <Cargando />}
      {!res && !loading && (
        <div className="card p-10 text-center text-gray-500">
          <Megaphone className="w-10 h-10 mx-auto mb-3" />
          Elige un carro y el agente escribe sus piezas: título del anuncio, descripción, post y mensaje de WhatsApp.
        </div>
      )}
    </div>
  );
}
