'use client';

import Link from 'next/link';
import {
  Eye,
  Award,
  ShieldCheck,
  Lightbulb,
  Car,
  Users,
  TrendingUp,
  Clock,
  ArrowRight,
  MessageCircle,
} from 'lucide-react';

const stats = [
  { label: 'Vehículos Vendidos', value: '+150', icon: Car },
  { label: 'Clientes Satisfechos', value: '98%', icon: Users },
  { label: 'Años de Experiencia', value: '5', icon: Clock },
  { label: 'En Transacciones', value: '+$2,000M', icon: TrendingUp },
];

const values = [
  {
    icon: Eye,
    title: 'Transparencia',
    description:
      'Creemos en la honestidad total. Cada vehículo incluye historial completo, peritaje profesional y documentación verificada. Sin sorpresas.',
  },
  {
    icon: Award,
    title: 'Calidad',
    description:
      'Solo trabajamos con vehículos que cumplen nuestros estrictos estándares de calidad. Cada carro pasa por una inspección de más de 150 puntos.',
  },
  {
    icon: ShieldCheck,
    title: 'Confianza',
    description:
      'Más de 5 años en el mercado nos respaldan. Nuestros clientes son nuestra mejor carta de presentación y muchos regresan para su próximo vehículo.',
  },
  {
    icon: Lightbulb,
    title: 'Innovación',
    description:
      'Utilizamos tecnología de punta para ofrecerte la mejor experiencia de compra y venta. Procesos digitales, ágiles y seguros.',
  },
];

export default function NosotrosPage() {
  return (
    <div className="pt-16">
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(212,168,67,0.08),transparent_50%)]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="max-w-3xl">
            <p className="text-primary font-medium uppercase tracking-widest text-sm mb-4">
              Nuestra historia
            </p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-display font-bold text-white leading-tight mb-6">
              Sobre{' '}
              <span className="gold-gradient">AutoNegocio</span>
            </h1>
            <p className="text-gray-400 text-lg sm:text-xl leading-relaxed max-w-2xl">
              Somos una empresa dedicada a la compra y venta de vehículos usados premium
              en Bogotá. Nuestro compromiso es ofrecer transparencia, calidad y el mejor servicio.
            </p>
          </div>
        </div>
      </section>

      {/* Mission / Vision */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="card p-8">
            <h2 className="text-2xl font-display font-bold text-white mb-4">
              Nuestra Misión
            </h2>
            <p className="text-gray-400 leading-relaxed">
              Facilitar la compra y venta de vehículos usados en Colombia, ofreciendo un
              servicio integral que garantice la satisfacción total de nuestros clientes.
              Nos enfocamos en brindar transparencia en cada transacción, vehículos de
              calidad verificada y acompañamiento personalizado en todo el proceso.
            </p>
          </div>
          <div className="card p-8">
            <h2 className="text-2xl font-display font-bold text-white mb-4">
              Nuestra Visión
            </h2>
            <p className="text-gray-400 leading-relaxed">
              Ser la plataforma líder de compra y venta de vehículos usados premium en
              Colombia, reconocida por nuestra innovación tecnológica, excelencia en el
              servicio y compromiso con la confianza del cliente. Aspiramos a transformar
              la experiencia automotriz en el país.
            </p>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center mb-10">
            <h2 className="section-title">Nuestros números hablan</h2>
            <p className="section-subtitle">Resultados que respaldan nuestra trayectoria</p>
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
            {stats.map((stat) => (
              <div key={stat.label} className="stat-card">
                <stat.icon className="w-8 h-8 text-primary mx-auto mb-3" />
                <p className="text-3xl font-bold text-white mb-1">{stat.value}</p>
                <p className="text-gray-400 text-sm">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-12">
          <h2 className="section-title">Nuestros Valores</h2>
          <p className="section-subtitle">Los pilares que guían cada decisión que tomamos</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {values.map((v) => (
            <div
              key={v.title}
              className="card p-6 text-center hover:bg-surface-light group"
            >
              <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-4 group-hover:bg-primary/20 transition-colors">
                <v.icon className="w-7 h-7 text-primary" />
              </div>
              <h3 className="text-white font-semibold text-lg mb-2">{v.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{v.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-20">
        <div className="relative rounded-2xl overflow-hidden bg-gradient-to-r from-primary/10 via-surface to-primary/5 border border-primary/20 p-8 sm:p-12">
          <div className="relative z-10 max-w-2xl">
            <h2 className="text-3xl sm:text-4xl font-display font-bold text-white mb-4">
              ¿Listo para trabajar con nosotros?
            </h2>
            <p className="text-gray-400 text-lg mb-6">
              Ya sea que quieras comprar o vender, estamos aquí para ayudarte.
              Contáctanos y descubre por qué somos la mejor opción en Bogotá.
            </p>
            <div className="flex flex-wrap gap-4">
              <a
                href="https://wa.me/573001234567?text=Hola%2C%20quiero%20información"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary flex items-center gap-2"
              >
                <MessageCircle className="w-5 h-5" />
                Escribir por WhatsApp
              </a>
              <Link href="/contacto" className="btn-secondary flex items-center gap-2">
                Formulario de Contacto
                <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
