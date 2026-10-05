import type { Metadata } from 'next';
import { Inter, Playfair_Display } from 'next/font/google';
import './globals.css';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';
import WhatsAppButton from '@/components/WhatsAppButton';
import { Toaster } from 'react-hot-toast';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'AutoNegocio - Compra y Venta de Vehículos Premium en Bogotá',
  description:
    'AutoNegocio es tu aliado para comprar y vender vehículos usados de alta calidad en Bogotá. Garantía, financiación y documentación al día. Encuentra tu próximo vehículo con total confianza.',
  keywords:
    'carros usados bogota, vehiculos usados, compra venta carros, concesionario bogota, autos seminuevos colombia',
  openGraph: {
    title: 'AutoNegocio - Vehículos Premium en Bogotá',
    description:
      'Compra y vende vehículos usados con total confianza. Garantía, financiación y documentación al día.',
    type: 'website',
    locale: 'es_CO',
    siteName: 'AutoNegocio',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className={`${inter.variable} ${playfair.variable}`}>
      <body className="font-sans bg-dark text-white min-h-screen flex flex-col">
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: '#1A1A1A',
              color: '#fff',
              border: '1px solid #2A2A2A',
            },
          }}
        />
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
        <WhatsAppButton />
      </body>
    </html>
  );
}
