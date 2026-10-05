'use client';

import { useEffect, useState } from 'react';
import { Loader2, Mail, Phone, Trash2, Users } from 'lucide-react';
import toast from 'react-hot-toast';
import AdminShell from '@/components/AdminShell';
import { fetchClientes, deleteCliente, apiErrorMessage, type Cliente } from '@/lib/api-admin';

const TIPOS = [
  { key: '', label: 'Todos' },
  { key: 'vendedor', label: 'Quieren vender' },
  { key: 'comprador', label: 'Quieren comprar' },
  { key: 'ambos', label: 'Ambos' },
];

function formatFecha(iso: string | null) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function LeadsPage() {
  const [tipo, setTipo] = useState('');
  const [items, setItems] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchClientes(tipo || undefined)
      .then(setItems)
      .catch((e) => toast.error(apiErrorMessage(e, 'No se pudieron cargar los leads')))
      .finally(() => setLoading(false));
  }, [tipo]);

  const handleDelete = async (c: Cliente) => {
    if (!confirm(`¿Eliminar a ${c.nombre}?`)) return;
    try {
      await deleteCliente(c.id);
      setItems((prev) => prev.filter((p) => p.id !== c.id));
      toast.success('Lead eliminado');
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo eliminar'));
    }
  };

  return (
    <AdminShell title="Leads y clientes" subtitle="Solicitudes recibidas desde el formulario «Vender» y clientes registrados">
      <div className="flex flex-wrap gap-2 mb-6">
        {TIPOS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTipo(t.key)}
            className={`px-3 py-1.5 rounded-full text-sm transition-colors ${
              tipo === t.key ? 'bg-primary text-dark font-medium' : 'bg-surface border border-border text-gray-400 hover:text-white'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-24"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>
      ) : items.length === 0 ? (
        <div className="card p-12 text-center text-gray-500">
          <Users className="w-10 h-10 mx-auto mb-3" />
          Aún no hay leads en esta categoría.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((c) => {
            const tel = c.telefono?.replace(/\D/g, '');
            const vehiculos = (c.vehiculos_interes ?? []) as Record<string, string | number>[];
            return (
              <div key={c.id} className="card p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-white font-semibold">
                      {c.nombre}
                      <span className="ml-2 badge-primary text-[11px] capitalize">{c.tipo}</span>
                    </p>
                    <p className="text-gray-500 text-xs mt-0.5">{formatFecha(c.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    {tel && (
                      <a
                        href={`https://wa.me/${tel.length === 10 ? '57' + tel : tel}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-ghost p-2 flex items-center gap-1.5 text-sm"
                      >
                        <Phone className="w-4 h-4" /> {c.telefono}
                      </a>
                    )}
                    {c.email && (
                      <a href={`mailto:${c.email}`} className="btn-ghost p-2" title={c.email}>
                        <Mail className="w-4 h-4" />
                      </a>
                    )}
                    <button onClick={() => handleDelete(c)} className="btn-ghost p-2 hover:text-red-400" title="Eliminar">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {vehiculos.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-3">
                    {vehiculos.map((v, i) => (
                      <span key={i} className="bg-dark rounded-lg px-3 py-1.5 text-sm text-gray-300">
                        {[v.marca, v.modelo, v.anio].filter(Boolean).join(' ')}
                        {v.kilometraje ? ` · ${v.kilometraje} km` : ''}
                        {v.precio_esperado ? ` · pide ${v.precio_esperado}` : ''}
                      </span>
                    ))}
                  </div>
                )}
                {c.notas && (
                  <pre className="text-gray-500 text-xs whitespace-pre-wrap font-sans mt-3">{c.notas.trim()}</pre>
                )}
              </div>
            );
          })}
        </div>
      )}
    </AdminShell>
  );
}
