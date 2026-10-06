'use client';

import { useEffect, useMemo, useState } from 'react';
import { ExternalLink, Loader2, Target, MessageSquarePlus, Zap } from 'lucide-react';
import toast from 'react-hot-toast';
import AdminShell from '@/components/AdminShell';
import { formatCOP, formatNumber } from '@/lib/data';
import {
  fetchOportunidades, updateOportunidadEstado, triggerScraping, apiErrorMessage,
  ESTADOS_OPORTUNIDAD, type EstadoOportunidad, type Oportunidad,
} from '@/lib/api-admin';

const ESTADO_LABEL: Record<EstadoOportunidad, string> = {
  nueva: 'Nueva',
  contactada: 'Contactada',
  negociando: 'Negociando',
  comprada: 'Comprada',
  descartada: 'Descartada',
  expirada: 'Expirada',
};

/** Pipeline columns shown as filter chips; "activas" groups the open states. */
const FILTROS: { key: string; label: string; match: (e: EstadoOportunidad) => boolean }[] = [
  { key: 'activas', label: 'Activas', match: (e) => ['nueva', 'contactada', 'negociando'].includes(e) },
  ...ESTADOS_OPORTUNIDAD.map((e) => ({ key: e, label: ESTADO_LABEL[e], match: (x: EstadoOportunidad) => x === e })),
  { key: 'todas', label: 'Todas', match: () => true },
];

function scoreStyle(score: number) {
  if (score >= 75) return 'bg-green-500/10 text-green-400';
  if (score >= 60) return 'bg-yellow-500/10 text-yellow-400';
  return 'bg-gray-500/10 text-gray-400';
}

export default function OportunidadesPage() {
  const [items, setItems] = useState<Oportunidad[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState('activas');
  const [scoreMin, setScoreMin] = useState(60);
  const [scraping, setScraping] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setItems(await fetchOportunidades());
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudieron cargar las oportunidades'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    FILTROS.forEach((f) => { c[f.key] = items.filter((o) => f.match(o.estado)).length; });
    return c;
  }, [items]);

  const visibles = useMemo(() => {
    const f = FILTROS.find((x) => x.key === filtro)!;
    return items.filter((o) => f.match(o.estado) && (o.score ?? 0) >= scoreMin);
  }, [items, filtro, scoreMin]);

  const cambiarEstado = async (o: Oportunidad, estado: EstadoOportunidad, notas?: string) => {
    try {
      const updated = await updateOportunidadEstado(o.id, estado, notas);
      setItems((prev) => prev.map((p) => (p.id === o.id ? updated : p)));
      if (estado !== o.estado) toast.success(`${o.marca} ${o.modelo} → ${ESTADO_LABEL[estado]}`);
      else if (notas) toast.success('Nota agregada');
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo actualizar'));
    }
  };

  const handleScraping = async () => {
    setScraping(true);
    const ok = await triggerScraping();
    setScraping(false);
    if (ok) {
      toast.success('Escaneo completado');
      load();
    } else {
      toast.error('No se pudo ejecutar el scraping');
    }
  };

  return (
    <AdminShell
      title="Oportunidades de compra"
      subtitle="Anuncios detectados por el Agente Cazador, ordenados por score"
      actions={
        <button onClick={handleScraping} disabled={scraping} className="btn-secondary flex items-center gap-2 text-sm py-2">
          {scraping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
          {scraping ? 'Escaneando...' : 'Buscar ahora'}
        </button>
      }
    >
      <div className="flex flex-wrap items-center gap-2 mb-6">
        {FILTROS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFiltro(f.key)}
            className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
              filtro === f.key ? 'bg-primary text-dark font-medium' : 'bg-surface border border-border text-gray-400 hover:text-white'
            }`}
          >
            {f.label} <span className="opacity-70">({counts[f.key] ?? 0})</span>
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2 text-sm text-gray-400">
          Score mínimo
          <select value={scoreMin} onChange={(e) => setScoreMin(Number(e.target.value))} className="select-field py-1.5 w-24">
            {[0, 40, 50, 60, 70, 80].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
      </div>

      {loading ? (
        <div className="flex justify-center py-24"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>
      ) : visibles.length === 0 ? (
        <div className="card p-12 text-center text-gray-500">
          <Target className="w-10 h-10 mx-auto mb-3" />
          {items.length === 0
            ? 'Aún no hay oportunidades. Ejecuta el scraping para buscar vehículos.'
            : 'No hay oportunidades en este filtro.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {visibles.map((o) => <OportunidadCard key={o.id} o={o} onEstado={cambiarEstado} />)}
        </div>
      )}
    </AdminShell>
  );
}

function OportunidadCard({
  o,
  onEstado,
}: {
  o: Oportunidad;
  onEstado: (o: Oportunidad, estado: EstadoOportunidad, notas?: string) => Promise<void>;
}) {
  const [nota, setNota] = useState('');
  const [showNota, setShowNota] = useState(false);

  const descuento = o.descuento_porcentaje;
  const score = o.score ?? 0;

  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-white font-semibold">{o.marca} {o.modelo} {o.año}</p>
          <p className="text-gray-500 text-xs mt-0.5">
            {[
              o.kilometraje != null ? `${formatNumber(o.kilometraje)} km` : null,
              o.ubicacion,
              o.plataforma.charAt(0).toUpperCase() + o.plataforma.slice(1),
            ]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
        <span className={`px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${scoreStyle(score)}`}>
          {o.score != null ? `${score.toFixed(0)}/100` : 'Sin score'}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm">
        <div className="bg-dark rounded-lg p-2.5">
          <p className="text-gray-500 text-xs">Publicado</p>
          <p className="text-white font-medium">{formatCOP(o.precio_publicado)}</p>
        </div>
        <div className="bg-dark rounded-lg p-2.5">
          <p className="text-gray-500 text-xs">Mercado est.</p>
          <p className="text-gray-300">{o.precio_mercado_estimado ? formatCOP(o.precio_mercado_estimado) : '-'}</p>
        </div>
        <div className="bg-dark rounded-lg p-2.5">
          <p className="text-gray-500 text-xs">vs mercado</p>
          <p className={descuento == null ? 'text-gray-500' : descuento >= 15 ? 'text-green-400' : descuento > 0 ? 'text-yellow-400' : 'text-red-400'}>
            {descuento != null ? `${descuento > 0 ? '-' : '+'}${Math.abs(descuento).toFixed(1)}%` : '-'}
          </p>
        </div>
      </div>

      {o.descripcion_corta && (
        <p className="text-gray-400 text-xs leading-relaxed line-clamp-2">{o.descripcion_corta}</p>
      )}
      {o.notas && (
        <pre className="text-gray-500 text-xs whitespace-pre-wrap font-sans bg-dark rounded-lg p-2.5 max-h-24 overflow-y-auto">
          {o.notas.trim()}
        </pre>
      )}

      {showNota && (
        <div className="flex gap-2">
          <input
            value={nota}
            onChange={(e) => setNota(e.target.value)}
            placeholder="Ej: Llamé, pide 52M, negociable"
            className="input-field py-2 text-sm"
            autoFocus
          />
          <button
            onClick={async () => {
              if (!nota.trim()) return;
              await onEstado(o, o.estado, nota.trim());
              setNota('');
              setShowNota(false);
            }}
            className="btn-primary py-2 px-4 text-sm"
          >
            Guardar
          </button>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border mt-auto">
        <select
          value={o.estado}
          onChange={(e) => onEstado(o, e.target.value as EstadoOportunidad)}
          className="select-field py-1.5 text-sm w-36"
        >
          {ESTADOS_OPORTUNIDAD.map((e) => <option key={e} value={e}>{ESTADO_LABEL[e]}</option>)}
        </select>
        <button onClick={() => setShowNota((s) => !s)} className="btn-ghost p-2" title="Agregar nota">
          <MessageSquarePlus className="w-4 h-4" />
        </button>
        {o.url && (
          <a href={o.url} target="_blank" rel="noopener noreferrer" className="btn-ghost p-2 ml-auto flex items-center gap-1 text-sm">
            Ver anuncio <ExternalLink className="w-4 h-4" />
          </a>
        )}
      </div>
    </div>
  );
}
