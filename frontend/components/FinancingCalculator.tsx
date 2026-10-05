'use client';

import { useState, useMemo } from 'react';
import { Calculator, DollarSign } from 'lucide-react';
import { formatCOP } from '@/lib/data';

interface FinancingCalculatorProps {
  vehiclePrice?: number;
}

export default function FinancingCalculator({ vehiclePrice = 100000000 }: FinancingCalculatorProps) {
  const [price, setPrice] = useState(vehiclePrice);
  const [downPayment, setDownPayment] = useState(Math.round(vehiclePrice * 0.3));
  const [months, setMonths] = useState(48);
  const annualRate = 18.5; // Typical Colombian rate

  const monthlyPayment = useMemo(() => {
    const principal = price - downPayment;
    if (principal <= 0) return 0;
    const monthlyRate = annualRate / 100 / 12;
    const payment =
      (principal * monthlyRate * Math.pow(1 + monthlyRate, months)) /
      (Math.pow(1 + monthlyRate, months) - 1);
    return Math.round(payment);
  }, [price, downPayment, months, annualRate]);

  const totalPayment = monthlyPayment * months + downPayment;
  const totalInterest = totalPayment - price;

  return (
    <div className="card-elevated p-6">
      <div className="flex items-center gap-2 mb-6">
        <Calculator className="w-5 h-5 text-primary" />
        <h3 className="text-white font-semibold text-lg">Simulador de Financiación</h3>
      </div>

      <div className="space-y-5">
        <div>
          <label className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-400">Valor del vehículo</span>
            <span className="text-white font-medium">{formatCOP(price)}</span>
          </label>
          <input
            type="range"
            min={30000000}
            max={300000000}
            step={1000000}
            value={price}
            onChange={(e) => {
              const newPrice = Number(e.target.value);
              setPrice(newPrice);
              setDownPayment(Math.round(newPrice * 0.3));
            }}
            className="w-full h-2 bg-border rounded-lg appearance-none cursor-pointer accent-primary"
          />
        </div>

        <div>
          <label className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-400">Cuota inicial ({Math.round((downPayment / price) * 100)}%)</span>
            <span className="text-white font-medium">{formatCOP(downPayment)}</span>
          </label>
          <input
            type="range"
            min={Math.round(price * 0.1)}
            max={Math.round(price * 0.8)}
            step={1000000}
            value={downPayment}
            onChange={(e) => setDownPayment(Number(e.target.value))}
            className="w-full h-2 bg-border rounded-lg appearance-none cursor-pointer accent-primary"
          />
        </div>

        <div>
          <label className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-400">Plazo</span>
            <span className="text-white font-medium">{months} meses</span>
          </label>
          <div className="flex gap-2">
            {[12, 24, 36, 48, 60, 72].map((m) => (
              <button
                key={m}
                onClick={() => setMonths(m)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                  months === m
                    ? 'bg-primary text-dark'
                    : 'bg-dark border border-border text-gray-400 hover:text-white hover:border-primary/30'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        <div className="border-t border-border pt-5 space-y-3">
          <div className="bg-primary/10 border border-primary/20 rounded-xl p-4 text-center">
            <p className="text-xs text-primary/70 uppercase tracking-wider mb-1">Cuota mensual estimada</p>
            <p className="text-3xl font-bold text-primary">{formatCOP(monthlyPayment)}</p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-dark rounded-lg p-3 text-center">
              <p className="text-gray-500 text-xs mb-1">Monto a financiar</p>
              <p className="text-white font-medium">{formatCOP(price - downPayment)}</p>
            </div>
            <div className="bg-dark rounded-lg p-3 text-center">
              <p className="text-gray-500 text-xs mb-1">Total intereses</p>
              <p className="text-white font-medium">{formatCOP(totalInterest)}</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 text-center">
            *Simulación con tasa E.A. del {annualRate}%. Las condiciones pueden variar.
          </p>
        </div>
      </div>
    </div>
  );
}
