'use client';

import Link from 'next/link';
import { MapPin, Gauge, Fuel, Settings2, Calendar } from 'lucide-react';
import { Vehicle, formatCOP, formatNumber } from '@/lib/data';

interface VehicleCardProps {
  vehicle: Vehicle;
}

export default function VehicleCard({ vehicle }: VehicleCardProps) {
  return (
    <Link href={`/catalogo/${vehicle.id}`} className="card group cursor-pointer">
      {/* Image */}
      <div className="relative aspect-[16/10] bg-dark-50 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-t from-dark/80 via-transparent to-transparent z-10" />
        {vehicle.imagen && vehicle.imagen !== '/placeholder-car.jpg' ? (
          <img
            src={vehicle.imagen.startsWith('http') ? vehicle.imagen : `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}${vehicle.imagen}`}
            alt={`${vehicle.marca} ${vehicle.modelo}`}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-surface-light to-dark flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-2 rounded-full bg-border/50 flex items-center justify-center">
                <Settings2 className="w-8 h-8 text-gray-600" />
              </div>
              <p className="text-gray-600 text-xs">{vehicle.marca} {vehicle.modelo}</p>
            </div>
          </div>
        )}
        {/* Status Badge */}
        {vehicle.estado === 'Reservado' && (
          <span className="absolute top-3 left-3 z-20 badge-warning">Reservado</span>
        )}
        {vehicle.estado === 'Vendido' && (
          <span className="absolute top-3 left-3 z-20 badge-danger">Vendido</span>
        )}
        {/* Year Badge */}
        <span className="absolute top-3 right-3 z-20 badge-primary">
          <Calendar className="w-3 h-3 mr-1" />
          {vehicle.anio}
        </span>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <div>
            <p className="text-xs text-primary font-medium uppercase tracking-wider">{vehicle.marca}</p>
            <h3 className="text-white font-semibold group-hover:text-primary transition-colors line-clamp-1">
              {vehicle.modelo}
            </h3>
          </div>
        </div>

        <p className="text-2xl font-bold text-primary mb-3">{formatCOP(vehicle.precio)}</p>

        <div className="grid grid-cols-2 gap-2 text-xs text-gray-400">
          <div className="flex items-center gap-1.5">
            <Gauge className="w-3.5 h-3.5" />
            {formatNumber(vehicle.kilometraje)} km
          </div>
          <div className="flex items-center gap-1.5">
            <Settings2 className="w-3.5 h-3.5" />
            {vehicle.transmision}
          </div>
          <div className="flex items-center gap-1.5">
            <Fuel className="w-3.5 h-3.5" />
            {vehicle.combustible}
          </div>
          <div className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5" />
            <span className="truncate">{vehicle.ubicacion.split(' - ')[1] || vehicle.ubicacion}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
