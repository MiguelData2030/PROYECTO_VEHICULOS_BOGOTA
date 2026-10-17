'use client';

import { useState, type ReactNode } from 'react';
import { Check, Copy, Cpu, Loader2, Sparkles, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { formatNumber } from '@/lib/data';

/** Small UI pieces shared by every agent panel. */

export function F({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="w-full">
      <label className="block text-gray-400 text-xs mb-1">{label}</label>
      {children}
    </div>
  );
}

export function Num({ value, onChange, money }: { value: number | null; onChange: (v: number | null) => void; money?: boolean }) {
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

export function Box({ label, value, sub, accent = 'text-white' }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div className="card p-3">
      <p className="text-gray-500 text-xs">{label}</p>
      <p className={`text-lg font-bold break-words ${accent}`}>{value}</p>
      {sub && <p className="text-gray-500 text-xs mt-0.5">{sub}</p>}
    </div>
  );
}

async function copiar(texto: string, ok: () => void) {
  try {
    await navigator.clipboard.writeText(texto);
    ok();
  } catch {
    toast.error('No se pudo copiar');
  }
}

export function CopyBtn({ texto }: { texto: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button
      onClick={() => copiar(texto, () => { setOk(true); setTimeout(() => setOk(false), 1500); })}
      className="btn-ghost text-xs px-2 py-1 flex items-center gap-1"
    >
      {ok ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
    </button>
  );
}

export function Texto({ titulo, texto, extra }: { titulo: string; texto: string; extra?: ReactNode }) {
  const [copiado, setCopiado] = useState(false);
  return (
    <div className="card p-4 flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <p className="text-primary text-xs font-semibold uppercase tracking-wider">{titulo}</p>
        <div className="flex gap-1">
          {extra}
          <button
            onClick={() => copiar(texto, () => { setCopiado(true); setTimeout(() => setCopiado(false), 1500); })}
            className="btn-ghost text-xs flex items-center gap-1 px-2 py-1"
          >
            {copiado ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />} {copiado ? 'Copiado' : 'Copiar'}
          </button>
        </div>
      </div>
      <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{texto}</p>
    </div>
  );
}

/** The agent's written conclusion (Claude when active, its own rules otherwise). */
export function Diagnostico({ titulo, texto, ia, nota }: { titulo: string; texto: string; ia: boolean; nota?: string }) {
  return (
    <div className="card p-5">
      <p className="text-white font-semibold flex items-center gap-2 mb-2">
        {ia ? <Sparkles className="w-4 h-4 text-green-400" /> : <Cpu className="w-4 h-4 text-primary" />}
        {titulo}
      </p>
      <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{texto}</p>
      {nota && <p className="text-xs text-gray-600 mt-3">{nota}</p>}
    </div>
  );
}

export function Alertas({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <div className="space-y-1.5">
      {items.map((a) => (
        <p key={a} className="text-sm text-yellow-300 flex gap-2">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />{a}
        </p>
      ))}
    </div>
  );
}

export function Cargando() {
  return <div className="card p-10 flex justify-center"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>;
}

/** Before / after comparison of one metric: "sin agente" vs "con agente". */
export function Antes({ label, antes, despues, mejor }: { label: string; antes: string; despues: string; mejor: boolean }) {
  return (
    <div className="card p-3">
      <p className="text-gray-500 text-xs">{label}</p>
      <p className="text-gray-500 text-sm line-through">{antes}</p>
      <p className={`text-lg font-bold ${mejor ? 'text-green-400' : 'text-white'}`}>{despues}</p>
    </div>
  );
}
