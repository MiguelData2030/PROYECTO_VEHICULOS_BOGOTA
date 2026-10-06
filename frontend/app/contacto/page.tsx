'use client';

import { useState, FormEvent } from 'react';
import {
  Phone,
  Mail,
  MapPin,
  Clock,
  MessageCircle,
  Send,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { NEGOCIO, whatsappUrl, mapsUrl } from '@/lib/negocio';

const contactInfo = [
  {
    icon: MessageCircle,
    title: 'WhatsApp',
    value: NEGOCIO.whatsappDisplay,
    href: whatsappUrl(),
  },
  {
    icon: Mail,
    title: 'Email',
    value: NEGOCIO.email,
    href: `mailto:${NEGOCIO.email}`,
  },
  {
    icon: MapPin,
    title: 'Dirección',
    value: NEGOCIO.direccion,
    href: mapsUrl(),
  },
  {
    icon: Clock,
    title: 'Horario',
    value: NEGOCIO.horario,
    href: null,
  },
].filter((c) => c.value);

const asuntos = [
  'Comprar vehículo',
  'Vender vehículo',
  'Financiación',
  'Otro',
];

export default function ContactoPage() {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    nombre: '',
    email: '',
    telefono: '',
    asunto: '',
    mensaje: '',
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
          telefono: form.telefono || null,
          email: form.email.trim() || null,
          tipo: form.asunto === 'Vender vehículo' ? 'vendedor' : 'comprador',
          origen: 'web_contacto',
          notas: `[Contacto web] ${form.asunto || 'Sin asunto'}: ${form.mensaje}`,
        }),
      });
      if (!res.ok) throw new Error('Error al enviar');
      toast.success('Mensaje enviado. Te contactaremos pronto.');
      setForm({ nombre: '', email: '', telefono: '', asunto: '', mensaje: '' });
    } catch {
      toast.error('No pudimos enviar tu mensaje. Escríbenos por WhatsApp.');
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
              Estamos para ayudarte
            </p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-display font-bold text-white leading-tight mb-6">
              <span className="gold-gradient">Contáctanos</span>
            </h1>
            <p className="text-gray-400 text-lg sm:text-xl leading-relaxed max-w-2xl">
              ¿Tienes preguntas sobre nuestros vehículos, financiación o quieres vender tu carro?
              Escríbenos y te responderemos lo antes posible.
            </p>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        {/* Contact Info Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {contactInfo.map((info) => {
            const content = (
              <div className="card p-6 text-center hover:bg-surface-light group h-full">
                <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-4 group-hover:bg-primary/20 transition-colors">
                  <info.icon className="w-7 h-7 text-primary" />
                </div>
                <h3 className="text-white font-semibold text-lg mb-1">{info.title}</h3>
                <p className="text-gray-400 text-sm">{info.value}</p>
              </div>
            );

            return info.href ? (
              <a
                key={info.title}
                href={info.href}
                target="_blank"
                rel="noopener noreferrer"
              >
                {content}
              </a>
            ) : (
              <div key={info.title}>{content}</div>
            );
          })}
        </div>

        {/* Contact Form */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-10">
          <div className="lg:col-span-3">
            <div className="card-elevated p-6 sm:p-10">
              <div className="flex items-center gap-3 mb-8">
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Send className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <h2 className="text-xl font-display font-bold text-white">
                    Envíanos un mensaje
                  </h2>
                  <p className="text-gray-400 text-sm">
                    Responderemos en menos de 24 horas
                  </p>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Nombre *</label>
                    <input
                      type="text"
                      name="nombre"
                      value={form.nombre}
                      onChange={handleChange}
                      required
                      placeholder="Tu nombre"
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Email *</label>
                    <input
                      type="email"
                      name="email"
                      value={form.email}
                      onChange={handleChange}
                      required
                      placeholder="tu@email.com"
                      className="input-field"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Teléfono</label>
                    <input
                      type="tel"
                      name="telefono"
                      value={form.telefono}
                      onChange={handleChange}
                      placeholder="3001234567"
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="block text-gray-400 text-sm mb-1.5">Asunto *</label>
                    <select
                      name="asunto"
                      value={form.asunto}
                      onChange={handleChange}
                      required
                      className="select-field"
                    >
                      <option value="">Seleccionar asunto</option>
                      {asuntos.map((a) => (
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Mensaje *</label>
                  <textarea
                    name="mensaje"
                    value={form.mensaje}
                    onChange={handleChange}
                    required
                    rows={5}
                    placeholder="Escribe tu mensaje aquí..."
                    className="input-field resize-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn-primary flex items-center gap-2 text-base disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Enviando...' : 'Enviar Mensaje'}
                  <Send className="w-5 h-5" />
                </button>
              </form>
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-2">
            <div className="card p-6 sm:p-8 sticky top-24">
              <h3 className="text-white font-display font-bold text-xl mb-4">
                Atención rápida por WhatsApp
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed mb-6">
                Para una respuesta inmediata, escríbenos por WhatsApp. Nuestro equipo está
                disponible de lunes a sábado de 8am a 6pm.
              </p>
              <a
                href={whatsappUrl('Hola, quiero información')}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary flex items-center justify-center gap-2 w-full"
              >
                <MessageCircle className="w-5 h-5" />
                Escribir por WhatsApp
              </a>

              <div className="mt-8 pt-6 border-t border-border">
                <h4 className="text-white font-semibold mb-3">Síguenos</h4>
                <p className="text-gray-400 text-sm">
                  Encuéntranos en redes sociales para ver nuestros últimos vehículos
                  y promociones.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
