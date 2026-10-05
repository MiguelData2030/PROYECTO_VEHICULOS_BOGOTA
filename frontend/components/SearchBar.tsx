'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, SlidersHorizontal } from 'lucide-react';
import { marcas } from '@/lib/data';

interface SearchBarProps {
  onSearch?: (filters: Record<string, string>) => void;
  compact?: boolean;
}

export default function SearchBar({ onSearch, compact = false }: SearchBarProps) {
  const router = useRouter();
  const [filters, setFilters] = useState({
    marca: '',
    modelo: '',
    anioMin: '',
    anioMax: '',
    precioMin: '',
    precioMax: '',
  });

  const handleChange = (key: string, value: string) => {
    const updated = { ...filters, [key]: value };
    setFilters(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (onSearch) {
      onSearch(filters);
      return;
    }

    // Build query params and navigate to catalogue
    const params = new URLSearchParams();
    if (filters.marca) params.set('marca', filters.marca);
    if (filters.anioMin) params.set('anio_min', filters.anioMin);
    if (filters.anioMax) params.set('anio_max', filters.anioMax);
    if (filters.precioMin) params.set('precio_min', filters.precioMin);
    if (filters.precioMax) params.set('precio_max', filters.precioMax);

    const qs = params.toString();
    router.push(`/catalogo${qs ? `?${qs}` : ''}`);
  };

  if (compact) {
    return (
      <form onSubmit={handleSubmit} className="flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[160px]">
          <select
            value={filters.marca}
            onChange={(e) => handleChange('marca', e.target.value)}
            className="select-field text-sm"
          >
            <option value="">Todas las marcas</option>
            {marcas.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[160px]">
          <input
            type="text"
            placeholder="Modelo..."
            value={filters.modelo}
            onChange={(e) => handleChange('modelo', e.target.value)}
            className="input-field text-sm"
          />
        </div>
        <div className="flex-1 min-w-[120px]">
          <select
            value={filters.anioMin}
            onChange={(e) => handleChange('anioMin', e.target.value)}
            className="select-field text-sm"
          >
            <option value="">Año desde</option>
            {Array.from({ length: 15 }, (_, i) => 2026 - i).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <div className="flex-1 min-w-[140px]">
          <select
            value={filters.precioMax}
            onChange={(e) => handleChange('precioMax', e.target.value)}
            className="select-field text-sm"
          >
            <option value="">Precio máx.</option>
            <option value="80000000">$80.000.000</option>
            <option value="100000000">$100.000.000</option>
            <option value="120000000">$120.000.000</option>
            <option value="150000000">$150.000.000</option>
            <option value="200000000">$200.000.000</option>
          </select>
        </div>
        <button type="submit" className="btn-primary flex items-center gap-2 text-sm">
          <Search className="w-4 h-4" />
          Buscar
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="card-elevated p-6">
      <div className="flex items-center gap-2 mb-4">
        <SlidersHorizontal className="w-5 h-5 text-primary" />
        <h3 className="text-white font-semibold">Búsqueda Rápida</h3>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Marca</label>
          <select
            value={filters.marca}
            onChange={(e) => handleChange('marca', e.target.value)}
            className="select-field text-sm"
          >
            <option value="">Todas</option>
            {marcas.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Modelo</label>
          <input
            type="text"
            placeholder="Ej: CX-5"
            value={filters.modelo}
            onChange={(e) => handleChange('modelo', e.target.value)}
            className="input-field text-sm"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Año desde</label>
          <select
            value={filters.anioMin}
            onChange={(e) => handleChange('anioMin', e.target.value)}
            className="select-field text-sm"
          >
            <option value="">Cualquiera</option>
            {Array.from({ length: 15 }, (_, i) => 2026 - i).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Año hasta</label>
          <select
            value={filters.anioMax}
            onChange={(e) => handleChange('anioMax', e.target.value)}
            className="select-field text-sm"
          >
            <option value="">Cualquiera</option>
            {Array.from({ length: 15 }, (_, i) => 2026 - i).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Precio máx.</label>
          <select
            value={filters.precioMax}
            onChange={(e) => handleChange('precioMax', e.target.value)}
            className="select-field text-sm"
          >
            <option value="">Sin límite</option>
            <option value="80000000">$80M</option>
            <option value="100000000">$100M</option>
            <option value="120000000">$120M</option>
            <option value="150000000">$150M</option>
            <option value="200000000">$200M</option>
          </select>
        </div>
        <div className="flex items-end">
          <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2 text-sm">
            <Search className="w-4 h-4" />
            Buscar
          </button>
        </div>
      </div>
    </form>
  );
}
