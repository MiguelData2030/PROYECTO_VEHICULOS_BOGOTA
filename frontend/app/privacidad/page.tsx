import { NEGOCIO } from '@/lib/negocio';

// Plantilla basada en la Ley 1581 de 2012 y el Decreto 1377 de 2013.
// Revísala con tu asesor legal y completa la razón social y el NIT reales.
const contacto = [NEGOCIO.email, NEGOCIO.telefono || NEGOCIO.whatsappDisplay].filter(Boolean).join(' · ');

const secciones: { titulo: string; parrafos: string[] }[] = [
  {
    titulo: '1. Responsable del tratamiento',
    parrafos: [
      `${NEGOCIO.nombre}, con domicilio en ${NEGOCIO.direccion}, es responsable del tratamiento de los datos personales que recoge a través de este sitio web, sus redes sociales, WhatsApp y su punto de venta.`,
      contacto
        ? `Canales de atención: ${contacto}.`
        : 'Canal de atención: el formulario de la página de Contacto.',
    ],
  },
  {
    titulo: '2. Datos que recogemos',
    parrafos: [
      'Nombre, teléfono, correo electrónico y los datos del vehículo que nos compartes (marca, modelo, año, kilometraje, estado y precio esperado), así como el contenido de los mensajes que nos envías.',
      'No solicitamos datos sensibles ni datos de menores de edad.',
    ],
  },
  {
    titulo: '3. Finalidades',
    parrafos: [
      'Responder tus solicitudes y cotizaciones; hacerte ofertas de compra de tu vehículo; ofrecerte vehículos de nuestro inventario, financiación y servicios relacionados; hacer el seguimiento comercial de tu solicitud; y cumplir obligaciones legales y contables.',
      'Solo te enviaremos comunicaciones comerciales si nos diste tu autorización.',
    ],
  },
  {
    titulo: '4. Tus derechos',
    parrafos: [
      'Como titular puedes conocer, actualizar y rectificar tus datos; pedir prueba de la autorización que nos diste; ser informado sobre el uso que les damos; revocar la autorización o pedir que los eliminemos cuando no exista un deber legal de conservarlos; y presentar quejas ante la Superintendencia de Industria y Comercio.',
    ],
  },
  {
    titulo: '5. Consultas y reclamos',
    parrafos: [
      'Puedes ejercer tus derechos por cualquiera de los canales de atención indicados. Las consultas se responden en un máximo de diez (10) días hábiles y los reclamos en un máximo de quince (15) días hábiles, prorrogables en los términos de la Ley 1581 de 2012.',
    ],
  },
  {
    titulo: '6. Seguridad y conservación',
    parrafos: [
      'Guardamos tus datos con medidas técnicas y administrativas razonables para evitar su pérdida, consulta o uso no autorizado, y los conservamos mientras sean necesarios para las finalidades descritas.',
    ],
  },
  {
    titulo: '7. Vigencia',
    parrafos: [
      'Esta política rige desde su publicación en este sitio. Cualquier cambio sustancial se informará por este mismo medio.',
    ],
  },
];

export default function PrivacidadPage() {
  return (
    <div className="pt-16">
      <section className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h1 className="text-3xl sm:text-4xl font-display font-bold text-white mb-4">
          Política de tratamiento de datos personales
        </h1>
        <p className="text-gray-400 mb-10">
          En cumplimiento de la Ley 1581 de 2012 y el Decreto 1377 de 2013.
        </p>
        <div className="space-y-8">
          {secciones.map((s) => (
            <div key={s.titulo}>
              <h2 className="text-xl font-semibold text-white mb-3">{s.titulo}</h2>
              {s.parrafos.map((p) => (
                <p key={p} className="text-gray-400 leading-relaxed mb-3">{p}</p>
              ))}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
