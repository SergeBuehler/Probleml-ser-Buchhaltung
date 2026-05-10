'use client'

import { useMemo } from 'react'
import { formatCHF } from '@/lib/utils'
import { Calendar, TrendingUp, DivideCircle } from 'lucide-react'

interface RevenueCalculatorProps {
  annualFee: number
  startDate: string
  year?: number
}

function getDaysInYear(year: number): number {
  return ((year % 4 === 0 && year % 100 !== 0) || year % 400 === 0) ? 366 : 365
}

function calculateProration(annualFee: number, startDate: string, year: number) {
  const start = new Date(startDate)
  const startYear = start.getFullYear()

  if (!annualFee || !startDate || isNaN(start.getTime())) {
    return { prorated: 0, monthlyRevenue: 0, daysActive: 0, daysInYear: 365, isFirstYear: false }
  }

  if (startYear > year) return { prorated: 0, monthlyRevenue: 0, daysActive: 0, daysInYear: getDaysInYear(year), isFirstYear: false }
  if (startYear < year) {
    return {
      prorated: annualFee,
      monthlyRevenue: annualFee / 12,
      daysActive: getDaysInYear(year),
      daysInYear: getDaysInYear(year),
      isFirstYear: false,
    }
  }

  const daysInYear = getDaysInYear(year)
  const yearEnd = new Date(year, 11, 31)
  const daysActive = Math.floor((yearEnd.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1
  const prorated = (annualFee / daysInYear) * daysActive

  return { prorated, monthlyRevenue: annualFee / 12, daysActive, daysInYear, isFirstYear: true }
}

export function RevenueCalculator({ annualFee, startDate, year }: RevenueCalculatorProps) {
  const currentYear = year ?? new Date().getFullYear()

  const calc = useMemo(
    () => calculateProration(annualFee, startDate, currentYear),
    [annualFee, startDate, currentYear]
  )

  if (!annualFee || !startDate) {
    return (
      <div className="bg-slate-50 rounded-lg border border-slate-200 p-4 text-sm text-slate-500 text-center">
        Füllen Sie Jahresgebühr und Startdatum aus, um die Einnahmen zu berechnen.
      </div>
    )
  }

  return (
    <div className="bg-blue-50 rounded-lg border border-blue-200 p-4 space-y-3">
      <div className="flex items-center gap-2 text-blue-800 font-semibold text-sm">
        <TrendingUp className="w-4 h-4" />
        Einnahmenvorschau {currentYear}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white rounded-md p-3 border border-blue-100">
          <div className="text-xs text-slate-500 mb-1 flex items-center gap-1">
            <Calendar className="w-3 h-3" />
            Monatseinnahmen
          </div>
          <div className="font-bold text-slate-900">{formatCHF(calc.monthlyRevenue)}</div>
        </div>
        <div className="bg-white rounded-md p-3 border border-blue-100">
          <div className="text-xs text-slate-500 mb-1 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            {calc.isFirstYear ? 'Erstes Jahr (Prorata)' : `Vollbetrag ${currentYear}`}
          </div>
          <div className="font-bold text-slate-900">{formatCHF(calc.prorated)}</div>
        </div>
        <div className="bg-white rounded-md p-3 border border-blue-100">
          <div className="text-xs text-slate-500 mb-1 flex items-center gap-1">
            <DivideCircle className="w-3 h-3" />
            Jahresgebühr (voll)
          </div>
          <div className="font-bold text-slate-900">{formatCHF(annualFee)}</div>
        </div>
      </div>

      {calc.isFirstYear && (
        <div className="text-xs text-blue-700 bg-blue-100 rounded p-2.5">
          <strong>Prorata-Berechnung:</strong> {formatCHF(annualFee)} ÷ {calc.daysInYear} Tage × {calc.daysActive} aktive Tage ={' '}
          <strong>{formatCHF(calc.prorated)}</strong>
        </div>
      )}

      {/* Visual timeline */}
      {calc.isFirstYear && (
        <div>
          <div className="text-xs text-slate-500 mb-1">Aktive Periode {currentYear}</div>
          <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full"
              style={{ width: `${(calc.daysActive / calc.daysInYear) * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>01.01.{currentYear}</span>
            <span>{calc.daysActive} von {calc.daysInYear} Tagen ({((calc.daysActive / calc.daysInYear) * 100).toFixed(1)}%)</span>
            <span>31.12.{currentYear}</span>
          </div>
        </div>
      )}
    </div>
  )
}
