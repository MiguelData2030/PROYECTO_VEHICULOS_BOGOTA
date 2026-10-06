'use client';

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import Link from 'next/link';
import {
  Plus, Pencil, Trash2, Loader2, X, Upload, ImageOff, Search, ExternalLink, Car, HandCoins, Megaphone,
} from 'lucide-react';
import toast from 'react-hot-toast';
import AdminShell from '@/components/AdminShell';
import { formatCOP, formatNumber } from '@/lib/data';
import {
  fetchInventario, createVehiculo, updateVehiculo, deleteVehiculo, uploadFotos, deleteFoto,
  apiErrorMessage, fotoUrl,
  ESTADOS_VEHICULO, TRANSMISIONES, COMBUSTIBLES, TIPOS_VEHICULO,
  type VehiculoAdmin, type VehiculoInput,
} from '@/lib/api-admin';

const ESTADO_LABEL: Record<string, string> = {
  disponible: 'Disponible',
  reservado: 'Reservado',
  en_proceso: 'En proceso',
  vendido: 'Vendido',
};

const ESTADO_STYLE: Record<string, string> = {
  disponible: 'bg-green-500/10 text-green-400',
  reservado: 'bg-yellow-500/10 text-yellow-400',
  en_proceso: 'bg-blue-500/10 text-blue-400',
  vendido: 'bg-red-500/10 text-red-400',
};

const EMPTY: VehiculoInput = {
  marca: '',
  modelo: '',
  año: new Date().getFullYear() - 3,
  tipo_vehiculo: 'SUV',
  placa: null,
  color: '',
  kilometraje: 0,
  transmision: 'automatica',
  combustible: 'gasolina',
  cilindraje: null,
  num_dueños: null,
  ciudad: 'Bogotá',
  precio_compra: null,
  precio_venta: null,
  precio_mercado: null,
  estado: 'disponible',
  estado_mecanico: 'bueno',
  soat_vigente: true,
  tecnicomecanica_vigente: true,
  impuestos_al_dia: true,
  libre_prendas: true,
  descripcion: null,
  fuente: 'particular',
  fecha_compra: null,
};

function toInput(v: VehiculoAdmin): VehiculoInput {
  const out = { ...EMPTY };
  (Object.keys(EMPTY) as (keyof VehiculoInput)[]).forEach((k) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (out as any)[k] = v[k] ?? EMPTY[k];
  });
  return out;
}

export default function InventarioPage() {
  const [items, setItems] = useState<VehiculoAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [estado, setEstado] = useState<string>('');
  const [editing, setEditing] = useState<VehiculoAdmin | 'new' | null>(null);

  const load = async () => {
    setLoading(true);
    setItems(await fetchInventario());
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((v) => {
      if (estado && v.estado !== estado) return false;
      if (!q) return true;
      return `${v.marca} ${v.modelo} ${v.año} ${v.placa ?? ''}`.toLowerCase().includes(q);
    });
  }, [items, query, estado]);

  const upsertLocal = (v: VehiculoAdmin) => {
    setItems((prev) => {
      const idx = prev.findIndex((p) => p.id === v.id);
      if (idx === -1) return [v, ...prev];
      const copy = [...prev];
      copy[idx] = v;
      return copy;
    });
  };

  const handleEstado = async (v: VehiculoAdmin, nuevo: string) => {
    try {
      const payload: Partial<VehiculoInput> & { fecha_venta?: string | null } = { estado: nuevo };
      if (nuevo === 'vendido' && !v.fecha_venta) payload.fecha_venta = new Date().toISOString();
      upsertLocal(await updateVehiculo(v.id, payload));
      toast.success(`${v.marca} ${v.modelo}: ${ESTADO_LABEL[nuevo]}`);
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo cambiar el estado'));
    }
  };

  const handleDelete = async (v: VehiculoAdmin) => {
    if (!confirm(`¿Eliminar ${v.marca} ${v.modelo} ${v.año}? Esta acción no se puede deshacer.`)) return;
    try {
      await deleteVehiculo(v.id);
      setItems((prev) => prev.filter((p) => p.id !== v.id));
      toast.success('Vehículo eliminado');
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo eliminar'));
    }
  };

  return (
    <AdminShell
      title="Inventario"
      subtitle={`${items.length} vehículos registrados`}
      actions={
        <button onClick={() => setEditing('new')} className="btn-primary flex items-center gap-2 text-sm py-2">
          <Plus className="w-4 h-4" /> Nuevo vehículo
        </button>
      }
    >
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-gray-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por marca, modelo, año o placa"
            className="input-field pl-10 py-2.5"
          />
        </div>
        <select value={estado} onChange={(e) => setEstado(e.target.value)} className="select-field sm:w-48 py-2.5">
          <option value="">Todos los estados</option>
          {ESTADOS_VEHICULO.map((e) => <option key={e} value={e}>{ESTADO_LABEL[e]}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="flex justify-center py-24"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center text-gray-500">
          <Car className="w-10 h-10 mx-auto mb-3" />
          {items.length === 0 ? 'Aún no hay vehículos. Crea el primero.' : 'Ningún vehículo coincide con el filtro.'}
        </div>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-gray-500 text-xs uppercase">
                <th className="text-left py-3 px-4">Vehículo</th>
                <th className="text-right py-3 px-3">Compra</th>
                <th className="text-right py-3 px-3">Venta</th>
                <th className="text-right py-3 px-3">Margen</th>
                <th className="text-center py-3 px-3">Días</th>
                <th className="text-center py-3 px-3">Estado</th>
                <th className="text-right py-3 px-4">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((v) => {
                const margenPct = v.precio_compra && v.precio_venta
                  ? (v.precio_venta - v.precio_compra) / v.precio_compra * 100
                  : null;
                const foto = v.fotos?.[0];
                return (
                  <tr key={v.id} className="border-b border-border/50 hover:bg-surface-light transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-14 h-10 rounded-md bg-dark overflow-hidden flex-shrink-0 flex items-center justify-center">
                          {foto
                            ? <img src={fotoUrl(foto)} alt="" className="w-full h-full object-cover" />
                            : <ImageOff className="w-4 h-4 text-gray-600" />}
                        </div>
                        <div>
                          <p className="text-white font-medium">{v.marca} {v.modelo} {v.año}</p>
                          <p className="text-gray-500 text-xs">
                            {formatNumber(v.kilometraje)} km · {v.tipo_vehiculo}{v.placa ? ` · ${v.placa}` : ''}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="text-right py-3 px-3 text-gray-400">{v.precio_compra ? formatCOP(v.precio_compra) : '-'}</td>
                    <td className="text-right py-3 px-3 text-white font-medium">{v.precio_venta ? formatCOP(v.precio_venta) : '-'}</td>
                    <td className="text-right py-3 px-3">
                      {margenPct !== null ? (
                        <span className={margenPct >= 15 ? 'text-green-400' : margenPct >= 10 ? 'text-yellow-400' : 'text-red-400'}>
                          {margenPct.toFixed(1)}%
                        </span>
                      ) : '-'}
                    </td>
                    <td className={`text-center py-3 px-3 ${(v.dias_en_inventario ?? 0) > 30 ? 'text-red-400' : 'text-gray-400'}`}>
                      {v.dias_en_inventario ?? '-'}
                    </td>
                    <td className="text-center py-3 px-3">
                      <select
                        value={v.estado}
                        onChange={(e) => handleEstado(v, e.target.value)}
                        className={`rounded-full px-2 py-1 text-xs font-medium border-0 cursor-pointer focus:outline-none ${ESTADO_STYLE[v.estado] ?? ''}`}
                      >
                        {ESTADOS_VEHICULO.map((e) => <option key={e} value={e} className="bg-dark text-white">{ESTADO_LABEL[e]}</option>)}
                      </select>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex justify-end gap-1">
                        {v.estado !== 'vendido' && (
                          <Link href={`/catalogo/vehiculo?id=${v.id}`} target="_blank" className="btn-ghost p-2" title="Ver en catálogo">
                            <ExternalLink className="w-4 h-4" />
                          </Link>
                        )}
                        {v.estado !== 'vendido' && (
                          <Link href={`/admin/ventas?vehiculo=${v.id}`} className="btn-ghost p-2 hover:text-green-400" title="Registrar venta">
                            <HandCoins className="w-4 h-4" />
                          </Link>
                        )}
                        {v.estado !== 'vendido' && (
                          <Link href={`/admin/agentes?agente=marketing&vehiculo=${v.id}`} className="btn-ghost p-2 hover:text-primary" title="Generar anuncio (Agente de Marketing)">
                            <Megaphone className="w-4 h-4" />
                          </Link>
                        )}
                        <button onClick={() => setEditing(v)} className="btn-ghost p-2" title="Editar">
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(v)} className="btn-ghost p-2 hover:text-red-400" title="Eliminar">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <VehiculoModal
          vehiculo={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={(v) => { upsertLocal(v); setEditing(v); }}
        />
      )}
    </AdminShell>
  );
}

// ---------------------------------------------------------------------------
// Create / edit modal
// ---------------------------------------------------------------------------

function VehiculoModal({
  vehiculo,
  onClose,
  onSaved,
}: {
  vehiculo: VehiculoAdmin | null;
  onClose: () => void;
  onSaved: (v: VehiculoAdmin) => void;
}) {
  const [form, setForm] = useState<VehiculoInput>(vehiculo ? toInput(vehiculo) : EMPTY);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const isNew = !vehiculo;

  useEffect(() => {
    if (vehiculo) setForm(toInput(vehiculo));
  }, [vehiculo]);

  const set = <K extends keyof VehiculoInput>(k: K, v: VehiculoInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const num = (s: string): number | null => (s.trim() === '' ? null : Number(s.replace(/\D/g, '')));

  const margen = form.precio_compra && form.precio_venta
    ? (form.precio_venta - form.precio_compra) / form.precio_compra * 100
    : null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload: VehiculoInput = {
        ...form,
        placa: form.placa?.trim().toUpperCase() || null,
        descripcion: form.descripcion?.trim() || null,
        margen_estimado: margen !== null ? Number(margen.toFixed(2)) : null,
      } as VehiculoInput;
      const saved = isNew ? await createVehiculo(payload) : await updateVehiculo(vehiculo.id, payload);
      toast.success(isNew ? 'Vehículo creado. Ya puedes subir fotos.' : 'Cambios guardados');
      onSaved(saved);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'No se pudo guardar'));
    } finally {
      setSaving(false);
    }
  };

  const handleUpload = async (files: FileList | null) => {
    if (!vehiculo || !files || files.length === 0) return;
    setUploading(true);
    try {
      onSaved(await uploadFotos(vehiculo.id, Array.from(files)));
      toast.success('Fotos subidas');
    } catch (err) {
      toast.error(apiErrorMessage(err, 'No se pudieron subir las fotos'));
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteFoto = async (url: string) => {
    if (!vehiculo) return;
    try {
      onSaved(await deleteFoto(vehiculo.id, url));
    } catch (err) {
      toast.error(apiErrorMessage(err, 'No se pudo eliminar la foto'));
    }
  };

  const handleMakeCover = async (url: string) => {
    if (!vehiculo?.fotos) return;
    const fotos = [url, ...vehiculo.fotos.filter((f) => f !== url)];
    try {
      onSaved(await updateVehiculo(vehiculo.id, { fotos } as Partial<VehiculoInput>));
    } catch (err) {
      toast.error(apiErrorMessage(err, 'No se pudo cambiar la portada'));
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-black/70 flex items-start justify-center overflow-y-auto p-4" onClick={onClose}>
      <div className="card-elevated w-full max-w-3xl my-8" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-lg font-semibold text-white">
            {isNew ? 'Nuevo vehículo' : `${vehiculo.marca} ${vehiculo.modelo} ${vehiculo.año}`}
          </h2>
          <button onClick={onClose} className="btn-ghost p-2"><X className="w-5 h-5" /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-6">
          <Section title="Vehículo">
            <Field label="Marca *"><input required value={form.marca} onChange={(e) => set('marca', e.target.value)} className="input-field py-2" placeholder="Toyota" /></Field>
            <Field label="Modelo *"><input required value={form.modelo} onChange={(e) => set('modelo', e.target.value)} className="input-field py-2" placeholder="Corolla Cross" /></Field>
            <Field label="Año *"><input required type="number" min={1990} max={2030} value={form.año} onChange={(e) => set('año', Number(e.target.value))} className="input-field py-2" /></Field>
            <Field label="Tipo *">
              <select value={form.tipo_vehiculo} onChange={(e) => set('tipo_vehiculo', e.target.value)} className="select-field py-2">
                {TIPOS_VEHICULO.map((t) => <option key={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Kilometraje *"><input required inputMode="numeric" value={form.kilometraje} onChange={(e) => set('kilometraje', num(e.target.value) ?? 0)} className="input-field py-2" /></Field>
            <Field label="Color *"><input required value={form.color} onChange={(e) => set('color', e.target.value)} className="input-field py-2" placeholder="Blanco" /></Field>
            <Field label="Transmisión">
              <select value={form.transmision} onChange={(e) => set('transmision', e.target.value)} className="select-field py-2 capitalize">
                {TRANSMISIONES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Combustible">
              <select value={form.combustible} onChange={(e) => set('combustible', e.target.value)} className="select-field py-2 capitalize">
                {COMBUSTIBLES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Cilindraje (cc)"><input inputMode="numeric" value={form.cilindraje ?? ''} onChange={(e) => set('cilindraje', num(e.target.value))} className="input-field py-2" /></Field>
            <Field label="Placa"><input value={form.placa ?? ''} onChange={(e) => set('placa', e.target.value)} className="input-field py-2 uppercase" placeholder="ABC123" /></Field>
            <Field label="N° dueños"><input type="number" min={1} value={form.num_dueños ?? ''} onChange={(e) => set('num_dueños', num(e.target.value))} className="input-field py-2" /></Field>
            <Field label="Ciudad"><input value={form.ciudad} onChange={(e) => set('ciudad', e.target.value)} className="input-field py-2" /></Field>
          </Section>

          <Section title="Precios (COP)">
            <Field label="Precio de compra"><MoneyInput value={form.precio_compra} onChange={(v) => set('precio_compra', v)} /></Field>
            <Field label="Precio de venta"><MoneyInput value={form.precio_venta} onChange={(v) => set('precio_venta', v)} /></Field>
            <Field label="Precio de mercado"><MoneyInput value={form.precio_mercado} onChange={(v) => set('precio_mercado', v)} /></Field>
            <div className="sm:col-span-3 text-sm">
              {margen !== null ? (
                <span className={margen >= 15 ? 'text-green-400' : margen >= 10 ? 'text-yellow-400' : 'text-red-400'}>
                  Margen bruto: {formatCOP((form.precio_venta ?? 0) - (form.precio_compra ?? 0))} ({margen.toFixed(1)}%)
                  {margen < 10 && ' — por debajo del mínimo del 10%'}
                </span>
              ) : <span className="text-gray-500">Ingresa compra y venta para ver el margen.</span>}
            </div>
          </Section>

          <Section title="Estado y documentos">
            <Field label="Estado">
              <select value={form.estado} onChange={(e) => set('estado', e.target.value)} className="select-field py-2">
                {ESTADOS_VEHICULO.map((e) => <option key={e} value={e}>{ESTADO_LABEL[e]}</option>)}
              </select>
            </Field>
            <Field label="Estado mecánico">
              <select value={form.estado_mecanico ?? ''} onChange={(e) => set('estado_mecanico', e.target.value || null)} className="select-field py-2">
                <option value="excelente">Excelente</option>
                <option value="bueno">Bueno</option>
                <option value="regular">Regular</option>
              </select>
            </Field>
            <Field label="Fuente">
              <select value={form.fuente ?? ''} onChange={(e) => set('fuente', e.target.value || null)} className="select-field py-2">
                <option value="particular">Particular</option>
                <option value="retoma">Retoma</option>
                <option value="subasta">Subasta</option>
                <option value="tucarro">TuCarro</option>
                <option value="carroya">Carroya</option>
                <option value="flota">Flota corporativa</option>
              </select>
            </Field>
            <Field label="Fecha de compra">
              <input
                type="date"
                value={form.fecha_compra ? form.fecha_compra.slice(0, 10) : ''}
                onChange={(e) => set('fecha_compra', e.target.value ? `${e.target.value}T12:00:00` : null)}
                className="input-field py-2"
              />
            </Field>
            <div className="sm:col-span-2 grid grid-cols-2 gap-2 text-sm">
              {([
                ['soat_vigente', 'SOAT vigente'],
                ['tecnicomecanica_vigente', 'Tecnomecánica vigente'],
                ['impuestos_al_dia', 'Impuestos al día'],
                ['libre_prendas', 'Libre de prendas'],
              ] as const).map(([k, label]) => (
                <label key={k} className="flex items-center gap-2 text-gray-300 cursor-pointer">
                  <input type="checkbox" checked={form[k]} onChange={(e) => set(k, e.target.checked)} className="accent-primary w-4 h-4" />
                  {label}
                </label>
              ))}
            </div>
          </Section>

          <div>
            <label className="block text-gray-400 text-sm mb-1.5">Descripción pública</label>
            <textarea
              rows={3}
              value={form.descripcion ?? ''}
              onChange={(e) => set('descripcion', e.target.value)}
              className="input-field py-2"
              placeholder="Único dueño, mantenimientos en concesionario..."
            />
          </div>

          {!isNew && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-white font-medium text-sm">Fotos ({vehiculo.fotos?.length ?? 0}/10)</h3>
                <label className={`btn-secondary text-sm py-1.5 px-3 flex items-center gap-2 cursor-pointer ${uploading ? 'opacity-50 pointer-events-none' : ''}`}>
                  {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
                  Subir fotos
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    multiple
                    className="hidden"
                    onChange={(e) => { handleUpload(e.target.files); e.target.value = ''; }}
                  />
                </label>
              </div>
              {vehiculo.fotos && vehiculo.fotos.length > 0 ? (
                <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
                  {vehiculo.fotos.map((f, i) => (
                    <div key={f} className="relative group aspect-[4/3] rounded-lg overflow-hidden bg-dark">
                      <img src={fotoUrl(f)} alt="" className="w-full h-full object-cover" />
                      {i === 0 && <span className="absolute top-1 left-1 badge-primary text-[10px]">Portada</span>}
                      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1">
                        {i !== 0 && (
                          <button type="button" onClick={() => handleMakeCover(f)} className="text-xs text-white bg-primary/80 rounded px-2 py-1">Portada</button>
                        )}
                        <button type="button" onClick={() => handleDeleteFoto(f)} className="p-1.5 rounded bg-red-500/80 text-white" title="Eliminar foto">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">Sin fotos. La primera foto será la portada en el catálogo.</p>
              )}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2 border-t border-border">
            <button type="button" onClick={onClose} className="btn-ghost">Cerrar</button>
            <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2 disabled:opacity-50">
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {isNew ? 'Crear vehículo' : 'Guardar cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <fieldset>
      <legend className="text-primary text-xs font-semibold uppercase tracking-wider mb-3">{title}</legend>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">{children}</div>
    </fieldset>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-gray-400 text-xs mb-1">{label}</label>
      {children}
    </div>
  );
}

function MoneyInput({ value, onChange }: { value: number | null; onChange: (v: number | null) => void }) {
  return (
    <input
      inputMode="numeric"
      value={value !== null ? formatNumber(value) : ''}
      onChange={(e) => {
        const digits = e.target.value.replace(/\D/g, '');
        onChange(digits === '' ? null : Number(digits));
      }}
      className="input-field py-2"
      placeholder="0"
    />
  );
}
