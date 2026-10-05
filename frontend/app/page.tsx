'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  ArrowRight,
  ShieldCheck,
  Landmark,
  FileCheck,
  Eye,
  Star,
  TrendingUp,
  Users,
  Car,
  MessageCircle,
  ChevronRight,
} from 'lucide-react';
import VehicleCard from '@/components/VehicleCard';
import SearchBar from '@/components/SearchBar';
import { formatCOP, type Vehicle } from '@/lib/data';
import { fetchCatalogo } from '@/lib/api';
import { whatsappUrl } from '@/lib/negocio';

// Value propositions (no invented figures — replace with real numbers once you have them)
const stats = [
  { label: 'Documentos verificados en RUNT', value: '100%', icon: Car },
  { label: 'Asesoría personalizada', value: '1 a 1', icon: Users },
  { label: 'Precios basados en datos del mercado', value: 'IA', icon: TrendingUp },
  { label: 'Atención por WhatsApp', value: 'Lun-Sáb', icon: Star },
];

const benefits = [
  {
    icon: ShieldCheck,
    title: 'Garantía',
    description: 'Todos nuestros vehículos cuentan con garantía de motor y caja. Tu tranquilidad es nuestra prioridad.',
  },
  {
    icon: Landmark,
    title: 'Financiación',
    description: 'Trabajamos con las mejores entidades financieras para ofrecerte las tasas más competitivas del mercado.',
  },
  {
    icon: FileCheck,
    title: 'Documentación al Día',
    description: 'SOAT, técnico-mecánica e impuestos verificados. Nos encargamos de todos los trámites de traspaso.',
  },
  {
    icon: Eye,
    title: 'Transparencia Total',
    description: 'Historial completo de cada vehículo. Sin sorpresas. Peritaje profesional incluido en cada compra.',
  },
];

const brands = ['Toyota', 'Mazda', 'Chevrolet', 'Kia', 'Renault', 'Hyundai'];

export default function HomePage() {
  const [featured, setFeatured] = useState<Vehicle[]>([]);

  useEffect(() => {
    fetchCatalogo()
      .then((data) => setFeatured(data.slice(0, 6)))
      .catch(() => setFeatured([]));
  }, []);

  return (
    <div className="pt-16">
      {/* Hero */}
      <section className="relative min-h-[85vh] flex items-center overflow-hidden">
        <div className="absolute inset-0 bg-hero-pattern" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(212,168,67,0.08),transparent_50%)]" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="max-w-3xl">
            <p className="text-primary font-medium uppercase tracking-widest text-sm mb-4">
              Compra &amp; Venta de Vehículos Premium
            </p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-display font-bold text-white leading-tight mb-6">
              Tu próximo vehículo{' '}
              <span className="gold-gradient">te espera</span>
            </h1>
            <p className="text-gray-400 text-lg sm:text-xl leading-relaxed mb-8 max-w-2xl">
              Descubre nuestra selección de vehículos premium verificados en Bogotá.
              Garantía, financiación y documentación al día. Compra con total confianza.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/catalogo" className="btn-primary flex items-center gap-2 text-base">
                Ver Catálogo
                <ArrowRight className="w-5 h-5" />
              </Link>
              <Link href="/vender" className="btn-secondary flex items-center gap-2 text-base">
                Vender mi Vehículo
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Search */}
      <section className="relative -mt-8 z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <SearchBar />
      </section>

      {/* Featured Vehicles */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="flex items-end justify-between mb-10">
          <div>
            <h2 className="section-title">Vehículos Destacados</h2>
            <p className="section-subtitle">Los mejores vehículos seleccionados para ti</p>
          </div>
          <Link href="/catalogo" className="hidden sm:flex items-center gap-1 text-primary hover:text-primary-light font-medium text-sm transition-colors">
            Ver todos
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {featured.map((v) => (
            <VehicleCard key={v.id} vehicle={v} />
          ))}
        </div>
        {featured.length === 0 && (
          <div className="card p-10 text-center text-gray-400">
            Estamos preparando nuevos vehículos. Escríbenos por WhatsApp y te avisamos apenas lleguen.
          </div>
        )}
        <div className="mt-8 text-center sm:hidden">
          <Link href="/catalogo" className="btn-secondary inline-flex items-center gap-2">
            Ver todo el catálogo
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
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

      {/* Why Choose Us */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-12">
          <h2 className="section-title">¿Por qué elegirnos?</h2>
          <p className="section-subtitle">Comprometidos con tu satisfacción en cada paso</p>
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
      </section>

      {/* Brands */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-display font-bold text-white">Marcas con las que trabajamos</h2>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-6">
            {brands.map((brand) => (
              <Link
                key={brand}
                href={`/catalogo?marca=${brand}`}
                className="flex items-center justify-center h-20 rounded-xl border border-border bg-dark hover:border-primary/30 hover:bg-primary/5 transition-all cursor-pointer"
              >
                <span className="text-gray-400 font-semibold text-lg hover:text-primary transition-colors">
                  {brand}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="relative rounded-2xl overflow-hidden bg-gradient-to-r from-primary/10 via-surface to-primary/5 border border-primary/20 p-8 sm:p-12">
          <div className="relative z-10 max-w-2xl">
            <h2 className="text-3xl sm:text-4xl font-display font-bold text-white mb-4">
              ¿Listo para encontrar tu vehículo ideal?
            </h2>
            <p className="text-gray-400 text-lg mb-6">
              Contáctanos ahora y recibe asesoría personalizada. Estamos disponibles por WhatsApp
              para resolver todas tus dudas.
            </p>
            <div className="flex flex-wrap gap-4">
              <a
                href={whatsappUrl('Hola, estoy interesado en un vehículo')}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary flex items-center gap-2"
              >
                <MessageCircle className="w-5 h-5" />
                Escribir por WhatsApp
              </a>
              <Link href="/contacto" className="btn-secondary">
                Formulario de Contacto
              </Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
