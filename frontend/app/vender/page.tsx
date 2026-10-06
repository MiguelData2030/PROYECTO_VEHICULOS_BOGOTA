'use client';

import { useState, FormEvent } from 'react';
import {
  Car,
  DollarSign,
  FileCheck,
  CheckCircle,
  Send,
  ShieldCheck,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { marcas, transmisiones, combustibles } from '@/lib/data';

const currentYear = new Date().getFullYear();
const years = Array.from({ length: 30 }, (_, i) => currentYear - i);

const benefits = [
  {
    icon: ShieldCheck,
    title: 'Evaluación gratuita',
    description: 'Evaluamos tu vehículo sin ningún costo ni compromiso.',
  },
  {
    icon: DollarSign,
    title: 'Pago inmediato',
    description: 'Recibe tu dinero el mismo día de la transacción.',
  },
  {
    icon: FileCheck,
    title: 'Trámites incluidos',
    description: 'Nos encargamos de toda la documentación y traspaso.',
  },
  {
    icon: CheckCircle,
    title: 'Precio justo',
    description: 'Ofrecemos precios competitivos basados en el mercado actual.',
  },
];

export default function VenderPage() {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    marca: '',
    modelo: '',
    anio: '',
    kilometraje: '',
    transmision: '',
    combustible: '',
    color: '',
    ciudad: 'Bogotá',
    precio_esperado: '',
    nombre: '',
    telefono: '',
    email: '',
    descripcion: '',
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/clientes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre: form.nombre,
          telefono: form.telefono,
          email: form.email.trim() || null,
          tipo: 'vendedor',
          origen: 'web_vender',
          vehiculos_interes: [{
            marca: form.marca,
            modelo: form.modelo,
            anio: form.anio,
            kilometraje: form.kilometraje,
            precio_esperado: form.precio_esperado,
          }],
          notas: `Km: ${form.kilometraje} | Transmisión: ${form.transmision} | Combustible: ${form.combustible} | Color: ${form.color} | Ciudad: ${form.ciudad} | Precio esperado: ${form.precio_esperado} | Descripción: ${form.descripcion}`,
        }),
      });

      if (!res.ok) throw new Error('Error al enviar');

      toast.success('¡Solicitud enviada! Te contactaremos pronto para evaluar tu vehículo.');
      setForm({
        marca: '',
        modelo: '',
        anio: '',
        kilometraje: '',
        transmision: '',
        combustible: '',
        color: '',
        ciudad: 'Bogotá',
        precio_esperado: '',
        nombre: '',
        telefono: '',
        email: '',
        descripcion: '',
      });
    } catch {
      toast.error('Hubo un error. Intenta nuevamente o contáctanos por WhatsApp.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pt-16">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(212,168,67,0.08),transparent_50%)]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="max-w-3xl">
            <p className="text-primary font-medium uppercase tracking-widest text-sm mb-4">
              Vende con confianza
            </p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-display font-bold text-white leading-tight mb-6">
              Vende tu{' '}
              <span className="gold-gradient">Vehículo</span>
            </h1>
            <p className="text-gray-400 text-lg sm:text-xl leading-relaxed max-w-2xl">
              Obtén el mejor precio por tu vehículo. Evaluación gratuita, pago inmediato
              y nos encargamos de todos los trámites. Sin complicaciones.
            </p>
          </div>
        </div>
      </section>

      {/* Form */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <div className="card-elevated p-6 sm:p-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <Car className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-display font-bold text-white">
                Información del Vehículo
              </h2>
              <p className="text-gray-400 text-sm">
                Completa los datos y te contactaremos en menos de 24 horas
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-8">
            {/* Vehicle info */}
            <div>
              <h3 className="text-white font-semibold mb-4 text-lg">Datos del vehículo</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Marca *</label>
                  <select
                    name="marca"
                    value={form.marca}
                    onChange={handleChange}
                    required
                    className="select-field"
                  >
                    <option value="">Seleccionar marca</option>
                    {marcas.map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Modelo *</label>
                  <input
                    type="text"
                    name="modelo"
                    value={form.modelo}
                    onChange={handleChange}
                    required
                    placeholder="Ej: CX-5 Grand Touring"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Año *</label>
                  <select
                    name="anio"
                    value={form.anio}
                    onChange={handleChange}
                    required
                    className="select-field"
                  >
                    <option value="">Seleccionar año</option>
                    {years.map((y) => (
                      <option key={y} value={y}>{y}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Kilometraje *</label>
                  <input
                    type="number"
                    name="kilometraje"
                    value={form.kilometraje}
                    onChange={handleChange}
                    required
                    placeholder="Ej: 25000"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Transmisión *</label>
                  <select
                    name="transmision"
                    value={form.transmision}
                    onChange={handleChange}
                    required
                    className="select-field"
                  >
                    <option value="">Seleccionar</option>
                    {transmisiones.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Combustible *</label>
                  <select
                    name="combustible"
                    value={form.combustible}
                    onChange={handleChange}
                    required
                    className="select-field"
                  >
                    <option value="">Seleccionar</option>
                    {combustibles.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Color</label>
                  <input
                    type="text"
                    name="color"
                    value={form.color}
                    onChange={handleChange}
                    placeholder="Ej: Rojo Cristal"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Ciudad</label>
                  <input
                    type="text"
                    name="ciudad"
                    value={form.ciudad}
                    onChange={handleChange}
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Precio esperado (COP)</label>
                  <input
                    type="number"
                    name="precio_esperado"
                    value={form.precio_esperado}
                    onChange={handleChange}
                    placeholder="Ej: 85000000"
                    className="input-field"
                  />
                </div>
              </div>
            </div>

            {/* Owner info */}
            <div>
              <h3 className="text-white font-semibold mb-4 text-lg">Datos del propietario</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Nombre completo *</label>
                  <input
                    type="text"
                    name="nombre"
                    value={form.nombre}
                    onChange={handleChange}
                    required
                    placeholder="Tu nombre completo"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Teléfono *</label>
                  <input
                    type="tel"
                    name="telefono"
                    value={form.telefono}
                    onChange={handleChange}
                    required
                    placeholder="Ej: 3001234567"
                    className="input-field"
                  />
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Email</label>
                  <input
                    type="email"
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                    placeholder="tu@email.com"
                    className="input-field"
                  />
                </div>
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-gray-400 text-sm mb-1.5">
                Descripción adicional
              </label>
              <textarea
                name="descripcion"
                value={form.descripcion}
                onChange={handleChange}
                rows={4}
                placeholder="Cuéntanos más sobre el estado de tu vehículo, accesorios, historial de mantenimiento..."
                className="input-field resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex items-center gap-2 text-base disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Enviando...' : 'Enviar Solicitud'}
              <Send className="w-5 h-5" />
            </button>
          </form>
        </div>
      </section>

      {/* Benefits */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center mb-12">
            <h2 className="section-title">¿Por qué vender con nosotros?</h2>
            <p className="section-subtitle">
              Hacemos que vender tu vehículo sea fácil y seguro
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {benefits.map((b) => (
              <div
                key={b.title}
                className="card p-6 text-center hover:bg-surface-light group"
              >
                <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-4 group-hover:bg-primary/20 transition-colors">
                  <b.icon className="w-7 h-7 text-primary" />
                </div>
                <h3 className="text-white font-semibold text-lg mb-2">{b.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{b.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
