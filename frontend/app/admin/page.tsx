'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  BarChart3, Car, DollarSign, TrendingUp, Package, Clock,
  Target, Zap, RefreshCw, Loader2, AlertCircle, ChevronRight, Receipt, FlaskConical, Trash2,
} from 'lucide-react';
import AdminShell from '@/components/AdminShell';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, ComposedChart, Line, Legend,
} from 'recharts';
import { formatCOP, formatCOPCompact, formatNumber } from '@/lib/data';
import {
  fetchEstadisticas, fetchInventario, fetchOportunidadesTop, triggerScraping,
  fetchDashboardKPIs, fetchDemoEstado, cargarDemo, borrarDemo, apiErrorMessage,
  type Estadisticas, type VehiculoAdmin, type Oportunidad, type DashboardKPIs, type DemoEstado,
} from '@/lib/api-admin';
import toast from 'react-hot-toast';

const COLORS = ['#d4a843', '#e8c567', '#b08930', '#8a6d24', '#f0d78c', '#6b5320'];

export default function AdminDashboard() {
  const [stats, setStats] = useState<Estadisticas | null>(null);
  const [inventario, setInventario] = useState<VehiculoAdmin[]>([]);
  const [oportunidades, setOportunidades] = useState<Oportunidad[]>([]);
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null);
  const [demo, setDemo] = useState<DemoEstado | null>(null);
  const [demoBusy, setDemoBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [s, inv, ops, k, d] = await Promise.all([
        fetchEstadisticas(),
        fetchInventario(),
        fetchOportunidadesTop(),
        fetchDashboardKPIs(),
        fetchDemoEstado(),
      ]);
      setStats(s);
      setInventario(inv);
      setOportunidades(ops);
      setKpis(k);
      setDemo(d);
    } catch {
      toast.error('Error cargando datos del dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const toggleDemo = async () => {
    const borrar = demo?.cargado;
    if (borrar && !confirm('¿Borrar todos los datos de demostración? Tus datos reales no se tocan.')) return;
    setDemoBusy(true);
    try {
      if (borrar) {
        await borrarDemo();
        toast.success('Datos de demostración eliminados');
      } else {
        const r = await cargarDemo();
        toast.success(`Demo cargada: ${r.vehiculos} vehículos, ${r.transacciones} transacciones`);
      }
      await loadData();
    } catch (e) {
      toast.error(apiErrorMessage(e, 'No se pudo completar la operación'));
    } finally {
      setDemoBusy(false);
    }
  };

  const handleScraping = async () => {
    setScraping(true);
    const ok = await triggerScraping();
    if (ok) {
      toast.success('Scraping iniciado. Los resultados aparecerán en minutos.');
    } else {
      toast.error('No se pudo iniciar el scraping. Verifica que el backend esté corriendo.');
    }
    setScraping(false);
  };

  const headerActions = (
    <>
      <button
        onClick={handleScraping}
        disabled={scraping}
        className="btn-secondary flex items-center gap-2 text-sm"
      >
        {scraping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
        {scraping ? 'Escaneando...' : 'Ejecutar Scraping'}
      </button>
      <button onClick={loadData} className="btn-ghost p-2" title="Refrescar">
        <RefreshCw className="w-4 h-4" />
      </button>
    </>
  );

  if (loading) {
    return (
      <AdminShell title="Dashboard" subtitle="Panel de administración AutoNegocio" actions={headerActions}>
        <div className="flex items-center justify-center min-h-[50vh]">
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
        </div>
      </AdminShell>
    );
  }

  const disponibles = stats?.por_estado?.disponible ?? 0;
  const reservados = stats?.por_estado?.reservado ?? 0;
  const vendidos = stats?.por_estado?.vendido ?? 0;

  // Inventory charts: only cars still in stock
  const enStock = inventario.filter((v) => v.estado !== 'vendido');
  const contar = (key: (v: VehiculoAdmin) => string) =>
    Object.entries(enStock.reduce<Record<string, number>>((acc, v) => {
      acc[key(v)] = (acc[key(v)] ?? 0) + 1;
      return acc;
    }, {})).sort(([, a], [, b]) => b - a).map(([name, value]) => ({ name, value }));
  const marcaData = contar((v) => v.marca).slice(0, 6);
  const tipoData = contar((v) => v.tipo_vehiculo);

  const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const mesesData = (kpis?.meses ?? []).map((m) => ({
    mes: `${MESES[Number(m.mes.slice(5)) - 1]} ${m.mes.slice(2, 4)}`,
    ventas: m.ventas,
    ganancia: Math.round(m.ganancia / 1e6),
  }));

  const topInventario = inventario
    .filter((v) => v.estado === 'disponible')
    .sort((a, b) => (b.score_oportunidad ?? 0) - (a.score_oportunidad ?? 0))
    .slice(0, 8);

  return (
    <AdminShell title="Dashboard" subtitle="Panel de administración AutoNegocio" actions={headerActions}>
        {/* Business KPIs (last 12 months) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KPICard
            icon={Receipt}
            label="Ventas (12 meses)"
            value={formatNumber(kpis?.ventas_12m ?? 0)}
            sub={`${kpis?.ventas_mes_actual ?? 0} este mes`}
            color="text-primary"
          />
          <KPICard
            icon={TrendingUp}
            label="Ganancia neta (12 meses)"
            value={formatCOPCompact(kpis?.ganancia_12m ?? 0)}
            sub={kpis?.margen_promedio_pct != null ? `Margen promedio ${kpis.margen_promedio_pct}%` : undefined}
            color="text-green-400"
          />
          <KPICard
            icon={DollarSign}
            label="Ingresos (12 meses)"
            value={formatCOPCompact(kpis?.ingresos_12m ?? 0)}
            sub={kpis?.ticket_promedio ? `Ticket promedio ${formatCOPCompact(kpis.ticket_promedio)}` : undefined}
            color="text-blue-400"
          />
          <KPICard
            icon={Clock}
            label="Días promedio para vender"
            value={kpis?.dias_promedio_venta != null ? `${kpis.dias_promedio_venta.toFixed(0)} días` : 'N/A'}
            sub="Meta: menos de 30"
            color="text-purple-400"
          />
        </div>

        {/* Inventory KPIs */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KPICard icon={Car} label="Vehículos en inventario" value={formatNumber(kpis?.vehiculos_en_inventario ?? enStock.length)} sub={`${disponibles} disponibles`} color="text-primary" />
          <KPICard icon={Package} label="Capital invertido" value={formatCOPCompact(kpis?.capital_invertido ?? 0)} sub="Costo de compra del stock" color="text-yellow-400" />
          <KPICard icon={DollarSign} label="Valor de venta del stock" value={formatCOPCompact(kpis?.valor_inventario_venta ?? 0)} sub={kpis && kpis.capital_invertido ? `Utilidad potencial ${formatCOPCompact(kpis.valor_inventario_venta - kpis.capital_invertido)}` : undefined} color="text-green-400" />
          <KPICard icon={Target} label="Score promedio" value={stats?.score_oportunidad_promedio ? stats.score_oportunidad_promedio.toFixed(0) + '/100' : 'N/A'} sub="Calidad de compra" color="text-blue-400" />
        </div>

        {/* Monthly performance */}
        <div className="card p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              Ventas y ganancia por mes
            </h3>
            <Link href="/admin/ventas" className="text-primary text-sm flex items-center gap-1 hover:underline">
              Ver ventas <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          {mesesData.some((m) => m.ventas > 0) ? (
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={mesesData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="mes" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 12 }} allowDecimals={false} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: '#9ca3af', fontSize: 12 }} unit="M" />
                <Tooltip
                  contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8 }}
                  labelStyle={{ color: '#fff' }}
                  formatter={(value: number, name: string) => (name === 'Ventas' ? [value, name] : [`$${value}M`, name])}
                />
                <Legend wrapperStyle={{ color: '#9ca3af', fontSize: 12 }} />
                <Bar yAxisId="left" dataKey="ventas" name="Ventas" fill="#d4a843" radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" type="monotone" dataKey="ganancia" name="Ganancia neta" stroke="#4ade80" strokeWidth={2} dot={{ r: 3 }} />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState text="Aún no hay ventas registradas" />
          )}
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* By Brand */}
          <div className="card p-6">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              Stock por Marca
            </h3>
            {marcaData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={marcaData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                  <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8 }}
                    labelStyle={{ color: '#fff' }}
                  />
                  <Bar dataKey="value" fill="#d4a843" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState text="Sin datos de marcas" />
            )}
          </div>

          {/* By Type */}
          <div className="card p-6">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Package className="w-4 h-4 text-primary" />
              Stock por Tipo
            </h3>
            {tipoData.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={tipoData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {tipoData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: 8 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState text="Sin datos de tipos" />
            )}
          </div>
        </div>

        {/* Status Summary */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="card p-4 text-center">
            <div className="w-3 h-3 rounded-full bg-green-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{disponibles}</p>
            <p className="text-gray-400 text-xs">Disponibles</p>
          </div>
          <div className="card p-4 text-center">
            <div className="w-3 h-3 rounded-full bg-yellow-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{reservados}</p>
            <p className="text-gray-400 text-xs">Reservados</p>
          </div>
          <div className="card p-4 text-center">
            <div className="w-3 h-3 rounded-full bg-red-500 mx-auto mb-2" />
            <p className="text-2xl font-bold text-white">{vendidos}</p>
            <p className="text-gray-400 text-xs">Vendidos</p>
          </div>
        </div>

        {/* Inventory Table */}
        <div className="card p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Car className="w-4 h-4 text-primary" />
              Inventario Disponible (Top por Score)
            </h3>
            <Link href="/admin/inventario" className="text-primary text-sm flex items-center gap-1 hover:underline">
              Gestionar inventario <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          {topInventario.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-gray-500 text-xs uppercase">
                    <th className="text-left py-3 px-2">Vehículo</th>
                    <th className="text-right py-3 px-2">Compra</th>
                    <th className="text-right py-3 px-2">Venta</th>
                    <th className="text-right py-3 px-2">Margen</th>
                    <th className="text-center py-3 px-2">Score</th>
                    <th className="text-center py-3 px-2">Fuente</th>
                  </tr>
                </thead>
                <tbody>
                  {topInventario.map((v) => {
                    const margen = v.precio_compra && v.precio_venta
                      ? ((v.precio_venta - v.precio_compra) / v.precio_compra * 100).toFixed(1)
                      : null;
                    return (
                      <tr key={v.id} className="border-b border-border/50 hover:bg-surface-light transition-colors">
                        <td className="py-3 px-2">
                          <Link href={`/catalogo/vehiculo?id=${v.id}`} className="hover:text-primary transition-colors">
                            <p className="text-white font-medium">{v.marca} {v.modelo}</p>
                            <p className="text-gray-500 text-xs">{v.año} · {formatNumber(v.kilometraje)} km</p>
                          </Link>
                        </td>
                        <td className="text-right py-3 px-2 text-gray-400">
                          {v.precio_compra ? formatCOP(v.precio_compra) : '-'}
                        </td>
                        <td className="text-right py-3 px-2 text-white font-medium">
                          {v.precio_venta ? formatCOP(v.precio_venta) : '-'}
                        </td>
                        <td className="text-right py-3 px-2">
                          {margen ? (
                            <span className={`font-medium ${Number(margen) >= 15 ? 'text-green-400' : 'text-yellow-400'}`}>
                              {margen}%
                            </span>
                          ) : '-'}
                        </td>
                        <td className="text-center py-3 px-2">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            (v.score_oportunidad ?? 0) >= 75
                              ? 'bg-green-500/10 text-green-400'
                              : (v.score_oportunidad ?? 0) >= 60
                              ? 'bg-yellow-500/10 text-yellow-400'
                              : 'bg-gray-500/10 text-gray-400'
                          }`}>
                            {v.score_oportunidad?.toFixed(0) ?? '-'}
                          </span>
                        </td>
                        <td className="text-center py-3 px-2">
                          <span className="text-gray-500 text-xs capitalize">{v.fuente ?? '-'}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState text="No hay vehículos en inventario" />
          )}
        </div>

        {/* Oportunidades */}
        {oportunidades.length > 0 && (
          <div className="card p-6">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Target className="w-4 h-4 text-primary" />
              Top Oportunidades de Compra
            </h3>
            <Link href="/admin/oportunidades" className="text-primary text-sm flex items-center gap-1 mb-4 hover:underline">
              Ver todas <ChevronRight className="w-4 h-4" />
            </Link>
            <div className="space-y-3">
              {oportunidades.slice(0, 5).map((op) => (
                <div key={op.id} className="flex items-center justify-between p-3 bg-dark rounded-xl">
                  <div>
                    <p className="text-white font-medium">{op.marca} {op.modelo} {op.año}</p>
                    <p className="text-gray-500 text-xs capitalize">{op.plataforma} · {op.ubicacion ?? '-'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-primary font-medium">{formatCOP(op.precio_publicado)}</p>
                    <span className={`text-xs font-medium ${
                      (op.score ?? 0) >= 75 ? 'text-green-400' : 'text-yellow-400'
                    }`}>
                      Score: {op.score?.toFixed(0) ?? '-'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      {/* Demo data */}
      <div className="card p-6 mt-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <FlaskConical className="w-5 h-5 text-primary mt-0.5" />
          <div>
            <p className="text-white font-semibold">Datos de demostración</p>
            <p className="text-gray-400 text-sm">
              {demo?.cargado
                ? `Cargados: ${demo.vehiculos} vehículos, ${demo.clientes} clientes y ${demo.transacciones} transacciones simuladas. Se ven en la web pública.`
                : 'Simula un año de operación (unos 95 vehículos con fotos, ventas, clientes y leads) para probar todo el sistema. Se borran con un clic.'}
            </p>
          </div>
        </div>
        <button
          onClick={toggleDemo}
          disabled={demoBusy}
          className={`${demo?.cargado ? 'btn-ghost text-red-400 border border-red-500/30' : 'btn-primary'} flex items-center gap-2 text-sm whitespace-nowrap disabled:opacity-50`}
        >
          {demoBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : demo?.cargado ? <Trash2 className="w-4 h-4" /> : <FlaskConical className="w-4 h-4" />}
          {demo?.cargado ? 'Borrar demo' : 'Cargar demo'}
        </button>
      </div>
    </AdminShell>
  );
}

function KPICard({ icon: Icon, label, value, sub, color }: {
  icon: typeof Car;
  label: string;
  value: string;
  sub?: string;
  color: string;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-xl bg-surface-light flex items-center justify-center ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <p className="text-xl sm:text-2xl font-bold text-white mb-0.5 break-words">{value}</p>
      <p className="text-gray-500 text-xs">{label}</p>
      {sub && <p className="text-gray-600 text-xs mt-1">{sub}</p>}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex items-center justify-center h-48 text-gray-600">
      <div className="text-center">
        <AlertCircle className="w-8 h-8 mx-auto mb-2" />
        <p className="text-sm">{text}</p>
      </div>
    </div>
  );
}
