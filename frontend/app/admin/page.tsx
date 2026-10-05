'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  BarChart3, Car, DollarSign, TrendingUp, Package, Clock,
  Target, Zap, RefreshCw, Loader2, AlertCircle, ChevronRight,
} from 'lucide-react';
import AdminShell from '@/components/AdminShell';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';
import { formatCOP, formatNumber } from '@/lib/data';
import {
  fetchEstadisticas, fetchInventario, fetchOportunidadesTop, triggerScraping,
  type Estadisticas, type VehiculoAdmin, type Oportunidad,
} from '@/lib/api-admin';
import toast from 'react-hot-toast';

const COLORS = ['#d4a843', '#e8c567', '#b08930', '#8a6d24', '#f0d78c', '#6b5320'];

export default function AdminDashboard() {
  const [stats, setStats] = useState<Estadisticas | null>(null);
  const [inventario, setInventario] = useState<VehiculoAdmin[]>([]);
  const [oportunidades, setOportunidades] = useState<Oportunidad[]>([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [s, inv, ops] = await Promise.all([
        fetchEstadisticas(),
        fetchInventario(),
        fetchOportunidadesTop(),
      ]);
      setStats(s);
      setInventario(inv);
      setOportunidades(ops);
    } catch {
      toast.error('Error cargando datos del dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

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

  const marcaData = stats
    ? Object.entries(stats.por_marca)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 6)
        .map(([name, value]) => ({ name, value }))
    : [];

  const tipoData = stats
    ? Object.entries(stats.por_tipo)
        .sort(([, a], [, b]) => b - a)
        .map(([name, value]) => ({ name, value }))
    : [];

  const topInventario = inventario
    .filter((v) => v.estado === 'disponible')
    .sort((a, b) => (b.score_oportunidad ?? 0) - (a.score_oportunidad ?? 0))
    .slice(0, 8);

  return (
    <AdminShell title="Dashboard" subtitle="Panel de administración AutoNegocio" actions={headerActions}>
        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KPICard
            icon={Car}
            label="Total Vehículos"
            value={stats?.total?.toString() ?? '0'}
            sub={`${disponibles} disponibles`}
            color="text-primary"
          />
          <KPICard
            icon={DollarSign}
            label="Valor Inventario"
            value={formatCOP(stats?.valor_inventario_venta_cop ?? 0)}
            sub={stats?.valor_inventario_compra_cop ? `Costo: ${formatCOP(stats.valor_inventario_compra_cop)}` : undefined}
            color="text-green-400"
          />
          <KPICard
            icon={TrendingUp}
            label="Margen Promedio"
            value={stats?.margen_promedio_pct ? `${stats.margen_promedio_pct.toFixed(1)}%` : 'N/A'}
            sub={stats?.margen_promedio_cop ? formatCOP(stats.margen_promedio_cop) + '/vehículo' : undefined}
            color="text-blue-400"
          />
          <KPICard
            icon={Target}
            label="Score Promedio"
            value={stats?.score_oportunidad_promedio ? stats.score_oportunidad_promedio.toFixed(0) + '/100' : 'N/A'}
            sub="Oportunidad de compra"
            color="text-purple-400"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* By Brand */}
          <div className="card p-6">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-primary" />
              Inventario por Marca
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
              Inventario por Tipo
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
                          <Link href={`/catalogo/${v.id}`} className="hover:text-primary transition-colors">
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
      <p className="text-2xl font-bold text-white mb-0.5">{value}</p>
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
