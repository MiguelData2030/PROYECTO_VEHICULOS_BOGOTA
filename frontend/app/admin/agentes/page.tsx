'use client';

import { Suspense, useEffect, useState, type FormEvent } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Bot, Calculator, Crosshair, Megaphone, Loader2, Sparkles, Cpu, ExternalLink, Copy, Check,
  ThumbsUp, ThumbsDown, Zap, ArrowRight,
} from 'lucide-react';
import toast from 'react-hot-toast';
import AdminShell from '@/components/AdminShell';
import { formatCOP, formatNumber, marcas } from '@/lib/data';
import {
  fetchAgentesEstado, valuarVehiculo, ejecutarCazador, generarMarketing, fetchInventario, updateVehiculo,
  apiErrorMessage, TRANSMISIONES, COMBUSTIBLES, TIPOS_VEHICULO,
  type AgentesEstado, type Valuacion, type ValuacionInput, type Caceria, type OportunidadCazada,
  type TextosMarketing, type VehiculoAdmin, type VehiculoInput,
} from '@/lib/api-admin';

type Tab = 'valuador' | 'cazador' | 'marketing';

const TABS: { key: Tab; label: string; icon: typeof Bot; desc: string }[] = [
  { key: 'valuador', label: 'Valuador', icon: Calculator, desc: 'Cuánto vale un carro, cuánto pagar como máximo y en cuánto venderlo' },
  { key: 'cazador', label: 'Cazador', icon: Crosshair, desc: 'Las mejores oportunidades de compra del mercado, priorizadas' },
  { key: 'marketing', label: 'Marketing', icon: Megaphone, desc: 'Anuncio, descripción, post de Instagram y WhatsApp de un carro' },
];

const EMPTY_VAL: ValuacionInput = {
  marca: 'Mazda', modelo: '', año: new Date().getFullYear() - 4, kilometraje: 50000,
  transmision: 'automatica', combustible: 'gasolina', color: 'Blanco', tipo_vehiculo: 'SUV',
  estado_mecanico: 'bueno', num_dueños: 1, precio_pedido: null,
};

export default function AgentesPage() {
  return (
    <Suspense fallback={null}>
      <Agentes />
    </Suspense>
  );
}

function Agentes() {
  const params = useSearchParams();
  const [tab, setTab] = useState<Tab>((params.get('agente') as Tab) || 'valuador');
  const [estado, setEstado] = useState<AgentesEstado | null>(null);
  const [valForm, setValForm] = useState<ValuacionInput>(EMPTY_VAL);
  const [valAuto, setValAuto] = useState(0); // bump to auto-run a valuation

  useEffect(() => { fetchAgentesEstado().then(setEstado); }, []);

  const valuarOportunidad = (o: OportunidadCazada) => {
    const [marca, ...resto] = o.titulo.split(' ');
    const año = Number(resto.pop());
    setValForm({ ...EMPTY_VAL, marca, modelo: resto.join(' '), año, kilometraje: o.kilometraje ?? 50000, precio_pedido: o.precio, url_anuncio: o.url });
    setTab('valuador');
    setValAuto((n) => n + 1);
  };

  return (
    <AdminShell title="Agentes IA" subtitle="Tu equipo de análisis: valuación, cacería de oportunidades y marketing">
      <div className={`card p-4 mb-6 flex items-start gap-3 ${estado?.ia_activa ? 'border-green-500/30' : ''}`}>
        {estado?.ia_activa ? <Sparkles className="w-5 h-5 text-green-400 mt-0.5" /> : <Cpu className="w-5 h-5 text-primary mt-0.5" />}
        <p className="text-sm text-gray-300">
          {estado?.ia_activa
            ? <>IA de Claude activa (<span className="text-white">{estado.modelo}</span>): los agentes agregan análisis escrito, estrategia de negociación y textos de venta redactados.</>
            : <>Modo cálculo propio: los agentes usan datos reales del mercado y tus ventas. Para agregar análisis escrito con Claude, configura <code className="text-primary">ANTHROPIC_API_KEY</code> en Render (servicio autonegocio-api → Environment).</>}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
        {TABS.map(({ key, label, icon: Icon, desc }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`card p-4 text-left transition-colors ${tab === key ? 'border-primary bg-primary/5' : ''}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <Icon className={`w-5 h-5 ${tab === key ? 'text-primary' : 'text-gray-400'}`} />
              <span className="text-white font-semibold">Agente {label}</span>
            </div>
            <p className="text-gray-500 text-xs">{desc}</p>
          </button>
        ))}
      </div>

      {tab === 'valuador' && <Valuador form={valForm} setForm={setValForm} autoRun={valAuto} />}
      {tab === 'cazador' && <Cazador onValuar={valuarOportunidad} />}
      {tab === 'marketing' && <Marketing vehiculoInicial={Number(params.get('vehiculo')) || null} />}
    </AdminShell>
  );
}

// ---------------------------------------------------------------------------
// Valuador
// ---------------------------------------------------------------------------

function Valuador({ form, setForm, autoRun }: {
  form: ValuacionInput; setForm: (f: ValuacionInput) => void; autoRun: number;
}) {
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<Valuacion | null>(null);
  const set = <K extends keyof ValuacionInput>(k: K, v: ValuacionInput[K]) => setForm({ ...form, [k]: v });

  const run = async () => {
    setLoading(true);
    try {
      setRes(await valuarVehiculo(form));
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo valuar'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (autoRun) run(); }, [autoRun]); // eslint-disable-line react-hooks/exhaustive-deps

  const submit = (e: FormEvent) => { e.preventDefault(); run(); };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <form onSubmit={submit} className="card p-5 lg:col-span-2 space-y-3 h-fit">
        <h3 className="text-white font-semibold mb-1">Vehículo a valuar</h3>
        <div className="grid grid-cols-2 gap-3">
          <F label="Marca">
            <select value={form.marca} onChange={(e) => set('marca', e.target.value)} className="select-field py-2">
              {marcas.map((m) => <option key={m}>{m}</option>)}
            </select>
          </F>
          <F label="Modelo"><input required value={form.modelo} onChange={(e) => setForm({ ...form, modelo: e.target.value, url_anuncio: null })} placeholder="CX-5" className="input-field py-2" /></F>
          <F label="Año"><input type="number" min={1990} max={2030} value={form.año} onChange={(e) => set('año', Number(e.target.value))} className="input-field py-2" /></F>
          <F label="Kilometraje"><Num value={form.kilometraje} onChange={(v) => set('kilometraje', v ?? 0)} /></F>
          <F label="Transmisión">
            <select value={form.transmision} onChange={(e) => set('transmision', e.target.value)} className="select-field py-2 capitalize">
              {TRANSMISIONES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </F>
          <F label="Combustible">
            <select value={form.combustible} onChange={(e) => set('combustible', e.target.value)} className="select-field py-2 capitalize">
              {COMBUSTIBLES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </F>
          <F label="Tipo">
            <select value={form.tipo_vehiculo} onChange={(e) => set('tipo_vehiculo', e.target.value)} className="select-field py-2">
              {TIPOS_VEHICULO.map((t) => <option key={t}>{t}</option>)}
            </select>
          </F>
          <F label="Color"><input value={form.color} onChange={(e) => set('color', e.target.value)} className="input-field py-2" /></F>
          <F label="Estado mecánico">
            <select value={form.estado_mecanico} onChange={(e) => set('estado_mecanico', e.target.value)} className="select-field py-2">
              <option value="excelente">Excelente</option><option value="bueno">Bueno</option><option value="regular">Regular</option>
            </select>
          </F>
          <F label="Dueños"><input type="number" min={1} value={form.num_dueños} onChange={(e) => set('num_dueños', Number(e.target.value) || 1)} className="input-field py-2" /></F>
        </div>
        <F label="Precio que pide el vendedor (opcional)"><Num value={form.precio_pedido} onChange={(v) => set('precio_pedido', v)} money /></F>
        <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Calculator className="w-4 h-4" />} Valuar
        </button>
      </form>

      <div className="lg:col-span-3 space-y-4">
        {!res && !loading && (
          <div className="card p-10 text-center text-gray-500">
            <Calculator className="w-10 h-10 mx-auto mb-3" />
            Ingresa los datos del carro. Si pones lo que pide el vendedor, te digo si comprar, negociar o pasar.
          </div>
        )}
        {loading && <div className="card p-10 flex justify-center"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>}
        {res && !loading && <ValuacionResultado r={res} />}
      </div>
    </div>
  );
}

const SEMAFORO = {
  verde: { cls: 'bg-green-500/10 border-green-500/40 text-green-400', label: 'Semáforo verde' },
  amarillo: { cls: 'bg-yellow-500/10 border-yellow-500/40 text-yellow-400', label: 'Semáforo amarillo' },
  rojo: { cls: 'bg-red-500/10 border-red-500/40 text-red-400', label: 'Semáforo rojo' },
};

function ValuacionResultado({ r }: { r: Valuacion }) {
  if (!r.valor_mercado) {
    return <div className="card p-6 text-gray-300 text-sm">{r.analisis}</div>;
  }
  return (
    <>
      {r.semaforo && (
        <div className={`rounded-xl border p-4 ${SEMAFORO[r.semaforo].cls}`}>
          <p className="text-xs uppercase tracking-wider font-semibold">{SEMAFORO[r.semaforo].label}</p>
          <p className="text-lg font-semibold text-white mt-1">{r.veredicto}</p>
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <Box label="Valor de mercado" value={formatCOP(r.valor_mercado)} sub={r.rango_mercado[0] ? `${formatCOP(r.rango_mercado[0])} – ${formatCOP(r.rango_mercado[1] ?? 0)}` : undefined} />
        <Box label="Publicar en" value={formatCOP(r.precio_venta_sugerido ?? 0)} accent="text-primary" />
        <Box label="Compra ideal" value={formatCOP(r.precio_compra_ideal ?? 0)} accent="text-green-400" />
        <Box label="Compra máxima rentable" value={formatCOP(r.precio_compra_maximo ?? 0)} accent="text-yellow-400" sub="10% neto mínimo" />
        <Box label="Costos estimados" value={formatCOP(r.costos_estimados ?? 0)} sub="Traspaso + alistamiento" />
        <Box label="Margen esperado" value={`${r.margen_esperado_pct}%`} sub={`Liquidez ${r.liquidez} · ~${r.dias_estimados_venta} días`} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="card p-4">
          <p className="text-green-400 text-sm font-semibold flex items-center gap-2 mb-2"><ThumbsUp className="w-4 h-4" /> A favor</p>
          <ul className="text-sm text-gray-300 space-y-1">{r.factores_positivos.map((f) => <li key={f}>• {f}</li>)}</ul>
        </div>
        <div className="card p-4">
          <p className="text-red-400 text-sm font-semibold flex items-center gap-2 mb-2"><ThumbsDown className="w-4 h-4" /> En contra</p>
          <ul className="text-sm text-gray-300 space-y-1">{r.factores_negativos.length ? r.factores_negativos.map((f) => <li key={f}>• {f}</li>) : <li className="text-gray-500">Nada relevante</li>}</ul>
        </div>
      </div>

      <div className="card p-5">
        <p className="text-white font-semibold flex items-center gap-2 mb-2">
          {r.analisis_ia ? <Sparkles className="w-4 h-4 text-green-400" /> : <Cpu className="w-4 h-4 text-primary" />}
          Análisis {r.analisis_ia ? 'de Claude' : 'del agente'}
        </p>
        <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{r.analisis}</p>
        <p className="text-xs text-gray-500 mt-3">Base: {r.metodo}.{r.historial.ventas ? ` Historial propio: ${r.historial.ventas} ventas de este modelo, margen ${r.historial.margen_promedio_pct}% y ${r.historial.dias_promedio} días promedio.` : ''}</p>
      </div>

      {r.comparables.length > 0 && (
        <div className="card p-5">
          <p className="text-white font-semibold mb-3">Anuncios comparables del mercado</p>
          <div className="space-y-2">
            {r.comparables.map((c) => (
              <a key={c.url} href={c.url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between gap-3 text-sm p-2 rounded-lg hover:bg-surface-light">
                <span className="text-gray-300">{c.titulo} · {c.kilometraje ? `${formatNumber(c.kilometraje)} km` : 's/km'} · {c.ubicacion ?? ''}</span>
                <span className="text-white font-medium whitespace-nowrap flex items-center gap-1">{formatCOP(c.precio)} <ExternalLink className="w-3 h-3 text-gray-500" /></span>
              </a>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Cazador
// ---------------------------------------------------------------------------

function Cazador({ onValuar }: { onValuar: (o: OportunidadCazada) => void }) {
  const [escanear, setEscanear] = useState(false);
  const [scoreMin, setScoreMin] = useState(55);
  const [marca, setMarca] = useState('');
  const [precioMax, setPrecioMax] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<Caceria | null>(null);

  const run = async () => {
    setLoading(true);
    try {
      setRes(await ejecutarCazador({ escanear, score_min: scoreMin, marca: marca || undefined, precio_max: precioMax ?? undefined }));
    } catch (e) {
      toast.error(apiErrorMessage(e, 'El Cazador no pudo completar la búsqueda'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="card p-5 grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
        <F label="Marca">
          <select value={marca} onChange={(e) => setMarca(e.target.value)} className="select-field py-2">
            <option value="">Todas</option>
            {marcas.map((m) => <option key={m}>{m}</option>)}
          </select>
        </F>
        <F label="Precio máximo"><Num value={precioMax} onChange={setPrecioMax} money /></F>
        <F label="Score mínimo">
          <select value={scoreMin} onChange={(e) => setScoreMin(Number(e.target.value))} className="select-field py-2">
            {[40, 50, 55, 60, 70].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </F>
        <label className="flex items-center gap-2 text-sm text-gray-300 pb-2 cursor-pointer">
          <input type="checkbox" checked={escanear} onChange={(e) => setEscanear(e.target.checked)} className="accent-primary w-4 h-4" />
          Escanear TuCarro ahora (≈1 min)
        </label>
        <button onClick={run} disabled={loading} className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />} Cazar
        </button>
      </div>

      {loading && <div className="card p-10 flex flex-col items-center gap-3 text-gray-400"><Loader2 className="w-8 h-8 text-primary animate-spin" />{escanear ? 'Escaneando el mercado y analizando…' : 'Analizando oportunidades…'}</div>}

      {res && !loading && (
        <>
          <div className="card p-5">
            <p className="text-white font-semibold flex items-center gap-2 mb-2">
              {res.analisis_ia ? <Sparkles className="w-4 h-4 text-green-400" /> : <Cpu className="w-4 h-4 text-primary" />}
              Reporte del Cazador
            </p>
            <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{res.resumen}</p>
            <p className="text-xs text-gray-500 mt-3">
              {res.escaneados != null ? `Escaneo nuevo: ${res.escaneados} anuncios. ` : ''}
              {res.total_mercado} anuncios en la base{res.ultima_actualizacion ? `, última actualización ${new Date(res.ultima_actualizacion).toLocaleString('es-CO')}` : ''}.
            </p>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {res.oportunidades.map((o) => (
              <div key={o.id} className="card p-4 flex flex-col gap-2">
                <div className="flex justify-between gap-2">
                  <div>
                    <p className="text-white font-semibold">{o.titulo}</p>
                    <p className="text-gray-500 text-xs">{[o.kilometraje ? `${formatNumber(o.kilometraje)} km` : null, o.ubicacion].filter(Boolean).join(' · ')}</p>
                  </div>
                  <span className="text-xs font-semibold px-2 py-1 rounded-full bg-primary/10 text-primary h-fit">{o.score.toFixed(0)}</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div><p className="text-gray-500 text-xs">Piden</p><p className="text-white">{formatCOP(o.precio)}</p></div>
                  <div><p className="text-gray-500 text-xs">Mercado</p><p className="text-gray-300">{o.precio_mercado ? formatCOP(o.precio_mercado) : '-'}</p></div>
                  <div><p className="text-gray-500 text-xs">Ganancia potencial</p><p className={(o.margen_potencial_pct ?? 0) >= 10 ? 'text-green-400' : 'text-yellow-400'}>{o.ganancia_potencial ? `${formatCOP(o.ganancia_potencial)} (${o.margen_potencial_pct}%)` : '-'}</p></div>
                </div>
                <div className="flex gap-2 pt-2 border-t border-border mt-1">
                  <button onClick={() => onValuar(o)} className="btn-ghost text-sm flex items-center gap-1 px-2"><Calculator className="w-4 h-4" /> Valuar a fondo</button>
                  <a href={o.url} target="_blank" rel="noopener noreferrer" className="btn-ghost text-sm flex items-center gap-1 px-2 ml-auto">Ver anuncio <ExternalLink className="w-4 h-4" /></a>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
      {!res && !loading && (
        <div className="card p-10 text-center text-gray-500">
          <Crosshair className="w-10 h-10 mx-auto mb-3" />
          Pulsa <b>Cazar</b> para analizar los anuncios ya recolectados, o marca &quot;Escanear TuCarro ahora&quot; para traer los más recientes.
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Marketing
// ---------------------------------------------------------------------------

function Marketing({ vehiculoInicial }: { vehiculoInicial: number | null }) {
  const [vehiculos, setVehiculos] = useState<VehiculoAdmin[]>([]);
  const [vid, setVid] = useState<number | null>(vehiculoInicial);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<TextosMarketing | null>(null);

  useEffect(() => { fetchInventario().then((all) => setVehiculos(all.filter((v) => v.estado !== 'vendido'))); }, []);
  useEffect(() => { if (vehiculoInicial) run(vehiculoInicial); }, [vehiculoInicial]); // eslint-disable-line react-hooks/exhaustive-deps

  async function run(id = vid) {
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
    if (!vid || !res) return;
    try {
      await updateVehiculo(vid, { descripcion: res.descripcion } as Partial<VehiculoInput>);
      toast.success('Descripción actualizada en el catálogo');
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo guardar'));
    }
  };

  return (
    <div className="space-y-6">
      <div className="card p-5 flex flex-col md:flex-row gap-3 md:items-end">
        <F label="Vehículo del inventario">
          <select value={vid ?? ''} onChange={(e) => setVid(Number(e.target.value))} className="select-field py-2 md:min-w-[420px]">
            <option value="" disabled>Elige un vehículo</option>
            {vehiculos.map((v) => <option key={v.id} value={v.id}>{v.marca} {v.modelo} {v.año} — {v.precio_venta ? formatCOP(v.precio_venta) : 's/precio'}</option>)}
          </select>
        </F>
        <button onClick={() => run()} disabled={!vid || loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Megaphone className="w-4 h-4" />} Generar textos
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
      {loading && <div className="card p-10 flex justify-center"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>}
      {!res && !loading && (
        <div className="card p-10 text-center text-gray-500">
          <Megaphone className="w-10 h-10 mx-auto mb-3" />
          Elige un carro y genera su anuncio. También puedes abrirlo desde Inventario con el botón de megáfono.
        </div>
      )}
    </div>
  );
}

function Texto({ titulo, texto, extra }: { titulo: string; texto: string; extra?: React.ReactNode }) {
  const [copiado, setCopiado] = useState(false);
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 1500);
    } catch {
      toast.error('No se pudo copiar');
    }
  };
  return (
    <div className="card p-4 flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <p className="text-primary text-xs font-semibold uppercase tracking-wider">{titulo}</p>
        <div className="flex gap-1">
          {extra}
          <button onClick={copiar} className="btn-ghost text-xs flex items-center gap-1 px-2 py-1">
            {copiado ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />} {copiado ? 'Copiado' : 'Copiar'}
          </button>
        </div>
      </div>
      <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{texto}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small UI helpers
// ---------------------------------------------------------------------------

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="w-full">
      <label className="block text-gray-400 text-xs mb-1">{label}</label>
      {children}
    </div>
  );
}

function Num({ value, onChange, money }: { value: number | null; onChange: (v: number | null) => void; money?: boolean }) {
  return (
    <input
      inputMode="numeric"
      value={value !== null ? formatNumber(value) : ''}
      onChange={(e) => {
        const d = e.target.value.replace(/\D/g, '');
        onChange(d === '' ? null : Number(d));
      }}
      placeholder={money ? '$ 0' : '0'}
      className="input-field py-2"
    />
  );
}

function Box({ label, value, sub, accent = 'text-white' }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className="card p-3">
      <p className="text-gray-500 text-xs">{label}</p>
      <p className={`text-lg font-bold ${accent}`}>{value}</p>
      {sub && <p className="text-gray-500 text-xs mt-0.5">{sub}</p>}
    </div>
  );
}
