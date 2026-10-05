'use client';

import { Suspense, useState, useEffect, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { SlidersHorizontal, ArrowUpDown, Grid3X3, ChevronLeft, ChevronRight, Loader2 } from 'lucide-react';
import VehicleCard from '@/components/VehicleCard';
import { vehiculosPlaceholder, marcas, tiposVehiculo, transmisiones, combustibles, type Vehicle } from '@/lib/data';
import { fetchCatalogo, type CatalogoFilters } from '@/lib/api';

type SortOption = 'precio_asc' | 'precio_desc' | 'anio_desc' | 'km_asc';

const ITEMS_PER_PAGE = 9;

export default function CatalogoPage() {
  return (
    <Suspense fallback={
      <div className="pt-16 flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
      </div>
    }>
      <CatalogoContent />
    </Suspense>
  );
}

function CatalogoContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Initialize filters from URL query params
  const [filtraMarca, setFiltraMarca] = useState(searchParams.get('marca') || '');
  const [filtraTipo, setFiltraTipo] = useState(searchParams.get('tipo_vehiculo') || '');
  const [anioMin, setAnioMin] = useState(searchParams.get('anio_min') || '');
  const [anioMax, setAnioMax] = useState(searchParams.get('anio_max') || '');
  const [precioMin, setPrecioMin] = useState(searchParams.get('precio_min') || '');
  const [precioMax, setPrecioMax] = useState(searchParams.get('precio_max') || '');
  const [kmMax, setKmMax] = useState(searchParams.get('km_max') || '');
  const [transmision, setTransmision] = useState(searchParams.get('transmision') || '');
  const [combustible, setCombustible] = useState(searchParams.get('combustible') || '');
  const [sortBy, setSortBy] = useState<SortOption>('precio_desc');
  const [page, setPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  // Fetch vehicles from API
  const loadVehicles = useCallback(async () => {
    setLoading(true);
    try {
      const filters: CatalogoFilters = {};
      if (filtraMarca) filters.marca = filtraMarca;
      if (filtraTipo) filters.tipo_vehiculo = filtraTipo;
      if (anioMin) filters.anio_min = Number(anioMin);
      if (anioMax) filters.anio_max = Number(anioMax);
      if (precioMin) filters.precio_min = Number(precioMin);
      if (precioMax) filters.precio_max = Number(precioMax);
      if (kmMax) filters.km_max = Number(kmMax);

      const data = await fetchCatalogo(filters);
      setVehicles(data);
      setUsingFallback(false);
    } catch {
      // Fallback to placeholder data if backend is unreachable
      let result = [...vehiculosPlaceholder];
      if (filtraMarca) result = result.filter((v) => v.marca === filtraMarca);
      if (filtraTipo) result = result.filter((v) => v.tipo === filtraTipo);
      if (anioMin) result = result.filter((v) => v.anio >= Number(anioMin));
      if (anioMax) result = result.filter((v) => v.anio <= Number(anioMax));
      if (precioMin) result = result.filter((v) => v.precio >= Number(precioMin));
      if (precioMax) result = result.filter((v) => v.precio <= Number(precioMax));
      if (kmMax) result = result.filter((v) => v.kilometraje <= Number(kmMax));
      if (transmision) result = result.filter((v) => v.transmision === transmision);
      if (combustible) result = result.filter((v) => v.combustible === combustible);
      setVehicles(result);
      setUsingFallback(true);
    } finally {
      setLoading(false);
    }
  }, [filtraMarca, filtraTipo, anioMin, anioMax, precioMin, precioMax, kmMax, transmision, combustible]);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    if (filtraMarca) params.set('marca', filtraMarca);
    if (filtraTipo) params.set('tipo_vehiculo', filtraTipo);
    if (anioMin) params.set('anio_min', anioMin);
    if (anioMax) params.set('anio_max', anioMax);
    if (precioMin) params.set('precio_min', precioMin);
    if (precioMax) params.set('precio_max', precioMax);
    if (kmMax) params.set('km_max', kmMax);

    const qs = params.toString();
    router.replace(`/catalogo${qs ? `?${qs}` : ''}`, { scroll: false });
  }, [filtraMarca, filtraTipo, anioMin, anioMax, precioMin, precioMax, kmMax, router]);

  // Client-side sort (backend doesn't have sort param for catalogo)
  const sorted = [...vehicles].sort((a, b) => {
    switch (sortBy) {
      case 'precio_asc': return a.precio - b.precio;
      case 'precio_desc': return b.precio - a.precio;
      case 'anio_desc': return b.anio - a.anio;
      case 'km_asc': return a.kilometraje - b.kilometraje;
      default: return 0;
    }
  });

  // Client-side filter for transmision/combustible (not in backend catalogo endpoint)
  const filtered = sorted.filter((v) => {
    if (transmision && v.transmision !== transmision) return false;
    if (combustible && v.combustible !== combustible) return false;
    return true;
  });

  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
  const paginated = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  const clearFilters = () => {
    setFiltraMarca('');
    setFiltraTipo('');
    setAnioMin('');
    setAnioMax('');
    setPrecioMin('');
    setPrecioMax('');
    setKmMax('');
    setTransmision('');
    setCombustible('');
    setPage(1);
  };

  return (
    <div className="pt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="section-title">Catálogo de Vehículos</h1>
          <p className="section-subtitle">
            {loading
              ? 'Cargando vehículos...'
              : `${filtered.length} vehículos ${usingFallback ? '(datos de demostración)' : 'disponibles'}`}
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar Filters */}
          <aside className={`lg:w-72 flex-shrink-0 ${showFilters ? 'block' : 'hidden lg:block'}`}>
            <div className="card-elevated p-5 sticky top-24 space-y-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <SlidersHorizontal className="w-4 h-4 text-primary" />
                  <h3 className="text-white font-semibold">Filtros</h3>
                </div>
                <button onClick={clearFilters} className="text-xs text-primary hover:text-primary-light transition-colors">
                  Limpiar
                </button>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Marca</label>
                <select value={filtraMarca} onChange={(e) => { setFiltraMarca(e.target.value); setPage(1); }} className="select-field text-sm">
                  <option value="">Todas</option>
                  {marcas.map((m) => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Tipo</label>
                <select value={filtraTipo} onChange={(e) => { setFiltraTipo(e.target.value); setPage(1); }} className="select-field text-sm">
                  <option value="">Todos</option>
                  {tiposVehiculo.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Año desde</label>
                  <select value={anioMin} onChange={(e) => { setAnioMin(e.target.value); setPage(1); }} className="select-field text-sm">
                    <option value="">Min</option>
                    {Array.from({ length: 15 }, (_, i) => 2026 - i).map((y) => <option key={y} value={y}>{y}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Año hasta</label>
                  <select value={anioMax} onChange={(e) => { setAnioMax(e.target.value); setPage(1); }} className="select-field text-sm">
                    <option value="">Max</option>
                    {Array.from({ length: 15 }, (_, i) => 2026 - i).map((y) => <option key={y} value={y}>{y}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Precio mín.</label>
                  <select value={precioMin} onChange={(e) => { setPrecioMin(e.target.value); setPage(1); }} className="select-field text-sm">
                    <option value="">Min</option>
                    <option value="50000000">$50M</option>
                    <option value="80000000">$80M</option>
                    <option value="100000000">$100M</option>
                    <option value="120000000">$120M</option>
                    <option value="150000000">$150M</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1.5">Precio máx.</label>
                  <select value={precioMax} onChange={(e) => { setPrecioMax(e.target.value); setPage(1); }} className="select-field text-sm">
                    <option value="">Max</option>
                    <option value="80000000">$80M</option>
                    <option value="100000000">$100M</option>
                    <option value="120000000">$120M</option>
                    <option value="150000000">$150M</option>
                    <option value="200000000">$200M</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Kilometraje máx.</label>
                <select value={kmMax} onChange={(e) => { setKmMax(e.target.value); setPage(1); }} className="select-field text-sm">
                  <option value="">Sin límite</option>
                  <option value="10000">10,000 km</option>
                  <option value="20000">20,000 km</option>
                  <option value="30000">30,000 km</option>
                  <option value="50000">50,000 km</option>
                  <option value="80000">80,000 km</option>
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Transmisión</label>
                <select value={transmision} onChange={(e) => { setTransmision(e.target.value); setPage(1); }} className="select-field text-sm">
                  <option value="">Todas</option>
                  {transmisiones.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Combustible</label>
                <select value={combustible} onChange={(e) => { setCombustible(e.target.value); setPage(1); }} className="select-field text-sm">
                  <option value="">Todos</option>
                  {combustibles.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <div className="flex-1">
            {/* Toolbar */}
            <div className="flex items-center justify-between mb-6 gap-4">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="lg:hidden btn-ghost flex items-center gap-2 text-sm"
              >
                <SlidersHorizontal className="w-4 h-4" />
                Filtros
              </button>
              <p className="text-gray-400 text-sm hidden sm:block">{filtered.length} vehículos encontrados</p>
              <div className="flex items-center gap-2">
                <ArrowUpDown className="w-4 h-4 text-gray-400" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as SortOption)}
                  className="select-field text-sm w-auto pr-8"
                >
                  <option value="precio_desc">Mayor precio</option>
                  <option value="precio_asc">Menor precio</option>
                  <option value="anio_desc">Más recientes</option>
                  <option value="km_asc">Menor kilometraje</option>
                </select>
              </div>
            </div>

            {/* Loading state */}
            {loading ? (
              <div className="flex flex-col items-center justify-center py-20">
                <Loader2 className="w-10 h-10 text-primary animate-spin mb-4" />
                <p className="text-gray-400">Cargando vehículos...</p>
              </div>
            ) : paginated.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-6">
                {paginated.map((v) => (
                  <VehicleCard key={v.id} vehicle={v} />
                ))}
              </div>
            ) : (
              <div className="text-center py-20">
                <Grid3X3 className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 text-lg">No se encontraron vehículos con estos filtros</p>
                <button onClick={clearFilters} className="text-primary hover:text-primary-light text-sm mt-2 transition-colors">
                  Limpiar filtros
                </button>
              </div>
            )}

            {/* Pagination */}
            {!loading && totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-10">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-lg border border-border text-gray-400 hover:text-white hover:border-primary/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-10 h-10 rounded-lg text-sm font-medium transition-all ${
                      page === p
                        ? 'bg-primary text-dark'
                        : 'border border-border text-gray-400 hover:text-white hover:border-primary/30'
                    }`}
                  >
                    {p}
                  </button>
                ))}
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="p-2 rounded-lg border border-border text-gray-400 hover:text-white hover:border-primary/30 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
