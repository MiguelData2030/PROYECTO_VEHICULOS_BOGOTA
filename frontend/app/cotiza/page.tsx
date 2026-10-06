'use client';

import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import { Calculator, Loader2, CheckCircle2, ShieldCheck, Clock, Banknote, ThumbsUp, ThumbsDown, MessageCircle } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { formatCOP, formatNumber, marcas } from '@/lib/data';
import { whatsappUrl } from '@/lib/negocio';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Resultado {
  encontrado: boolean;
  mensaje?: string;
  rango_mercado?: [number, number];
  valor_mercado?: number;
  oferta_estimada?: [number, number];
  liquidez?: string;
  dias_estimados_venta?: number;
  factores_positivos?: string[];
  factores_negativos?: string[];
  comparables?: number;
  lead_guardado: boolean;
}

export default function CotizaPage() {
  const [form, setForm] = useState({
    marca: 'Mazda', modelo: '', año: String(new Date().getFullYear() - 4), kilometraje: '',
    transmision: 'automatica', combustible: 'gasolina', estado_mecanico: 'bueno',
    nombre: '', telefono: '', email: '', acepta_contacto: false,
  });
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState<Resultado | null>(null);
  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await axios.post<Resultado>(`${API_URL}/publico/cotizar`, {
        marca: form.marca, modelo: form.modelo, año: Number(form.año),
        kilometraje: Number(form.kilometraje.replace(/\D/g, '') || 0),
        transmision: form.transmision, combustible: form.combustible, estado_mecanico: form.estado_mecanico,
        nombre: form.nombre || null, telefono: form.telefono || null, email: form.email || null,
        acepta_contacto: form.acepta_contacto,
      }, { timeout: 60000 });
      setRes(data);
      setTimeout(() => document.getElementById('resultado')?.scrollIntoView({ behavior: 'smooth' }), 100);
    } catch (err) {
      const msg = axios.isAxiosError(err) && typeof err.response?.data?.detail === 'string'
        ? err.response.data.detail : 'No pudimos cotizar en este momento. Escríbenos por WhatsApp.';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const carro = `${form.marca} ${form.modelo} ${form.año}`.trim();

  return (
    <div className="pt-16">
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(212,168,67,0.1),transparent_55%)]" />
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
          <p className="text-primary font-medium uppercase tracking-widest text-sm mb-3">Cotizador gratuito</p>
          <h1 className="text-4xl sm:text-5xl font-display font-bold text-white mb-4">
            ¿Cuánto vale <span className="gold-gradient">tu carro</span>?
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl">
            Te damos un rango de precio en segundos, calculado con anuncios reales del mercado en Bogotá.
            Si te sirve, te hacemos una oferta formal y pagamos de contado.
          </p>
          <div className="flex flex-wrap gap-6 mt-6 text-sm text-gray-300">
            <span className="flex items-center gap-2"><Clock className="w-4 h-4 text-primary" /> Resultado al instante</span>
            <span className="flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-primary" /> Peritaje y traspaso por nuestra cuenta</span>
            <span className="flex items-center gap-2"><Banknote className="w-4 h-4 text-primary" /> Pago de contado</span>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pb-20 grid grid-cols-1 lg:grid-cols-5 gap-8">
        <form onSubmit={submit} className="card p-6 lg:col-span-3 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Campo label="Marca *">
              <select value={form.marca} onChange={(e) => set('marca', e.target.value)} className="select-field">
                {marcas.map((m) => <option key={m}>{m}</option>)}
              </select>
            </Campo>
            <Campo label="Modelo *"><input required value={form.modelo} onChange={(e) => set('modelo', e.target.value)} placeholder="Ej: CX-5, Duster, Onix" className="input-field" /></Campo>
            <Campo label="Año *"><input required type="number" min={1995} max={2030} value={form.año} onChange={(e) => set('año', e.target.value)} className="input-field" /></Campo>
            <Campo label="Kilometraje *">
              <input required inputMode="numeric" value={form.kilometraje} placeholder="Ej: 45.000"
                onChange={(e) => { const d = e.target.value.replace(/\D/g, ''); set('kilometraje', d ? formatNumber(Number(d)) : ''); }} className="input-field" />
            </Campo>
            <Campo label="Transmisión">
              <select value={form.transmision} onChange={(e) => set('transmision', e.target.value)} className="select-field">
                <option value="automatica">Automática</option><option value="mecanica">Mecánica</option><option value="cvt">CVT</option>
              </select>
            </Campo>
            <Campo label="Estado general">
              <select value={form.estado_mecanico} onChange={(e) => set('estado_mecanico', e.target.value)} className="select-field">
                <option value="excelente">Excelente</option><option value="bueno">Bueno</option><option value="regular">Regular (necesita taller)</option>
              </select>
            </Campo>
          </div>

          <div className="border-t border-border pt-4">
            <p className="text-white text-sm font-medium mb-1">¿Quieres que te hagamos una oferta formal? <span className="text-gray-500 font-normal">(opcional)</span></p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-2">
              <input value={form.nombre} onChange={(e) => set('nombre', e.target.value)} placeholder="Tu nombre" className="input-field" />
              <input value={form.telefono} onChange={(e) => set('telefono', e.target.value)} placeholder="Celular / WhatsApp" className="input-field" />
              <input type="email" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="Email" className="input-field" />
            </div>
            <label className="flex items-start gap-2 text-xs text-gray-400 mt-3 cursor-pointer">
              <input type="checkbox" checked={form.acepta_contacto} onChange={(e) => set('acepta_contacto', e.target.checked)} className="accent-primary mt-0.5" />
              Autorizo a AutoNegocio a tratar mis datos personales para contactarme con una oferta por mi vehículo (Ley 1581 de 2012).
            </label>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base disabled:opacity-50">
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Calculator className="w-5 h-5" />} Calcular el valor de mi carro
          </button>
        </form>

        <div id="resultado" className="lg:col-span-2">
          {!res ? (
            <div className="card p-6 h-full flex flex-col justify-center text-center text-gray-400">
              <Calculator className="w-12 h-12 text-primary mx-auto mb-4" />
              <p>Completa los datos y te mostramos cuánto vale tu carro en el mercado y cuánto te podríamos pagar.</p>
            </div>
          ) : !res.encontrado ? (
            <div className="card p-6 space-y-4">
              <p className="text-white font-semibold">Necesitamos verlo de cerca</p>
              <p className="text-gray-400 text-sm">{res.mensaje}</p>
              {res.lead_guardado && <p className="text-green-400 text-sm flex items-center gap-2"><CheckCircle2 className="w-4 h-4" /> Recibimos tus datos: te contactamos hoy.</p>}
              <a href={whatsappUrl(`Hola, quiero cotizar mi ${carro}`)} target="_blank" rel="noopener noreferrer" className="btn-primary flex items-center justify-center gap-2"><MessageCircle className="w-4 h-4" /> Cotizar por WhatsApp</a>
            </div>
          ) : (
            <div className="card-elevated p-6 space-y-5 border border-primary/30">
              <div>
                <p className="text-gray-400 text-sm">Valor de mercado de tu {carro}</p>
                <p className="text-3xl font-bold text-white mt-1">{formatCOP(res.rango_mercado![0])} – {formatCOP(res.rango_mercado![1])}</p>
                <p className="text-gray-500 text-xs mt-1">Basado en {res.comparables ? `${res.comparables} anuncios reales similares` : 'el comportamiento del mercado'} en Bogotá.</p>
              </div>
              <div className="bg-primary/10 border border-primary/30 rounded-xl p-4">
                <p className="text-primary text-xs uppercase tracking-wider font-semibold">Te lo compramos hoy por</p>
                <p className="text-2xl font-bold text-white mt-1">{formatCOP(res.oferta_estimada![0])} – {formatCOP(res.oferta_estimada![1])}</p>
                <p className="text-gray-400 text-xs mt-1">De contado, sin trámites para ti. Valor final sujeto a peritaje.</p>
              </div>
              {(res.factores_positivos?.length || res.factores_negativos?.length) ? (
                <div className="grid grid-cols-1 gap-2 text-sm">
                  {res.factores_positivos?.map((f) => <p key={f} className="text-gray-300 flex gap-2"><ThumbsUp className="w-4 h-4 text-green-400 flex-shrink-0" />{f}</p>)}
                  {res.factores_negativos?.map((f) => <p key={f} className="text-gray-300 flex gap-2"><ThumbsDown className="w-4 h-4 text-red-400 flex-shrink-0" />{f}</p>)}
                </div>
              ) : null}
              {res.lead_guardado
                ? <p className="text-green-400 text-sm flex items-center gap-2"><CheckCircle2 className="w-4 h-4" /> Listo: un asesor te contacta hoy con la oferta formal.</p>
                : <a href={whatsappUrl(`Hola, coticé mi ${carro} en la web (${formatCOP(res.rango_mercado![0])} – ${formatCOP(res.rango_mercado![1])}). Quiero una oferta.`)} target="_blank" rel="noopener noreferrer" className="btn-primary flex items-center justify-center gap-2"><MessageCircle className="w-4 h-4" /> Quiero la oferta por WhatsApp</a>}
              <p className="text-gray-600 text-xs">También puedes <Link href="/vender/" className="text-primary hover:underline">dejarnos todos los detalles aquí</Link>.</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function Campo({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-gray-400 text-sm mb-1.5">{label}</label>
      {children}
    </div>
  );
}
