'use client';

import Link from 'next/link';
import { Car, MapPin, Phone, Mail, Clock, Facebook, Instagram, Youtube } from 'lucide-react';
import { NEGOCIO } from '@/lib/negocio';

export default function Footer() {
  return (
    <footer className="bg-surface border-t border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Brand */}
          <div>
            <Link href="/" className="flex items-center gap-2 mb-4">
              <div className="w-9 h-9 bg-primary rounded-lg flex items-center justify-center">
                <Car className="w-5 h-5 text-dark" />
              </div>
              <span className="text-xl font-bold text-white">
                Auto<span className="text-primary">Negocio</span>
              </span>
            </Link>
            <p className="text-gray-400 text-sm leading-relaxed">
              Tu aliado confiable para la compra y venta de vehículos usados premium en Bogotá.
              Garantía, financiación y total transparencia.
            </p>
            <div className="flex items-center gap-3 mt-4">
              <a href="#" className="w-9 h-9 rounded-lg bg-dark flex items-center justify-center text-gray-400 hover:text-primary hover:bg-primary/10 transition-all">
                <Facebook className="w-4 h-4" />
              </a>
              <a href="#" className="w-9 h-9 rounded-lg bg-dark flex items-center justify-center text-gray-400 hover:text-primary hover:bg-primary/10 transition-all">
                <Instagram className="w-4 h-4" />
              </a>
              <a href="#" className="w-9 h-9 rounded-lg bg-dark flex items-center justify-center text-gray-400 hover:text-primary hover:bg-primary/10 transition-all">
                <Youtube className="w-4 h-4" />
              </a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-white font-semibold mb-4">Enlaces Rápidos</h3>
            <ul className="space-y-2">
              {[
                { href: '/catalogo', label: 'Catálogo de Vehículos' },
                { href: '/vender', label: 'Vender mi Vehículo' },
                { href: '/nosotros', label: 'Sobre Nosotros' },
                { href: '/contacto', label: 'Contacto' },
              ].map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="text-gray-400 hover:text-primary text-sm transition-colors">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Services */}
          <div>
            <h3 className="text-white font-semibold mb-4">Servicios</h3>
            <ul className="space-y-2 text-sm text-gray-400">
              <li>Compra de Vehículos</li>
              <li>Venta de Vehículos</li>
              <li>Financiación</li>
              <li>Traspaso de Propiedad</li>
              <li>Peritaje Vehicular</li>
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h3 className="text-white font-semibold mb-4">Contacto</h3>
            <ul className="space-y-3">
              <li className="flex items-start gap-3 text-sm text-gray-400">
                <MapPin className="w-4 h-4 mt-0.5 text-primary flex-shrink-0" />
                {NEGOCIO.direccion}
              </li>
              {(NEGOCIO.telefono || NEGOCIO.whatsappDisplay) && (
                <li className="flex items-center gap-3 text-sm text-gray-400">
                  <Phone className="w-4 h-4 text-primary flex-shrink-0" />
                  {NEGOCIO.telefono || NEGOCIO.whatsappDisplay}
                </li>
              )}
              {NEGOCIO.email && (
                <li className="flex items-center gap-3 text-sm text-gray-400">
                  <Mail className="w-4 h-4 text-primary flex-shrink-0" />
                  {NEGOCIO.email}
                </li>
              )}
              <li className="flex items-start gap-3 text-sm text-gray-400">
                <Clock className="w-4 h-4 mt-0.5 text-primary flex-shrink-0" />
                {NEGOCIO.horario}
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-border mt-10 pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} AutoNegocio. Todos los derechos reservados.
          </p>
          <div className="flex items-center gap-4 text-sm text-gray-500">
            <a href="#" className="hover:text-gray-300 transition-colors">Política de Privacidad</a>
            <a href="#" className="hover:text-gray-300 transition-colors">Términos y Condiciones</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
