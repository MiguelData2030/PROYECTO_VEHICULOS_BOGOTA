'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft, MapPin, Gauge, Fuel, Settings2, Calendar, Palette,
  Shield, FileCheck, ShieldCheck, Users, MessageCircle, Phone,
  ChevronLeft, ChevronRight, Loader2, CheckCircle2, XCircle,
  Car, Hash, Cog,
} from 'lucide-react';
import FinancingCalculator from '@/components/FinancingCalculator';
import { formatCOP, formatNumber, type Vehicle } from '@/lib/data';
import { fetchVehiculo } from '@/lib/api';
import { whatsappUrl, telUrl } from '@/lib/negocio';

// Static export: the vehicle id comes from the query string (/catalogo/vehiculo?id=13)
export default function VehiculoDetallePage() {
  return (
    <Suspense fallback={null}>
      <VehiculoDetalle />
    </Suspense>
  );
}

function VehiculoDetalle() {
  const searchParams = useSearchParams();
  const id = Number(searchParams.get('id'));

  const [vehicle, setVehicle] = useState<Vehicle | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPhoto, setCurrentPhoto] = useState(0);

  useEffect(() => {
    setLoading(true);
    fetchVehiculo(id)
      .then((data) => setVehicle(data))
      .catch(() => setVehicle(null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="pt-16 flex items-center justify-center min-h-[80vh]">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
      </div>
    );
  }

  if (!vehicle) {
    return (
      <div className="pt-16 min-h-[80vh] flex flex-col items-center justify-center">
        <Car className="w-16 h-16 text-gray-600 mb-4" />
        <h2 className="text-2xl font-bold text-white mb-2">Vehículo no encontrado</h2>
        <p className="text-gray-400 mb-6">El vehículo que buscas no existe o fue removido.</p>
        <Link href="/catalogo" className="btn-primary">Volver al catálogo</Link>
      </div>
    );
  }

  const photos = vehicle.fotos && vehicle.fotos.length > 0
    ? vehicle.fotos
    : vehicle.imagen && vehicle.imagen !== '/placeholder-car.jpg'
      ? [vehicle.imagen]
      : [];

  const whatsappMsg = encodeURIComponent(
    `Hola, estoy interesado en el ${vehicle.marca} ${vehicle.modelo} ${vehicle.anio} publicado en su web. ¿Está disponible?`
  );

  const docs = [
    { label: 'SOAT vigente', ok: vehicle.soat, icon: ShieldCheck },
    { label: 'Técnico-mecánica', ok: vehicle.tecnicomecanica, icon: FileCheck },
    { label: 'Impuestos al día', ok: vehicle.impuestos, icon: Shield },
  ];

  const specs = [
    { label: 'Año', value: vehicle.anio.toString(), icon: Calendar },
    { label: 'Kilometraje', value: `${formatNumber(vehicle.kilometraje)} km`, icon: Gauge },
    { label: 'Transmisión', value: vehicle.transmision, icon: Cog },
    { label: 'Combustible', value: vehicle.combustible, icon: Fuel },
    { label: 'Color', value: vehicle.color, icon: Palette },
    { label: 'Tipo', value: vehicle.tipo, icon: Car },
    { label: 'Ubicación', value: vehicle.ubicacion, icon: MapPin },
  ];

  return (
    <div className="pt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb */}
        <Link
          href="/catalogo"
          className="inline-flex items-center gap-2 text-gray-400 hover:text-primary transition-colors mb-6 text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Volver al catálogo
        </Link>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Left: Images + Description (3 cols) */}
          <div className="lg:col-span-3 space-y-6">
            {/* Image Gallery */}
            <div className="card overflow-hidden">
              <div className="relative aspect-[16/10] bg-dark">
                {photos.length > 0 ? (
                  <>
                    <img
                      src={photos[currentPhoto].startsWith('http')
                        ? photos[currentPhoto]
                        : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${photos[currentPhoto]}`}
                      alt={`${vehicle.marca} ${vehicle.modelo}`}
                      className="w-full h-full object-cover"
                    />
                    {photos.length > 1 && (
                      <>
                        <button
                          onClick={() => setCurrentPhoto((p) => (p === 0 ? photos.length - 1 : p - 1))}
                          className="absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-dark/70 text-white hover:bg-dark transition-colors"
                        >
                          <ChevronLeft className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => setCurrentPhoto((p) => (p === photos.length - 1 ? 0 : p + 1))}
                          className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-full bg-dark/70 text-white hover:bg-dark transition-colors"
                        >
                          <ChevronRight className="w-5 h-5" />
                        </button>
                        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
                          {photos.map((_, i) => (
                            <button
                              key={i}
                              onClick={() => setCurrentPhoto(i)}
                              className={`w-2.5 h-2.5 rounded-full transition-colors ${
                                i === currentPhoto ? 'bg-primary' : 'bg-white/40'
                              }`}
                            />
                          ))}
                        </div>
                      </>
                    )}
                  </>
                ) : (
                  <div className="w-full h-full bg-gradient-to-br from-surface-light to-dark flex items-center justify-center">
                    <div className="text-center">
                      <Settings2 className="w-20 h-20 text-gray-600 mx-auto mb-3" />
                      <p className="text-gray-500">{vehicle.marca} {vehicle.modelo}</p>
                    </div>
                  </div>
                )}

                {/* Status badge */}
                {vehicle.estado === 'Reservado' && (
                  <span className="absolute top-4 left-4 badge-warning text-sm px-3 py-1">Reservado</span>
                )}
                {vehicle.estado === 'Vendido' && (
                  <span className="absolute top-4 left-4 badge-danger text-sm px-3 py-1">Vendido</span>
                )}
              </div>
            </div>

            {/* Specs Grid */}
            <div className="card p-6">
              <h3 className="text-white font-semibold text-lg mb-4">Especificaciones</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {specs.map((spec) => (
                  <div key={spec.label} className="bg-dark rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-1">
                      <spec.icon className="w-4 h-4 text-primary" />
                      <span className="text-xs text-gray-500">{spec.label}</span>
                    </div>
                    <p className="text-white font-medium">{spec.value}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Description */}
            {vehicle.descripcion && (
              <div className="card p-6">
                <h3 className="text-white font-semibold text-lg mb-3">Descripción</h3>
                <p className="text-gray-400 leading-relaxed">{vehicle.descripcion}</p>
              </div>
            )}

            {/* Documentation */}
            <div className="card p-6">
              <h3 className="text-white font-semibold text-lg mb-4">Documentación</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {docs.map((doc) => (
                  <div
                    key={doc.label}
                    className={`flex items-center gap-3 p-3 rounded-xl border ${
                      doc.ok
                        ? 'border-green-500/20 bg-green-500/5'
                        : 'border-red-500/20 bg-red-500/5'
                    }`}
                  >
                    {doc.ok ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                    )}
                    <span className={`text-sm font-medium ${doc.ok ? 'text-green-400' : 'text-red-400'}`}>
                      {doc.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right: Price + CTA + Financing (2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Price Card */}
            <div className="card-elevated p-6">
              <p className="text-xs text-primary font-medium uppercase tracking-wider mb-1">{vehicle.marca}</p>
              <h1 className="text-2xl font-bold text-white mb-1">{vehicle.modelo}</h1>
              <p className="text-gray-500 text-sm mb-4">{vehicle.anio} · {formatNumber(vehicle.kilometraje)} km · {vehicle.ubicacion}</p>

              <div className="border-t border-border pt-4 mb-6">
                <p className="text-xs text-gray-500 mb-1">Precio</p>
                <p className="text-4xl font-bold gold-gradient">{formatCOP(vehicle.precio)}</p>
              </div>

              {/* Contact Buttons */}
              <div className="space-y-3">
                <a
                  href={`${whatsappUrl()}?text=${whatsappMsg}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary w-full flex items-center justify-center gap-2 text-base py-3"
                >
                  <MessageCircle className="w-5 h-5" />
                  Consultar por WhatsApp
                </a>
                <a
                  href={telUrl()}
                  className="btn-secondary w-full flex items-center justify-center gap-2 text-base py-3"
                >
                  <Phone className="w-5 h-5" />
                  Llamar ahora
                </a>
              </div>

              <p className="text-xs text-gray-500 text-center mt-4">
                Respuesta inmediata en horario laboral
              </p>
            </div>

            {/* Benefits */}
            <div className="card p-5 space-y-3">
              {[
                { icon: ShieldCheck, text: 'Garantía de motor y caja incluida' },
                { icon: FileCheck, text: 'Trámites de traspaso incluidos' },
                { icon: Shield, text: 'Peritaje profesional verificado' },
                { icon: Users, text: 'Financiación con las mejores tasas' },
              ].map((b) => (
                <div key={b.text} className="flex items-center gap-3">
                  <b.icon className="w-5 h-5 text-primary flex-shrink-0" />
                  <span className="text-gray-300 text-sm">{b.text}</span>
                </div>
              ))}
            </div>

            {/* Financing Calculator */}
            <FinancingCalculator vehiclePrice={vehicle.precio} />
          </div>
        </div>
      </div>
    </div>
  );
}
