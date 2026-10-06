'use client';

import { useEffect, useState } from 'react';
import { Loader2, Users, Eye, MessageCircle, DollarSign, Heart, Share2, Bookmark, Lightbulb, Receipt } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, BarChart, Bar,
} from 'recharts';
import toast from 'react-hot-toast';
import AdminShell from '@/components/AdminShell';
import { formatCOP, formatCOPCompact, formatNumber } from '@/lib/data';
import { canalInfo } from '@/lib/canales';
import { fetchRedes, apiErrorMessage, type ResumenRedes } from '@/lib/api-admin';

const FORMATO: Record<string, string> = {
  reel: 'Reel', carrusel: 'Carrusel', historia: 'Historia', video: 'Video', post: 'Post',
};

function compacto(n: number) {
  return n >= 1_000_000 ? `${(n / 1e6).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);
}

export default function RedesPage() {
  const [dias, setDias] = useState(90);
  const [data, setData] = useState<ResumenRedes | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchRedes(dias)
      .then(setData)
      .catch((e) => toast.error(apiErrorMessage(e, 'No se pudieron cargar las redes')))
      .finally(() => setLoading(false));
  }, [dias]);

  const vacio = data && data.redes.length === 0;
  const serie = (data?.serie ?? []).map((p) => ({ ...p, dia: new Date(`${p.fecha}T12:00:00`).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' }) }));
  const mejorFormato = data?.rendimiento_formato[0];
  const mejorRed = data ? [...data.redes].sort((a, b) => b.ventas - a.ventas)[0] : null;
  const masBarata = data ? data.redes.filter((r) => r.costo_por_lead).sort((a, b) => (a.costo_por_lead ?? 0) - (b.costo_por_lead ?? 0))[0] : null;

  return (
    <AdminShell
      title="Redes sociales"
      subtitle="Cómo crecen las redes y cuántos clientes y ventas traen"
      actions={
        <select value={dias} onChange={(e) => setDias(Number(e.target.value))} className="select-field py-2 w-40">
          <option value={30}>Últimos 30 días</option>
          <option value={60}>Últimos 60 días</option>
          <option value={90}>Últimos 90 días</option>
        </select>
      }
    >
      {loading ? (
        <div className="flex justify-center py-24"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>
      ) : !data || vacio ? (
        <div className="card p-12 text-center text-gray-500">
          <Share2 className="w-10 h-10 mx-auto mb-3" />
          Aún no hay métricas de redes. Carga la demo desde el Dashboard para ver un ejemplo, o conecta tus cuentas (próxima fase).
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <Kpi icon={Users} label="Seguidores totales" value={formatNumber(data.totales.seguidores)} sub={`+${formatNumber(data.totales.crecimiento)} en ${dias} días`} accent="text-green-400" />
            <Kpi icon={Eye} label="Alcance" value={compacto(data.totales.alcance)} sub="Personas alcanzadas" />
            <Kpi icon={MessageCircle} label="Leads de redes" value={formatNumber(data.totales.leads)} sub={data.totales.costo_por_lead ? `Costo por lead ${formatCOP(data.totales.costo_por_lead)}` : undefined} accent="text-primary" />
            <Kpi icon={Receipt} label="Ventas originadas en redes" value={String(data.totales.ventas_desde_redes)} sub={`${formatCOPCompact(data.totales.valor_ventas_redes)} vendidos`} accent="text-green-400" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
            {data.redes.map((r) => {
              const c = canalInfo(r.red);
              return (
                <div key={r.red} className="card p-4" style={{ borderTop: `3px solid ${c.color}` }}>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-xs px-2 py-0.5 rounded ${c.cls}`}>{c.label}</span>
                    <span className="text-green-400 text-xs font-medium">+{r.crecimiento_pct}%</span>
                  </div>
                  <p className="text-2xl font-bold text-white">{formatNumber(r.seguidores)}</p>
                  <p className="text-gray-500 text-xs mb-3">{r.red === 'whatsapp' ? 'contactos en difusión' : 'seguidores'}</p>
                  <div className="grid grid-cols-2 gap-y-1 text-xs">
                    <span className="text-gray-500">Engagement</span><span className="text-gray-200 text-right">{r.engagement_pct}%</span>
                    <span className="text-gray-500">Mensajes</span><span className="text-gray-200 text-right">{formatNumber(r.mensajes)}</span>
                    <span className="text-gray-500">Leads</span><span className="text-gray-200 text-right">{formatNumber(r.leads)}</span>
                    <span className="text-gray-500">Costo por lead</span><span className="text-gray-200 text-right">{r.costo_por_lead ? formatCOP(r.costo_por_lead) : 'Orgánico'}</span>
                    <span className="text-gray-500">Ventas</span><span className="text-primary text-right font-medium">{r.ventas} · {formatCOPCompact(r.valor_ventas)}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="card p-5 lg:col-span-2">
              <h3 className="text-white font-semibold mb-4">Crecimiento de seguidores</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={serie}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                  <XAxis dataKey="dia" tick={{ fill: '#9ca3af', fontSize: 11 }} interval={Math.ceil(serie.length / 8)} />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={compacto} />
                  <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8 }} labelStyle={{ color: '#fff' }} formatter={(v: number) => formatNumber(v)} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {data.redes.map((r) => (
                    <Line key={r.red} type="monotone" dataKey={r.red} name={canalInfo(r.red).label} stroke={canalInfo(r.red).color} dot={false} strokeWidth={2} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="card p-5">
              <h3 className="text-white font-semibold mb-4 flex items-center gap-2"><Lightbulb className="w-4 h-4 text-primary" /> Lectura rápida</h3>
              <ul className="space-y-3 text-sm text-gray-300">
                {mejorRed && <li>• <b className="text-white">{canalInfo(mejorRed.red).label}</b> es la red que más ventas trajo ({mejorRed.ventas}, {formatCOPCompact(mejorRed.valor_ventas)}).</li>}
                {mejorFormato && <li>• El formato que más clientes genera es <b className="text-white">{FORMATO[mejorFormato.formato.split(':')[1]] ?? mejorFormato.formato} en {canalInfo(mejorFormato.formato.split(':')[0]).label}</b>: {mejorFormato.leads_por_publicacion} leads por publicación.</li>}
                {masBarata && <li>• La pauta más eficiente es <b className="text-white">{canalInfo(masBarata.red).label}</b> ({formatCOP(masBarata.costo_por_lead ?? 0)} por lead).</li>}
                <li>• Publicar el carro el mismo día que llega y responder DMs en menos de 1 hora son los dos hábitos que más mueven estas cifras.</li>
              </ul>
            </div>
          </div>

          <div className="card p-5 mb-8">
            <h3 className="text-white font-semibold mb-4">Leads por día</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={serie}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="dia" tick={{ fill: '#9ca3af', fontSize: 11 }} interval={Math.ceil(serie.length / 8)} />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
                <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8 }} labelStyle={{ color: '#fff' }} />
                <Bar dataKey="leads" name="Leads" fill="#d4a843" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <h3 className="text-white font-semibold mb-4">Publicaciones que más venden</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {data.top_publicaciones.map((p) => {
              const c = canalInfo(p.red);
              return (
                <div key={p.id} className="card overflow-hidden">
                  <div className="relative aspect-[4/3] bg-dark">
                    {p.imagen && <img src={p.imagen} alt="" className="w-full h-full object-cover" />}
                    <span className={`absolute top-2 left-2 text-[10px] px-1.5 py-0.5 rounded bg-black/70 ${c.cls}`}>{c.label} · {FORMATO[p.tipo] ?? p.tipo}</span>
                    {p.vehiculo_estado === 'vendido' && <span className="absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded bg-green-600 text-white font-semibold">VENDIDO</span>}
                  </div>
                  <div className="p-3">
                    <p className="text-white text-sm leading-tight line-clamp-2 min-h-[2.5rem]">{p.titulo}</p>
                    <p className="text-gray-500 text-xs mt-1">{new Date(`${p.fecha}T12:00:00`).toLocaleDateString('es-CO', { day: 'numeric', month: 'short' })} · {compacto(p.alcance)} alcance</p>
                    <div className="flex justify-between text-xs text-gray-400 mt-2">
                      <span className="flex items-center gap-1"><Heart className="w-3 h-3" />{compacto(p.me_gusta)}</span>
                      <span className="flex items-center gap-1"><Share2 className="w-3 h-3" />{compacto(p.compartidos)}</span>
                      <span className="flex items-center gap-1"><Bookmark className="w-3 h-3" />{compacto(p.guardados)}</span>
                      <span className="flex items-center gap-1 text-primary font-medium"><DollarSign className="w-3 h-3" />{p.leads} leads</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="card p-5 overflow-x-auto">
            <h3 className="text-white font-semibold mb-4">Rendimiento por formato</h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-xs uppercase border-b border-border">
                  <th className="text-left py-2">Formato</th><th className="text-right py-2">Publicaciones</th>
                  <th className="text-right py-2">Alcance</th><th className="text-right py-2">Leads</th><th className="text-right py-2">Leads / publicación</th>
                </tr>
              </thead>
              <tbody>
                {data.rendimiento_formato.map((f) => {
                  const [red, tipo] = f.formato.split(':');
                  return (
                    <tr key={f.formato} className="border-b border-border/50">
                      <td className="py-2 text-gray-200">{FORMATO[tipo] ?? tipo} · {canalInfo(red).label}</td>
                      <td className="py-2 text-right text-gray-400">{f.publicaciones}</td>
                      <td className="py-2 text-right text-gray-400">{compacto(f.alcance)}</td>
                      <td className="py-2 text-right text-gray-200">{f.leads}</td>
                      <td className="py-2 text-right text-primary font-medium">{f.leads_por_publicacion}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="text-gray-600 text-xs mt-3">Datos de demostración. En producción se conectan Meta (Instagram/Facebook), TikTok y WhatsApp Business por API.</p>
          </div>
        </>
      )}
    </AdminShell>
  );
}

function Kpi({ icon: Icon, label, value, sub, accent = 'text-white' }: {
  icon: typeof Users; label: string; value: string; sub?: string; accent?: string;
}) {
  return (
    <div className="card p-4">
      <Icon className="w-4 h-4 text-primary mb-2" />
      <p className={`text-xl font-bold ${accent}`}>{value}</p>
      <p className="text-gray-400 text-xs">{label}</p>
      {sub && <p className="text-gray-600 text-xs mt-0.5">{sub}</p>}
    </div>
  );
}
