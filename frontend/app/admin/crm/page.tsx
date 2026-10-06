'use client';

import { useEffect, useMemo, useState, type DragEvent, type FormEvent } from 'react';
import {
  KanbanSquare, Loader2, Plus, X, Phone, MessageCircle, CalendarClock, AlertTriangle, Target, TrendingUp,
  Users, Clock, Send, User,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import toast from 'react-hot-toast';
import AdminShell from '@/components/AdminShell';
import { formatCOP, formatCOPCompact } from '@/lib/data';
import { canalInfo, CANAL_INFO } from '@/lib/canales';
import {
  fetchPipeline, fetchResumenCRM, fetchSeguimiento, updateSeguimiento, addInteraccion, createSeguimiento,
  fetchInventario, apiErrorMessage, ETAPAS_CRM, TIPOS_INTERACCION,
  type SeguimientoCRM, type ResumenCRM, type EtapaCRM, type VehiculoAdmin,
} from '@/lib/api-admin';

const ETAPA: Record<EtapaCRM, { label: string; cls: string }> = {
  nuevo: { label: 'Nuevo', cls: 'border-t-gray-400' },
  contactado: { label: 'Contactado', cls: 'border-t-blue-400' },
  cita: { label: 'Cita / test drive', cls: 'border-t-purple-400' },
  negociacion: { label: 'Negociación', cls: 'border-t-primary' },
  ganado: { label: 'Ganado', cls: 'border-t-green-500' },
  perdido: { label: 'Perdido', cls: 'border-t-red-500' },
};
const INTERACCION_LABEL: Record<string, string> = {
  llamada: 'Llamada', whatsapp: 'WhatsApp', mensaje_red: 'Mensaje en redes', email: 'Email / formulario',
  visita: 'Visita', test_drive: 'Test drive', cotizacion: 'Cotización', nota: 'Nota',
};
const MOTIVOS = [
  'Compró en otro concesionario', 'No le aprobaron el crédito', 'El precio quedó fuera de su presupuesto',
  'Dejó de responder', 'Buscaba un modelo más reciente', 'Encontró un particular más barato', 'Otro',
];
const ASESORES = ['Andrea Gómez', 'Felipe Rojas', 'Gerencia'];

function fechaCorta(iso: string | null) {
  if (!iso) return '';
  const d = new Date(iso.length === 10 ? `${iso}T12:00:00` : iso);
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short' });
}

function waLink(tel: string | null) {
  const d = (tel ?? '').replace(/\D/g, '');
  return d ? `https://wa.me/${d.length === 10 ? '57' + d : d}` : null;
}

export default function CRMPage() {
  const [items, setItems] = useState<SeguimientoCRM[]>([]);
  const [resumen, setResumen] = useState<ResumenCRM | null>(null);
  const [loading, setLoading] = useState(true);
  const [tipo, setTipo] = useState<'' | 'compra' | 'venta'>('');
  const [responsable, setResponsable] = useState('');
  const [abierto, setAbierto] = useState<number | null>(null);
  const [nuevo, setNuevo] = useState(false);
  const [drag, setDrag] = useState<number | null>(null);

  const load = async () => {
    try {
      const [p, r] = await Promise.all([fetchPipeline(), fetchResumenCRM()]);
      setItems(p);
      setResumen(r);
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo cargar el CRM'));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const visibles = useMemo(
    () => items.filter((s) => (!tipo || s.tipo === tipo) && (!responsable || s.responsable === responsable)),
    [items, tipo, responsable],
  );

  const mover = async (id: number, etapa: EtapaCRM) => {
    const s = items.find((x) => x.id === id);
    if (!s || s.etapa === etapa) return;
    if (etapa === 'perdido') {
      setAbierto(id);
      toast('Indica el motivo de pérdida en la ficha', { icon: 'ℹ️' });
      return;
    }
    setItems((prev) => prev.map((x) => (x.id === id ? { ...x, etapa } : x)));
    try {
      const u = await updateSeguimiento(id, { etapa });
      setItems((prev) => prev.map((x) => (x.id === id ? u : x)));
      if (etapa === 'ganado') toast.success(`¡Negocio ganado con ${u.cliente?.nombre}! Regístralo en Ventas.`);
      fetchResumenCRM().then(setResumen);
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo mover'));
      load();
    }
  };

  const onDrop = (e: DragEvent, etapa: EtapaCRM) => {
    e.preventDefault();
    if (drag !== null) mover(drag, etapa);
    setDrag(null);
  };

  const canalesData = resumen
    ? Object.entries(resumen.por_canal).map(([k, v]) => ({ canal: canalInfo(k).label, Leads: v.leads, Ganados: v.ganados }))
    : [];

  return (
    <AdminShell
      title="CRM de ventas"
      subtitle="Seguimiento de cada negocio, desde el primer mensaje hasta el cierre"
      actions={
        <button onClick={() => setNuevo(true)} className="btn-primary flex items-center gap-2 text-sm py-2">
          <Plus className="w-4 h-4" /> Nuevo lead
        </button>
      }
    >
      {resumen && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Kpi icon={KanbanSquare} label="Negocios abiertos" value={String(resumen.abiertos)} sub={`${formatCOPCompact(resumen.valor_pipeline)} en juego`} />
          <Kpi icon={TrendingUp} label="Valor ponderado" value={formatCOPCompact(resumen.valor_ponderado)} sub="Según probabilidad por etapa" accent="text-green-400" />
          <Kpi icon={Target} label="Tasa de cierre" value={resumen.conversion_pct != null ? `${resumen.conversion_pct}%` : '-'} sub="Ganados / cerrados (12 meses)" accent="text-primary" />
          <Kpi icon={AlertTriangle} label="Acciones vencidas" value={String(resumen.acciones_vencidas)} sub={`${resumen.acciones_hoy} para hoy`} accent={resumen.acciones_vencidas ? 'text-red-400' : 'text-white'} />
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <select value={tipo} onChange={(e) => setTipo(e.target.value as typeof tipo)} className="select-field py-2 w-52">
          <option value="">Compradores y vendedores</option>
          <option value="compra">Clientes que compran</option>
          <option value="venta">Personas que nos venden</option>
        </select>
        <select value={responsable} onChange={(e) => setResponsable(e.target.value)} className="select-field py-2 w-48">
          <option value="">Todos los asesores</option>
          {ASESORES.map((a) => <option key={a}>{a}</option>)}
        </select>
        <p className="text-gray-500 text-xs self-center">Arrastra las tarjetas entre columnas para cambiar la etapa.</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-24"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-4 mb-8">
          {ETAPAS_CRM.map((etapa) => {
            const col = visibles.filter((s) => s.etapa === etapa);
            const valor = col.reduce((a, s) => a + (s.valor_estimado ?? 0), 0);
            return (
              <div
                key={etapa}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => onDrop(e, etapa)}
                className={`min-w-[250px] w-[250px] flex-shrink-0 bg-surface/60 rounded-xl border border-border border-t-4 ${ETAPA[etapa].cls}`}
              >
                <div className="p-3 border-b border-border">
                  <p className="text-white font-semibold text-sm">{ETAPA[etapa].label} <span className="text-gray-500">({col.length})</span></p>
                  <p className="text-gray-500 text-xs">{valor ? formatCOPCompact(valor) : '—'}</p>
                </div>
                <div className="p-2 space-y-2 max-h-[560px] overflow-y-auto">
                  {col.map((s) => (
                    <Tarjeta key={s.id} s={s} onOpen={() => setAbierto(s.id)} onDragStart={() => setDrag(s.id)} />
                  ))}
                  {col.length === 0 && <p className="text-gray-600 text-xs text-center py-6">Sin negocios</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {resumen && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="card p-5 lg:col-span-2">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2"><Users className="w-4 h-4 text-primary" /> Leads y cierres por canal (12 meses)</h3>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={canalesData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="canal" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8 }} labelStyle={{ color: '#fff' }} />
                <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
                <Bar dataKey="Leads" fill="#6b7280" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Ganados" fill="#d4a843" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="card p-5">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2"><AlertTriangle className="w-4 h-4 text-red-400" /> Por qué se pierden negocios</h3>
            <div className="space-y-3">
              {Object.entries(resumen.motivos_perdida).map(([m, n]) => {
                const max = Math.max(...Object.values(resumen.motivos_perdida));
                return (
                  <div key={m}>
                    <div className="flex justify-between text-xs text-gray-300 mb-1"><span>{m}</span><span>{n}</span></div>
                    <div className="h-2 bg-dark rounded-full"><div className="h-2 bg-red-500/60 rounded-full" style={{ width: `${(n / max) * 100}%` }} /></div>
                  </div>
                );
              })}
              {Object.keys(resumen.motivos_perdida).length === 0 && <p className="text-gray-500 text-sm">Sin negocios perdidos registrados.</p>}
            </div>
          </div>
        </div>
      )}

      {abierto !== null && (
        <Ficha
          id={abierto}
          onClose={() => setAbierto(null)}
          onChange={(u) => { setItems((prev) => prev.map((x) => (x.id === u.id ? u : x))); fetchResumenCRM().then(setResumen); }}
        />
      )}
      {nuevo && (
        <NuevoLead
          onClose={() => setNuevo(false)}
          onCreated={(s) => { setItems((prev) => [s, ...prev]); setNuevo(false); fetchResumenCRM().then(setResumen); }}
        />
      )}
    </AdminShell>
  );
}

function Kpi({ icon: Icon, label, value, sub, accent = 'text-white' }: {
  icon: typeof Target; label: string; value: string; sub?: string; accent?: string;
}) {
  return (
    <div className="card p-4">
      <Icon className="w-4 h-4 text-primary mb-2" />
      <p className={`text-xl font-bold ${accent}`}>{value}</p>
      <p className="text-gray-400 text-xs">{label}</p>
      {sub && <p className="text-gray-600 text-xs mt-0.5">{sub}</p>}
    </div>
  );
}

function Tarjeta({ s, onOpen, onDragStart }: { s: SeguimientoCRM; onOpen: () => void; onDragStart: () => void }) {
  const canal = canalInfo(s.canal);
  const hoy = new Date().toLocaleDateString('en-CA'); // local YYYY-MM-DD
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onClick={onOpen}
      className={`bg-dark rounded-lg p-3 border cursor-pointer hover:border-primary/50 transition-colors ${s.vencida ? 'border-red-500/50' : 'border-border'}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-white text-sm font-medium leading-tight">{s.cliente?.nombre ?? 'Cliente'}</p>
        <span className={`text-[10px] px-1.5 py-0.5 rounded ${canal.cls} whitespace-nowrap`}>{canal.label}</span>
      </div>
      {s.tipo === 'venta' ? (
        <p className="text-orange-300 text-xs mt-1">Nos quiere vender{s.notas ? `: ${s.notas.replace('Quiere vender: ', '')}` : ''}</p>
      ) : s.vehiculo ? (
        <div className="flex items-center gap-2 mt-2">
          {s.vehiculo.foto && <img src={s.vehiculo.foto} alt="" className="w-10 h-7 rounded object-cover" />}
          <p className="text-gray-400 text-xs leading-tight">{s.vehiculo.nombre}</p>
        </div>
      ) : null}
      {s.valor_estimado ? <p className="text-primary text-xs font-medium mt-1">{formatCOP(s.valor_estimado)}</p> : null}
      {s.proxima_accion && (
        <p className={`text-[11px] mt-2 flex items-center gap-1 ${s.vencida ? 'text-red-400' : s.fecha_proxima === hoy ? 'text-yellow-300' : 'text-gray-500'}`}>
          <CalendarClock className="w-3 h-3 flex-shrink-0" />
          <span className="truncate">{s.proxima_accion}</span>
          <span className="whitespace-nowrap">· {s.vencida ? 'vencida' : s.fecha_proxima === hoy ? 'hoy' : fechaCorta(s.fecha_proxima)}</span>
        </p>
      )}
      {s.etapa === 'perdido' && s.motivo_perdida && <p className="text-red-400/80 text-[11px] mt-1">{s.motivo_perdida}</p>}
      <div className="flex items-center justify-between mt-2 text-[10px] text-gray-600">
        <span className="flex items-center gap-1"><User className="w-3 h-3" />{s.responsable ?? 'Sin asignar'}</span>
        <span>{s.n_interacciones} {s.n_interacciones === 1 ? 'interacción' : 'interacciones'}</span>
      </div>
    </div>
  );
}

function Ficha({ id, onClose, onChange }: { id: number; onClose: () => void; onChange: (s: SeguimientoCRM) => void }) {
  const [s, setS] = useState<SeguimientoCRM | null>(null);
  const [tipo, setTipo] = useState('whatsapp');
  const [texto, setTexto] = useState('');
  const [motivo, setMotivo] = useState(MOTIVOS[0]);
  const [accion, setAccion] = useState('');
  const [fecha, setFecha] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchSeguimiento(id).then((d) => { setS(d); setAccion(d.proxima_accion ?? ''); setFecha(d.fecha_proxima ?? ''); });
  }, [id]);

  const aplicar = async (fn: () => Promise<SeguimientoCRM>, ok?: string) => {
    setBusy(true);
    try {
      const u = await fn();
      setS(u);
      onChange(u);
      if (ok) toast.success(ok);
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo guardar'));
    } finally {
      setBusy(false);
    }
  };

  const registrar = (e: FormEvent) => {
    e.preventDefault();
    if (!texto.trim()) return;
    aplicar(() => addInteraccion(id, tipo, texto.trim()), 'Interacción registrada').then(() => setTexto(''));
  };

  const wa = waLink(s?.cliente?.telefono ?? null);

  return (
    <div className="fixed inset-0 z-[60] bg-black/60 flex justify-end" onClick={onClose}>
      <div className="w-full max-w-lg h-full bg-surface border-l border-border overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        {!s ? (
          <div className="flex justify-center py-24"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>
        ) : (
          <div className="p-5 space-y-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-white text-lg font-semibold">{s.cliente?.nombre}</p>
                <p className="text-gray-500 text-xs">
                  {s.tipo === 'venta' ? 'Nos quiere vender su carro' : 'Cliente comprador'} · {canalInfo(s.canal).label} · desde {fechaCorta(s.created_at)}
                </p>
              </div>
              <button onClick={onClose} className="btn-ghost p-2"><X className="w-5 h-5" /></button>
            </div>

            <div className="flex flex-wrap gap-2">
              {wa && <a href={wa} target="_blank" rel="noopener noreferrer" className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1"><MessageCircle className="w-3 h-3" /> WhatsApp</a>}
              {s.cliente?.telefono && <a href={`tel:${s.cliente.telefono}`} className="btn-ghost text-xs py-1.5 px-3 flex items-center gap-1 border border-border"><Phone className="w-3 h-3" /> Llamar</a>}
              {!s.cliente?.telefono && <span className="text-gray-600 text-xs">Sin teléfono registrado (datos demo)</span>}
            </div>

            {s.vehiculo && (
              <div className="flex items-center gap-3 bg-dark rounded-lg p-3">
                {s.vehiculo.foto && <img src={s.vehiculo.foto} alt="" className="w-20 h-14 rounded object-cover" />}
                <div>
                  <p className="text-white text-sm font-medium">{s.vehiculo.nombre}</p>
                  <p className="text-primary text-sm">{s.vehiculo.precio ? formatCOP(s.vehiculo.precio) : ''}</p>
                  <p className="text-gray-500 text-xs capitalize">{s.vehiculo.estado.replace('_', ' ')}</p>
                </div>
              </div>
            )}

            <div>
              <p className="text-gray-400 text-xs mb-2">Etapa (probabilidad {s.probabilidad ?? 0}%)</p>
              <div className="grid grid-cols-3 gap-1">
                {ETAPAS_CRM.filter((e) => e !== 'perdido').map((e) => (
                  <button key={e} disabled={busy} onClick={() => aplicar(() => updateSeguimiento(id, { etapa: e }), `Movido a ${ETAPA[e].label}`)}
                    className={`text-xs py-1.5 rounded-lg border ${s.etapa === e ? 'bg-primary text-dark border-primary font-semibold' : 'border-border text-gray-300 hover:border-primary/50'}`}>
                    {ETAPA[e].label}
                  </button>
                ))}
              </div>
              {s.etapa !== 'perdido' && s.etapa !== 'ganado' && (
                <div className="flex gap-2 mt-2">
                  <select value={motivo} onChange={(e) => setMotivo(e.target.value)} className="select-field py-1.5 text-xs">
                    {MOTIVOS.map((m) => <option key={m}>{m}</option>)}
                  </select>
                  <button disabled={busy} onClick={() => aplicar(() => updateSeguimiento(id, { etapa: 'perdido', motivo_perdida: motivo }), 'Marcado como perdido')}
                    className="text-xs px-3 rounded-lg border border-red-500/40 text-red-400 whitespace-nowrap">Marcar perdido</button>
                </div>
              )}
              {s.etapa === 'perdido' && <p className="text-red-400 text-xs mt-2">Perdido: {s.motivo_perdida}</p>}
            </div>

            {s.etapa !== 'ganado' && s.etapa !== 'perdido' && (
              <div className="bg-dark rounded-lg p-3 space-y-2">
                <p className="text-gray-400 text-xs flex items-center gap-1"><Clock className="w-3 h-3" /> Próxima acción</p>
                <input value={accion} onChange={(e) => setAccion(e.target.value)} placeholder="Ej: Llamar para agendar test drive" className="input-field py-1.5 text-sm" />
                <div className="flex gap-2">
                  <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="input-field py-1.5 text-sm" />
                  <select defaultValue={s.responsable ?? ''} onChange={(e) => aplicar(() => updateSeguimiento(id, { responsable: e.target.value || null }), 'Asesor asignado')} className="select-field py-1.5 text-sm">
                    <option value="">Sin asignar</option>
                    {ASESORES.map((a) => <option key={a}>{a}</option>)}
                  </select>
                </div>
                <button disabled={busy} onClick={() => aplicar(() => updateSeguimiento(id, { proxima_accion: accion || null, fecha_proxima: fecha || null }), 'Próxima acción guardada')}
                  className="btn-secondary text-xs py-1.5 px-3">Guardar próxima acción</button>
              </div>
            )}

            <form onSubmit={registrar} className="space-y-2">
              <p className="text-gray-400 text-xs">Registrar interacción</p>
              <div className="flex gap-2">
                <select value={tipo} onChange={(e) => setTipo(e.target.value)} className="select-field py-1.5 text-sm w-40">
                  {TIPOS_INTERACCION.map((t) => <option key={t} value={t}>{INTERACCION_LABEL[t]}</option>)}
                </select>
                <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="¿Qué pasó?" className="input-field py-1.5 text-sm" />
                <button disabled={busy} className="btn-primary px-3 py-1.5"><Send className="w-4 h-4" /></button>
              </div>
            </form>

            <div>
              <p className="text-gray-400 text-xs mb-3">Historial</p>
              <ol className="relative border-l border-border ml-2 space-y-4">
                {[...(s.interacciones ?? [])].reverse().map((i) => (
                  <li key={i.id} className="ml-4">
                    <span className="absolute -left-1.5 w-3 h-3 rounded-full bg-primary/70 border border-dark" />
                    <p className="text-xs text-gray-500">{new Date(i.fecha).toLocaleString('es-CO', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })} · {INTERACCION_LABEL[i.tipo] ?? i.tipo}</p>
                    <p className="text-sm text-gray-200">{i.resumen}</p>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function NuevoLead({ onClose, onCreated }: { onClose: () => void; onCreated: (s: SeguimientoCRM) => void }) {
  const [vehiculos, setVehiculos] = useState<VehiculoAdmin[]>([]);
  const [form, setForm] = useState({ nombre: '', telefono: '', canal: 'instagram', tipo: 'compra' as 'compra' | 'venta', vehiculo_id: '', responsable: '' });
  const [busy, setBusy] = useState(false);
  useEffect(() => { fetchInventario().then((all) => setVehiculos(all.filter((v) => v.estado !== 'vendido'))); }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const s = await createSeguimiento({
        cliente_nuevo: { nombre: form.nombre, telefono: form.telefono || null },
        tipo: form.tipo, canal: form.canal, vehiculo_id: form.vehiculo_id ? Number(form.vehiculo_id) : null,
        responsable: form.responsable || null,
      });
      toast.success('Lead creado');
      onCreated(s);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'No se pudo crear'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-start justify-center p-4 overflow-y-auto" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()} className="card-elevated w-full max-w-md my-12 p-5 space-y-3">
        <div className="flex justify-between items-center">
          <h2 className="text-white font-semibold">Nuevo lead</h2>
          <button type="button" onClick={onClose} className="btn-ghost p-1"><X className="w-5 h-5" /></button>
        </div>
        <input required placeholder="Nombre" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} className="input-field py-2" />
        <input placeholder="Teléfono / WhatsApp" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} className="input-field py-2" />
        <div className="grid grid-cols-2 gap-2">
          <select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value as 'compra' | 'venta' })} className="select-field py-2">
            <option value="compra">Quiere comprar</option>
            <option value="venta">Quiere vendernos</option>
          </select>
          <select value={form.canal} onChange={(e) => setForm({ ...form, canal: e.target.value })} className="select-field py-2">
            {Object.entries(CANAL_INFO).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
        </div>
        {form.tipo === 'compra' && (
          <select value={form.vehiculo_id} onChange={(e) => setForm({ ...form, vehiculo_id: e.target.value })} className="select-field py-2">
            <option value="">Vehículo de interés (opcional)</option>
            {vehiculos.map((v) => <option key={v.id} value={v.id}>{v.marca} {v.modelo} {v.año}</option>)}
          </select>
        )}
        <select value={form.responsable} onChange={(e) => setForm({ ...form, responsable: e.target.value })} className="select-field py-2">
          <option value="">Asesor (opcional)</option>
          {ASESORES.map((a) => <option key={a}>{a}</option>)}
        </select>
        <button disabled={busy} className="btn-primary w-full flex items-center justify-center gap-2">
          {busy && <Loader2 className="w-4 h-4 animate-spin" />} Crear lead
        </button>
      </form>
    </div>
  );
}
