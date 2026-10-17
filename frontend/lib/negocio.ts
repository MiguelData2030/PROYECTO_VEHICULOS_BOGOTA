/**
 * Datos reales del negocio. Se configuran con variables de entorno en Vercel
 * (Settings → Environment Variables) para no tener que tocar código.
 */

const digits = (s: string) => s.replace(/\D/g, '');

const whatsapp = digits(process.env.NEXT_PUBLIC_WHATSAPP || '');

export const NEGOCIO = {
  nombre: 'AutoNegocio',
  /** Número de WhatsApp con indicativo, solo dígitos. Ej: 573001234567 */
  whatsapp,
  whatsappDisplay: whatsapp.length === 12
    ? `+${whatsapp.slice(0, 2)} ${whatsapp.slice(2, 5)} ${whatsapp.slice(5, 8)} ${whatsapp.slice(8)}`
    : whatsapp,
  telefono: process.env.NEXT_PUBLIC_TELEFONO || '',
  email: process.env.NEXT_PUBLIC_EMAIL || '',
  direccion: process.env.NEXT_PUBLIC_DIRECCION || 'Bogotá, Colombia',
  horario: process.env.NEXT_PUBLIC_HORARIO || 'Lun - Sáb: 8:00 AM - 6:00 PM',
};

/** Perfiles en redes (URL completa). Los que no estén configurados no se muestran. */
export const REDES = [
  { red: 'instagram', label: 'Instagram', url: process.env.NEXT_PUBLIC_INSTAGRAM || '' },
  { red: 'facebook', label: 'Facebook', url: process.env.NEXT_PUBLIC_FACEBOOK || '' },
  { red: 'tiktok', label: 'TikTok', url: process.env.NEXT_PUBLIC_TIKTOK || '' },
].filter((r) => r.url);

/**
 * Link de WhatsApp con mensaje prellenado. Sin número configurado lleva a la
 * página de contacto (wa.me sin número abre WhatsApp sin destinatario).
 */
export function whatsappUrl(mensaje?: string): string {
  if (!NEGOCIO.whatsapp) return '/contacto/';
  const base = `https://wa.me/${NEGOCIO.whatsapp}`;
  return mensaje ? `${base}?text=${encodeURIComponent(mensaje)}` : base;
}

/** Link para llamar, o null si no hay teléfono ni WhatsApp configurado. */
export function telUrl(): string | null {
  const num = digits(NEGOCIO.telefono) || NEGOCIO.whatsapp;
  if (!num) return null;
  return `tel:+${num.length === 10 ? '57' + num : num}`;
}

export function mapsUrl(): string {
  return `https://maps.google.com/?q=${encodeURIComponent(NEGOCIO.direccion)}`;
}
