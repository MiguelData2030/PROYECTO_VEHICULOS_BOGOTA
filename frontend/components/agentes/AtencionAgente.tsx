'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Send, Loader2, UserRound, Bot, Sparkles, Cpu, PlayCircle, Flame } from 'lucide-react';
import toast from 'react-hot-toast';
import { canalInfo } from '@/lib/canales';
import { formatCOP } from '@/lib/data';
import { apiErrorMessage } from '@/lib/api-admin';
import {
  enviarMensaje, simularAtencion, type RespuestaAtencion, type SimulacionAtencion,
} from '@/lib/api-agentes';
import { Box, Cargando, F } from './ui';

const EJEMPLOS = [
  'Hola, busco una camioneta Mazda de hasta 150 millones, la necesito esta semana',
  'Quiero vender mi Chevrolet 2019, ¿cuánto me dan?',
  '¿Financian? Gano 6 millones al mes y quiero un carro',
  '¿El Kia que publicaron en Instagram sigue disponible?',
  'Llevo 3 días esperando los papeles del traspaso, muy mal servicio',
];

const INTENCION: Record<string, string> = {
  comprar: 'Quiere comprar', vender: 'Quiere vender', financiacion: 'Financiación',
  disponibilidad: 'Disponibilidad', cita: 'Cita / visita', queja: 'Queja', otro: 'No clasificado',
};

const TEMP: Record<string, string> = {
  caliente: 'bg-red-500/15 text-red-300', tibio: 'bg-yellow-500/15 text-yellow-300', frio: 'bg-blue-500/15 text-blue-300',
};

type Turno = { de: 'cliente'; texto: string } | { de: 'agente'; r: RespuestaAtencion };

export default function AtencionAgente() {
  const [canal, setCanal] = useState('whatsapp');
  const [cliente, setCliente] = useState('Laura Gómez');
  const [texto, setTexto] = useState('');
  const [guardar, setGuardar] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [chat, setChat] = useState<Turno[]>([]);
  const fin = useRef<HTMLDivElement>(null);

  useEffect(() => { fin.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [chat]);

  const enviar = async (e?: FormEvent, mensaje = texto) => {
    e?.preventDefault();
    if (mensaje.trim().length < 2) return;
    setChat((c) => [...c, { de: 'cliente', texto: mensaje }]);
    setTexto('');
    setEnviando(true);
    try {
      const r = await enviarMensaje({ mensaje, canal, cliente, guardar_lead: guardar });
      setChat((c) => [...c, { de: 'agente', r }]);
      if (r.lead_id) toast.success('Lead guardado en el CRM');
    } catch (err) {
      toast.error(apiErrorMessage(err, 'El agente no pudo responder'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card p-5 space-y-3 h-fit">
          <p className="text-white font-semibold">Escríbele como si fueras un cliente</p>
          <F label="Canal">
            <select value={canal} onChange={(e) => setCanal(e.target.value)} className="select-field py-2">
              {['whatsapp', 'instagram', 'facebook', 'tiktok', 'web'].map((c) => <option key={c} value={c}>{canalInfo(c).label}</option>)}
            </select>
          </F>
          <F label="Nombre del cliente">
            <input value={cliente} onChange={(e) => setCliente(e.target.value)} className="input-field py-2" />
          </F>
          <label className="flex items-start gap-2 text-xs text-gray-400 cursor-pointer">
            <input type="checkbox" checked={guardar} onChange={(e) => setGuardar(e.target.checked)} className="accent-primary mt-0.5" />
            Guardar cada conversación como lead en el CRM (etapa «nuevo»)
          </label>
          <div>
            <p className="text-gray-400 text-xs mb-2">Mensajes de ejemplo</p>
            <div className="flex flex-col gap-1.5">
              {EJEMPLOS.map((m) => (
                <button key={m} onClick={() => enviar(undefined, m)} disabled={enviando}
                  className="text-left text-xs text-gray-300 bg-dark border border-border rounded-lg px-3 py-2 hover:border-primary/50 disabled:opacity-50">
                  {m}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="card lg:col-span-2 flex flex-col h-[560px]">
          <div className="px-5 py-3 border-b border-border flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-xs ${canalInfo(canal).cls}`}>{canalInfo(canal).label}</span>
            <span className="text-white text-sm">{cliente}</span>
            <span className="text-gray-500 text-xs ml-auto">Responde en segundos, a cualquier hora</span>
          </div>
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {chat.length === 0 && (
              <p className="text-center text-gray-500 text-sm mt-20">Escribe un mensaje o toca uno de los ejemplos.</p>
            )}
            {chat.map((t, i) => t.de === 'cliente' ? (
              <div key={i} className="flex justify-end gap-2">
                <p className="bg-primary/15 text-gray-100 text-sm rounded-2xl rounded-tr-sm px-4 py-2 max-w-[80%]">{t.texto}</p>
                <UserRound className="w-6 h-6 text-gray-500 flex-shrink-0" />
              </div>
            ) : (
              <div key={i} className="flex gap-2">
                <Bot className="w-6 h-6 text-primary flex-shrink-0" />
                <div className="max-w-[85%] space-y-1.5">
                  <p className="bg-dark border border-border text-gray-100 text-sm rounded-2xl rounded-tl-sm px-4 py-2 whitespace-pre-wrap">{t.r.respuesta}</p>
                  <div className="flex flex-wrap gap-1.5 text-[11px]">
                    <span className="px-2 py-0.5 rounded bg-surface-light text-gray-300">{INTENCION[t.r.intencion] ?? t.r.intencion}</span>
                    {t.r.a_humano
                      ? <span className="px-2 py-0.5 rounded bg-orange-500/15 text-orange-300">Pasa a un asesor</span>
                      : <span className={`px-2 py-0.5 rounded ${TEMP[t.r.temperatura] ?? 'bg-surface-light text-gray-300'}`}>Lead {t.r.temperatura}</span>}
                    {t.r.presupuesto && <span className="px-2 py-0.5 rounded bg-surface-light text-gray-300">Presupuesto {formatCOP(t.r.presupuesto)}</span>}
                    {t.r.marca && <span className="px-2 py-0.5 rounded bg-surface-light text-gray-300">{t.r.marca}</span>}
                    {t.r.urgente && <span className="px-2 py-0.5 rounded bg-red-500/15 text-red-300">Urgente</span>}
                    {t.r.lead_id && <span className="px-2 py-0.5 rounded bg-green-500/15 text-green-300">En el CRM</span>}
                    <span className="text-gray-500 flex items-center gap-1">
                      {t.r.respuesta_ia ? <><Sparkles className="w-3 h-3 text-green-400" /> Claude</> : <><Cpu className="w-3 h-3" /> reglas</>}
                    </span>
                  </div>
                </div>
              </div>
            ))}
            {enviando && <div className="flex gap-2 text-gray-500 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> escribiendo…</div>}
            <div ref={fin} />
          </div>
          <form onSubmit={enviar} className="p-3 border-t border-border flex gap-2">
            <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Escribe un mensaje…" className="input-field py-2 flex-1" />
            <button disabled={enviando || texto.trim().length < 2} className="btn-primary px-4 disabled:opacity-50"><Send className="w-4 h-4" /></button>
          </form>
        </div>
      </div>

      <Simulacion />
    </div>
  );
}

function Simulacion() {
  const [semilla, setSemilla] = useState(2026);
  const [loading, setLoading] = useState(false);
  const [r, setR] = useState<SimulacionAtencion | null>(null);

  const run = async (s = semilla) => {
    setLoading(true);
    try {
      setR(await simularAtencion(s));
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo simular'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <p className="text-white font-semibold">Simular un día completo de mensajes</p>
          <p className="text-gray-500 text-xs">40 mensajes ficticios de WhatsApp y redes, respondidos con el inventario real.</p>
        </div>
        <div className="flex gap-2">
          {r && <button onClick={() => { setSemilla(semilla + 1); run(semilla + 1); }} disabled={loading} className="btn-ghost text-sm">Otro día</button>}
          <button onClick={() => run()} disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />} Simular día
          </button>
        </div>
      </div>
      {loading && <Cargando />}
      {r && !loading && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <Box label="Respondidos sin asesor" value={`${r.resueltos_automaticamente} de ${r.mensajes}`} sub={`${r.resueltos_pct}%`} accent="text-green-400" />
            <Box label="Primera respuesta" value={`${r.tiempo_respuesta.agente_min} min`} sub={`antes ${r.tiempo_respuesta.asesor_min} min`} accent="text-primary" />
            <Box label="Fuera de horario" value={String(r.fuera_de_horario)} sub="atendidos igual" />
            <Box label="Leads calientes" value={String(r.leads_calientes)} sub="para llamar primero" accent="text-red-300" />
            <Box label="Intención acertada" value={`${r.precision_intencion_pct}%`} sub="vs. la etiqueta real" />
          </div>
          <div className="card p-5 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs uppercase border-b border-border">
                  <th className="text-left py-2">Hora</th><th className="text-left">Canal</th><th className="text-left">Mensaje</th>
                  <th className="text-left">Intención</th><th className="text-left">Resultado</th>
                </tr>
              </thead>
              <tbody>
                {r.detalle.map((m, i) => (
                  <tr key={i} className="border-b border-border/50 align-top">
                    <td className="py-2 text-gray-500">{m.hora}</td>
                    <td><span className={`px-2 py-0.5 rounded text-xs ${canalInfo(m.canal).cls}`}>{canalInfo(m.canal).label}</span></td>
                    <td className="text-gray-300 max-w-md">{m.mensaje}</td>
                    <td className={m.acierto ? 'text-gray-300' : 'text-red-400'}>{INTENCION[m.intencion] ?? m.intencion}</td>
                    <td>
                      {m.a_humano
                        ? <span className="text-orange-300 text-xs">a un asesor</span>
                        : <span className={`px-2 py-0.5 rounded text-xs ${TEMP[m.temperatura] ?? ''}`}>{m.temperatura === 'caliente' && <Flame className="w-3 h-3 inline mr-0.5" />}{m.temperatura}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-xs text-gray-600 mt-3">{r.supuestos}</p>
          </div>
        </>
      )}
    </div>
  );
}
