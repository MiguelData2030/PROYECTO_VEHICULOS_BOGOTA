'use client';

import { MessageCircle } from 'lucide-react';
import { NEGOCIO, whatsappUrl } from '@/lib/negocio';

export default function WhatsAppButton() {
  if (!NEGOCIO.whatsapp) return null;

  return (
    <a
      href={whatsappUrl('Hola, estoy interesado en un vehículo de AutoNegocio. ¿Podrían darme más información?')}
      target="_blank"
      rel="noopener noreferrer"
      className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-green-500 hover:bg-green-600 rounded-full flex items-center justify-center shadow-lg shadow-green-500/30 hover:scale-110 transition-all duration-300 group"
      aria-label="Contactar por WhatsApp"
    >
      <MessageCircle className="w-7 h-7 text-white" />
      <span className="absolute right-full mr-3 bg-dark border border-border text-white text-sm px-3 py-1.5 rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
        Escríbenos por WhatsApp
      </span>
    </a>
  );
}
