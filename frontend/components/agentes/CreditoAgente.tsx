'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { Loader2, Landmark, PlayCircle, CheckCircle2, AlertTriangle, XCircle, Repeat } from 'lucide-react';
import toast from 'react-hot-toast';
import { formatCOP, formatCOPCompact } from '@/lib/data';
import { apiErrorMessage, fetchInventario, type VehiculoAdmin } from '@/lib/api-admin';
import {
  evaluarCredito, simularCreditos, type CreditoInput, type DecisionCredito, type SimulacionCredito,
} from '@/lib/api-agentes';
import { Antes, Box, Cargando, F, Num } from './ui';

const DECISION: Record<DecisionCredito['decision'], { label: string; cls: string; icon: typeof CheckCircle2 }> = {
  aprobable: { label: 'Aprobable', cls: 'text-green-400 border-green-500/40 bg-green-500/10', icon: CheckCircle2 },
  aprobable_con_ajuste: { label: 'Aprobable con ajuste', cls: 'text-primary border-primary/40 bg-primary/10', icon: Repeat },
  alternativa: { label: 'Mejor otro carro', cls: 'text-yellow-300 border-yellow-500/40 bg-yellow-500/10', icon: AlertTriangle },
  no_viable: { label: 'No viable hoy', cls: 'text-red-400 border-red-500/40 bg-red-500/10', icon: XCircle },
};

export default function CreditoAgente() {
  const [inv, setInv] = useState<VehiculoAdmin[]>([]);
  const [form, setForm] = useState<CreditoInput>({
    cliente: 'Andrés Rojas', empleo: 'empleado', ingreso_mensual: 6_000_000, cuotas_actuales: 400_000,
    puntaje_buro: 720, vehiculo_id: null, cuota_inicial: 20_000_000,
  });
  const [loading, setLoading] = useState(false);
  const [r, setR] = useState<DecisionCredito | null>(null);
  const set = <K extends keyof CreditoInput>(k: K, v: CreditoInput[K]) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    fetchInventario().then((all) => {
      const disponibles = all.filter((v) => v.estado === 'disponible' && v.precio_venta);
      setInv(disponibles);
      if (disponibles.length) setForm((f) => ({ ...f, vehiculo_id: f.vehiculo_id ?? disponibles[0].id }));
    });
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      setR(await evaluarCredito(form));
    } catch (err) {
      toast.error(apiErrorMessage(err, 'No se pudo precalificar'));
    } finally {
      setLoading(false);
    }
  };

  const carro = inv.find((v) => v.id === form.vehiculo_id);

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <form onSubmit={submit} className="card p-5 lg:col-span-2 space-y-3 h-fit">
          <p className="text-white font-semibold">Cliente que pide financiación</p>
          <div className="grid grid-cols-2 gap-3">
            <F label="Nombre"><input value={form.cliente} onChange={(e) => set('cliente', e.target.value)} className="input-field py-2" /></F>
            <F label="Tipo de ingreso">
              <select value={form.empleo} onChange={(e) => set('empleo', e.target.value as CreditoInput['empleo'])} className="select-field py-2">
                <option value="empleado">Empleado</option><option value="independiente">Independiente</option><option value="pensionado">Pensionado</option>
              </select>
            </F>
            <F label="Ingreso mensual"><Num money value={form.ingreso_mensual} onChange={(v) => set('ingreso_mensual', v ?? 0)} /></F>
            <F label="Cuotas que ya paga al mes"><Num money value={form.cuotas_actuales} onChange={(v) => set('cuotas_actuales', v ?? 0)} /></F>
          </div>
          <F label={`Puntaje en centrales de riesgo: ${form.puntaje_buro}`}>
            <input type="range" min={300} max={950} step={10} value={form.puntaje_buro} onChange={(e) => set('puntaje_buro', Number(e.target.value))} className="w-full accent-primary" />
          </F>
          <F label="Carro que quiere">
            <select value={form.vehiculo_id ?? ''} onChange={(e) => set('vehiculo_id', Number(e.target.value))} className="select-field py-2">
              {inv.map((v) => <option key={v.id} value={v.id}>{v.marca} {v.modelo} {v.año} — {formatCOP(v.precio_venta!)}</option>)}
            </select>
          </F>
          <F label={`Cuota inicial${carro?.precio_venta ? ` (${Math.round((form.cuota_inicial / carro.precio_venta) * 100)}% del precio)` : ''}`}>
            <Num money value={form.cuota_inicial} onChange={(v) => set('cuota_inicial', v ?? 0)} />
          </F>
          <button disabled={loading || !form.vehiculo_id} className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Landmark className="w-4 h-4" />} Precalificar
          </button>
          <p className="text-[11px] text-gray-500">Es una precalificación: la aprobación final la da el banco. Consultar centrales requiere autorización del cliente.</p>
        </form>

        <div className="lg:col-span-3 space-y-4">
          {loading && <Cargando />}
          {!loading && !r && (
            <div className="card p-10 text-center text-gray-500">
              <Landmark className="w-10 h-10 mx-auto mb-3" />
              Llena los datos del cliente. Si no le alcanza, el agente busca cómo sí: más plazo, más cuota inicial u otro carro.
            </div>
          )}
          {!loading && r && <Resultado r={r} />}
        </div>
      </div>

      <SimulacionLote />
    </div>
  );
}

function Resultado({ r }: { r: DecisionCredito }) {
  const d = DECISION[r.decision];
  const Icon = d.icon;
  return (
    <>
      <div className={`card p-5 border ${d.cls}`}>
        <p className="font-semibold flex items-center gap-2 text-lg"><Icon className="w-5 h-5" /> {d.label}</p>
        <p className="text-gray-200 mt-2">{r.propuesta}</p>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Box label="Capacidad de cuota" value={formatCOPCompact(r.capacidad_cuota)} sub="tope de endeudamiento" />
        <Box label="Tasa E.A." value={r.tasa_ea ? `${(r.tasa_ea * 100).toFixed(1)}%` : '-'} sub={`puntaje ${r.puntaje_buro}`} />
        <Box label="Cuota propuesta" value={r.cuota ? formatCOP(r.cuota) : '-'} sub={r.plazo ? `${r.plazo} meses` : undefined} accent="text-primary" />
        <Box label="Cuota inicial" value={r.cuota_inicial ? formatCOPCompact(r.cuota_inicial) : '-'} />
      </div>
      {r.tabla && r.tabla.length > 0 && (
        <div className="card p-5">
          <p className="text-white font-semibold mb-3">Cuota del carro que pidió, según el plazo</p>
          <div className="grid grid-cols-3 gap-3">
            {r.tabla.map((t) => {
              const cabe = t.cuota <= r.capacidad_cuota;
              return (
                <div key={t.plazo} className={`rounded-lg border p-3 text-center ${cabe ? 'border-green-500/40' : 'border-red-500/30'}`}>
                  <p className="text-gray-400 text-xs">{t.plazo} meses</p>
                  <p className={`font-bold ${cabe ? 'text-green-400' : 'text-red-400'}`}>{formatCOP(t.cuota)}</p>
                  <p className="text-[11px] text-gray-500">{cabe ? 'le alcanza' : 'no le alcanza'}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}

function SimulacionLote() {
  const [semilla, setSemilla] = useState(2026);
  const [loading, setLoading] = useState(false);
  const [r, setR] = useState<SimulacionCredito | null>(null);

  const run = async (s = semilla) => {
    setLoading(true);
    try {
      setR(await simularCreditos(s));
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo simular'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <p className="text-white font-semibold">Simular 25 solicitudes de crédito</p>
          <p className="text-gray-500 text-xs">Clientes ficticios pidiendo carros reales del inventario. Compara con revisar solo el plazo estándar de 60 meses.</p>
        </div>
        <div className="flex gap-2">
          {r && <button onClick={() => { setSemilla(semilla + 1); run(semilla + 1); }} disabled={loading} className="btn-ghost text-sm">Otro lote</button>}
          <button onClick={() => run()} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />} Simular
          </button>
        </div>
      </div>
      {loading && <Cargando />}
      {r && !loading && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <Antes label="Ventas viables" antes={`${r.linea_base.ventas_viables} sin agente`} despues={`${r.agente.ventas_viables} con agente`} mejor />
            <Antes label="Valor de esas ventas" antes={formatCOPCompact(r.linea_base.valor_cop)} despues={formatCOPCompact(r.agente.valor_cop)} mejor />
            <Box label="Ventas rescatadas" value={String(r.ventas_rescatadas)} sub="más plazo, más inicial u otro carro" accent="text-green-400" />
            <Box label="No viables" value={String(r.decisiones.no_viable ?? 0)} sub="plan de ahorro o contado" />
          </div>
          <div className="card p-5 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs uppercase border-b border-border">
                  <th className="text-left py-2">Cliente</th><th className="text-left">Carro pedido</th><th className="text-right">Puntaje</th>
                  <th className="text-left pl-4">Decisión</th><th className="text-left">Propuesta</th>
                </tr>
              </thead>
              <tbody>
                {r.detalle.map((x) => (
                  <tr key={x.id} className="border-b border-border/50 align-top">
                    <td className="py-2 text-white">{x.cliente}</td>
                    <td className="text-gray-400">{x.vehiculo}</td>
                    <td className="text-right text-gray-400">{x.puntaje_buro}</td>
                    <td className={`pl-4 whitespace-nowrap ${DECISION[x.decision].cls.split(' ')[0]}`}>{DECISION[x.decision].label}</td>
                    <td className="text-gray-300">{x.propuesta}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-xs text-gray-600 mt-3">{r.supuestos}</p>
          </div>
        </>
      )}
    </div>
  );
}
