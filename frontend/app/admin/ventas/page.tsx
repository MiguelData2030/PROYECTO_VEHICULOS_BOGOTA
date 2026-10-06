'use client';

import { Suspense, useEffect, useMemo, useState, type FormEvent } from 'react';
import { useSearchParams } from 'next/navigation';
import { Loader2, Plus, Receipt, Trash2, X, TrendingUp, DollarSign, Percent, Clock } from 'lucide-react';
import toast from 'react-hot-toast';
import AdminShell from '@/components/AdminShell';
import { formatCOP, formatCOPCompact, formatNumber } from '@/lib/data';
import {
  fetchTransacciones, fetchInventario, fetchClientes, createTransaccion, createCliente, deleteTransaccion,
  apiErrorMessage, type Transaccion, type VehiculoAdmin, type Cliente,
} from '@/lib/api-admin';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

function mesLabel(key: string) {
  const [y, m] = key.split('-');
  return `${MESES[Number(m) - 1]} ${y}`;
}

export default function VentasPage() {
  return (
    <Suspense fallback={null}>
      <Ventas />
    </Suspense>
  );
}

function Ventas() {
  const searchParams = useSearchParams();
  const [ventas, setVentas] = useState<Transaccion[]>([]);
  const [loading, setLoading] = useState(true);
  const [periodo, setPeriodo] = useState('12m');
  const [modal, setModal] = useState<number | 'new' | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setVentas(await fetchTransacciones({ tipo: 'venta' }));
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudieron cargar las ventas'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // /admin/ventas?vehiculo=12 opens the form with that vehicle selected
  useEffect(() => {
    const v = searchParams.get('vehiculo');
    if (v) setModal(Number(v));
  }, [searchParams]);

  const meses = useMemo(
    () => Array.from(new Set(ventas.map((v) => v.fecha.slice(0, 7)))).sort().reverse(),
    [ventas],
  );

  const filtradas = useMemo(() => {
    if (periodo === '12m') {
      const desde = new Date();
      desde.setMonth(desde.getMonth() - 12);
      return ventas.filter((v) => new Date(v.fecha) >= desde);
    }
    if (periodo === 'todo') return ventas;
    return ventas.filter((v) => v.fecha.startsWith(periodo));
  }, [ventas, periodo]);

  const resumen = useMemo(() => {
    const ingresos = filtradas.reduce((s, v) => s + v.precio, 0);
    const ganancia = filtradas.reduce((s, v) => s + (v.ganancia_neta ?? 0), 0);
    const margenes = filtradas.map((v) => v.margen_pct).filter((m): m is number => m != null);
    const dias = filtradas.map((v) => v.dias_en_inventario).filter((d): d is number => d != null);
    return {
      n: filtradas.length,
      ingresos,
      ganancia,
      margen: margenes.length ? margenes.reduce((a, b) => a + b, 0) / margenes.length : null,
      dias: dias.length ? dias.reduce((a, b) => a + b, 0) / dias.length : null,
    };
  }, [filtradas]);

  const anular = async (v: Transaccion) => {
    if (!confirm(`¿Anular la venta del ${v.vehiculo_nombre}? El vehículo vuelve a quedar disponible.`)) return;
    try {
      await deleteTransaccion(v.id);
      setVentas((prev) => prev.filter((x) => x.id !== v.id));
      toast.success('Venta anulada');
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo anular'));
    }
  };

  return (
    <AdminShell
      title="Ventas"
      subtitle="Historial de ventas, ganancia neta y margen por vehículo"
      actions={
        <button onClick={() => setModal('new')} className="btn-primary flex items-center gap-2 text-sm py-2">
          <Plus className="w-4 h-4" /> Registrar venta
        </button>
      }
    >
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <select value={periodo} onChange={(e) => setPeriodo(e.target.value)} className="select-field py-2 w-56">
          <option value="12m">Últimos 12 meses</option>
          <option value="todo">Todo el historial</option>
          {meses.map((m) => <option key={m} value={m}>{mesLabel(m)}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <Stat icon={Receipt} label="Ventas" value={formatNumber(resumen.n)} />
        <Stat icon={DollarSign} label="Ingresos" value={formatCOPCompact(resumen.ingresos)} />
        <Stat icon={TrendingUp} label="Ganancia neta" value={formatCOPCompact(resumen.ganancia)} accent={resumen.ganancia >= 0 ? 'text-green-400' : 'text-red-400'} />
        <Stat icon={Percent} label="Margen promedio" value={resumen.margen != null ? `${resumen.margen.toFixed(1)}%` : '-'} />
        <Stat icon={Clock} label="Días para vender" value={resumen.dias != null ? resumen.dias.toFixed(0) : '-'} />
      </div>

      {loading ? (
        <div className="flex justify-center py-24"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>
      ) : filtradas.length === 0 ? (
        <div className="card p-12 text-center text-gray-500">
          <Receipt className="w-10 h-10 mx-auto mb-3" />
          No hay ventas en este periodo.
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-gray-500 text-xs uppercase">
                <th className="text-left py-3 px-4">Fecha</th>
                <th className="text-left py-3 px-3">Vehículo</th>
                <th className="text-left py-3 px-3">Cliente</th>
                <th className="text-right py-3 px-3">Precio</th>
                <th className="text-right py-3 px-3">Ganancia</th>
                <th className="text-right py-3 px-3">Margen</th>
                <th className="text-center py-3 px-3">Días</th>
                <th className="py-3 px-4" />
              </tr>
            </thead>
            <tbody>
              {filtradas.map((v) => (
                <tr key={v.id} className="border-b border-border/50 hover:bg-surface-light transition-colors" title={v.notas ?? ''}>
                  <td className="py-3 px-4 text-gray-400 whitespace-nowrap">
                    {new Date(v.fecha).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </td>
                  <td className="py-3 px-3 text-white font-medium">{v.vehiculo_nombre}</td>
                  <td className="py-3 px-3 text-gray-400">{v.cliente_nombre}</td>
                  <td className="py-3 px-3 text-right text-white">{formatCOP(v.precio)}</td>
                  <td className={`py-3 px-3 text-right font-medium ${(v.ganancia_neta ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {v.ganancia_neta != null ? formatCOP(v.ganancia_neta) : '-'}
                  </td>
                  <td className="py-3 px-3 text-right text-gray-300">{v.margen_pct != null ? `${v.margen_pct.toFixed(1)}%` : '-'}</td>
                  <td className={`py-3 px-3 text-center ${(v.dias_en_inventario ?? 0) > 60 ? 'text-red-400' : 'text-gray-400'}`}>
                    {v.dias_en_inventario ?? '-'}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button onClick={() => anular(v)} className="btn-ghost p-2 hover:text-red-400" title="Anular venta">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal !== null && (
        <VentaModal
          vehiculoId={modal === 'new' ? null : modal}
          onClose={() => setModal(null)}
          onSaved={(tx) => { setVentas((prev) => [tx, ...prev]); setModal(null); }}
        />
      )}
    </AdminShell>
  );
}

function Stat({ icon: Icon, label, value, accent = 'text-white' }: {
  icon: typeof Receipt; label: string; value: string; accent?: string;
}) {
  return (
    <div className="card p-4">
      <Icon className="w-4 h-4 text-primary mb-2" />
      <p className={`text-xl font-bold ${accent}`}>{value}</p>
      <p className="text-gray-500 text-xs">{label}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Register a sale
// ---------------------------------------------------------------------------

function VentaModal({ vehiculoId, onClose, onSaved }: {
  vehiculoId: number | null;
  onClose: () => void;
  onSaved: (tx: Transaccion) => void;
}) {
  const [vehiculos, setVehiculos] = useState<VehiculoAdmin[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [vid, setVid] = useState<number | null>(vehiculoId);
  const [clienteId, setClienteId] = useState<number | 'nuevo'>('nuevo');
  const [nuevo, setNuevo] = useState({ nombre: '', telefono: '', email: '' });
  const [precio, setPrecio] = useState<number | null>(null);
  const [comision, setComision] = useState<number | null>(null);
  const [traspaso, setTraspaso] = useState<number | null>(null);
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10));
  const [forma, setForma] = useState('Financiado');
  const [notas, setNotas] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchInventario().then((all) => setVehiculos(all.filter((v) => v.estado !== 'vendido')));
    fetchClientes().then(setClientes).catch(() => setClientes([]));
  }, []);

  const vehiculo = vehiculos.find((v) => v.id === vid) ?? null;
  useEffect(() => {
    if (vehiculo && precio === null) setPrecio(vehiculo.precio_venta);
  }, [vehiculo, precio]);

  const ganancia = vehiculo?.precio_compra && precio
    ? precio - vehiculo.precio_compra - (comision ?? 0) - (traspaso ?? 0)
    : null;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!vehiculo || !precio) return;
    setSaving(true);
    try {
      let cid = clienteId;
      if (cid === 'nuevo') {
        const c = await createCliente({
          nombre: nuevo.nombre, telefono: nuevo.telefono || null, email: nuevo.email || null, tipo: 'comprador',
        });
        cid = c.id;
      }
      const tx = await createTransaccion({
        vehiculo_id: vehiculo.id, cliente_id: cid, tipo: 'venta', precio,
        comision: comision ?? 0, gastos_traspaso: traspaso ?? 0, fecha,
        notas: [`Forma de pago: ${forma}.`, notas].filter(Boolean).join(' '),
      });
      toast.success(`Venta registrada: ${tx.vehiculo_nombre}`);
      onSaved(tx);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'No se pudo registrar la venta'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-start justify-center overflow-y-auto p-4" onClick={onClose}>
      <form onSubmit={submit} className="card-elevated w-full max-w-2xl my-8" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-lg font-semibold text-white">Registrar venta</h2>
          <button type="button" onClick={onClose} className="btn-ghost p-2"><X className="w-5 h-5" /></button>
        </div>
        <div className="p-5 space-y-5">
          <div>
            <label className="block text-gray-400 text-xs mb-1">Vehículo *</label>
            <select required value={vid ?? ''} onChange={(e) => { setVid(Number(e.target.value)); setPrecio(null); }} className="select-field py-2">
              <option value="" disabled>Selecciona un vehículo del inventario</option>
              {vehiculos.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.marca} {v.modelo} {v.año} — {v.precio_venta ? formatCOP(v.precio_venta) : 'sin precio'} ({v.estado})
                </option>
              ))}
            </select>
            {vehiculo && (
              <p className="text-gray-500 text-xs mt-1">
                Costo de compra: {vehiculo.precio_compra ? formatCOP(vehiculo.precio_compra) : '-'} · {vehiculo.dias_en_inventario ?? '-'} días en inventario
              </p>
            )}
          </div>

          <div>
            <label className="block text-gray-400 text-xs mb-1">Cliente *</label>
            <select value={clienteId} onChange={(e) => setClienteId(e.target.value === 'nuevo' ? 'nuevo' : Number(e.target.value))} className="select-field py-2">
              <option value="nuevo">+ Cliente nuevo</option>
              {clientes.filter((c) => c.tipo !== 'vendedor').map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </select>
            {clienteId === 'nuevo' && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2">
                <input required placeholder="Nombre completo" value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} className="input-field py-2" />
                <input placeholder="Teléfono" value={nuevo.telefono} onChange={(e) => setNuevo({ ...nuevo, telefono: e.target.value })} className="input-field py-2" />
                <input type="email" placeholder="Email" value={nuevo.email} onChange={(e) => setNuevo({ ...nuevo, email: e.target.value })} className="input-field py-2" />
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Money label="Precio de venta *" value={precio} onChange={setPrecio} required />
            <Money label="Comisión" value={comision} onChange={setComision} />
            <Money label="Gastos de traspaso (si los asumes)" value={traspaso} onChange={setTraspaso} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-gray-400 text-xs mb-1">Fecha</label>
              <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} className="input-field py-2" />
            </div>
            <div>
              <label className="block text-gray-400 text-xs mb-1">Forma de pago</label>
              <select value={forma} onChange={(e) => setForma(e.target.value)} className="select-field py-2">
                <option>Financiado</option><option>Contado</option><option>Retoma + saldo</option>
              </select>
            </div>
          </div>
          <textarea rows={2} placeholder="Notas (cuota inicial, banco, condiciones de entrega...)" value={notas} onChange={(e) => setNotas(e.target.value)} className="input-field py-2" />

          {ganancia !== null && (
            <p className={`text-sm ${ganancia >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              Ganancia bruta estimada: {formatCOP(ganancia)}
              {vehiculo?.precio_compra ? ` (${(ganancia / vehiculo.precio_compra * 100).toFixed(1)}%)` : ''} — el sistema descuenta además el traspaso y taller de la compra.
            </p>
          )}
        </div>
        <div className="flex justify-end gap-3 p-5 border-t border-border">
          <button type="button" onClick={onClose} className="btn-ghost">Cancelar</button>
          <button type="submit" disabled={saving || !vehiculo} className="btn-primary flex items-center gap-2 disabled:opacity-50">
            {saving && <Loader2 className="w-4 h-4 animate-spin" />} Registrar venta
          </button>
        </div>
      </form>
    </div>
  );
}

function Money({ label, value, onChange, required }: {
  label: string; value: number | null; onChange: (v: number | null) => void; required?: boolean;
}) {
  return (
    <div>
      <label className="block text-gray-400 text-xs mb-1">{label}</label>
      <input
        required={required}
        inputMode="numeric"
        value={value !== null ? formatNumber(value) : ''}
        onChange={(e) => {
          const d = e.target.value.replace(/\D/g, '');
          onChange(d === '' ? null : Number(d));
        }}
        className="input-field py-2"
        placeholder="0"
      />
    </div>
  );
}
