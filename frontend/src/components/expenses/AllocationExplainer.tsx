'use client'

import { AllocationMethod } from '@/lib/types'
import { formatCHF, formatPercent } from '@/lib/utils'
import { Info } from 'lucide-react'

interface AllocationExplainerProps {
  allocationMethod: AllocationMethod
  totalAmount: number
  customSplitA?: number
  customSplitB?: number
  managerARevenue?: number
  managerBRevenue?: number
  managerAName?: string
  managerBName?: string
}

function getAllocationSplit(
  method: AllocationMethod,
  totalAmount: number,
  customSplitA?: number,
  customSplitB?: number,
  managerARevenue?: number,
  managerBRevenue?: number
): { percentA: number; percentB: number; amountA: number; amountB: number; description: string } {
  switch (method) {
    case 'manager_a_only':
      return {
        percentA: 100,
        percentB: 0,
        amountA: totalAmount,
        amountB: 0,
        description: 'Diese Ausgabe wird vollständig Verwalter A zugewiesen.',
      }
    case 'manager_b_only':
      return {
        percentA: 0,
        percentB: 100,
        amountA: 0,
        amountB: totalAmount,
        description: 'Diese Ausgabe wird vollständig Verwalter B zugewiesen.',
      }
    case 'split_equal':
      return {
        percentA: 50,
        percentB: 50,
        amountA: totalAmount / 2,
        amountB: totalAmount / 2,
        description: 'Diese Ausgabe wird gleichmässig (50/50) auf beide Verwalter aufgeteilt.',
      }
    case 'split_by_revenue': {
      const totalRevenue = (managerARevenue ?? 0) + (managerBRevenue ?? 0)
      const percentA = totalRevenue > 0 ? ((managerARevenue ?? 0) / totalRevenue) * 100 : 50
      const percentB = 100 - percentA
      return {
        percentA,
        percentB,
        amountA: (totalAmount * percentA) / 100,
        amountB: (totalAmount * percentB) / 100,
        description: `Aufteilung entsprechend dem Einnahmenanteil: ${percentA.toFixed(1)}% / ${percentB.toFixed(1)}%`,
      }
    }
    case 'split_custom': {
      const pA = customSplitA ?? 50
      const pB = customSplitB ?? 50
      return {
        percentA: pA,
        percentB: pB,
        amountA: (totalAmount * pA) / 100,
        amountB: (totalAmount * pB) / 100,
        description: `Benutzerdefinierte Aufteilung: ${pA}% / ${pB}%`,
      }
    }
    default:
      return {
        percentA: 50,
        percentB: 50,
        amountA: totalAmount / 2,
        amountB: totalAmount / 2,
        description: 'Gleichmässige Aufteilung',
      }
  }
}

const METHOD_LABELS: Record<AllocationMethod, string> = {
  manager_a_only: 'Nur Verwalter A',
  manager_b_only: 'Nur Verwalter B',
  split_equal: 'Gleichmässig (50/50)',
  split_by_revenue: 'Nach Einnahmenanteil',
  split_custom: 'Benutzerdefiniert',
}

export function AllocationExplainer({
  allocationMethod,
  totalAmount,
  customSplitA,
  customSplitB,
  managerARevenue,
  managerBRevenue,
  managerAName = 'Verwalter A',
  managerBName = 'Verwalter B',
}: AllocationExplainerProps) {
  const split = getAllocationSplit(
    allocationMethod,
    totalAmount,
    customSplitA,
    customSplitB,
    managerARevenue,
    managerBRevenue
  )

  if (!totalAmount) return null

  return (
    <div className="bg-slate-50 rounded-lg border border-slate-200 p-4 space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
        <Info className="w-4 h-4 text-blue-500" />
        Kostenaufteilung: {METHOD_LABELS[allocationMethod]}
      </div>

      <p className="text-xs text-slate-500">{split.description}</p>

      {/* Visual bar */}
      <div>
        <div className="h-4 rounded-full overflow-hidden flex">
          <div
            className="h-full bg-blue-500 transition-all"
            style={{ width: `${split.percentA}%` }}
          />
          <div
            className="h-full bg-orange-400 transition-all"
            style={{ width: `${split.percentB}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-slate-400 mt-1">
          <span>{split.percentA.toFixed(1)}%</span>
          <span>{split.percentB.toFixed(1)}%</span>
        </div>
      </div>

      {/* Amount breakdown */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded p-3 border border-blue-100">
          <div className="flex items-center gap-1.5 mb-1">
            <div className="w-2.5 h-2.5 rounded-full bg-blue-500" />
            <span className="text-xs font-medium text-slate-700">{managerAName}</span>
          </div>
          <div className="text-sm font-bold text-slate-900">{formatCHF(split.amountA)}</div>
          <div className="text-xs text-slate-500">{formatPercent(split.percentA / 100)}</div>
        </div>
        <div className="bg-white rounded p-3 border border-orange-100">
          <div className="flex items-center gap-1.5 mb-1">
            <div className="w-2.5 h-2.5 rounded-full bg-orange-400" />
            <span className="text-xs font-medium text-slate-700">{managerBName}</span>
          </div>
          <div className="text-sm font-bold text-slate-900">{formatCHF(split.amountB)}</div>
          <div className="text-xs text-slate-500">{formatPercent(split.percentB / 100)}</div>
        </div>
      </div>

      <div className="flex justify-between text-xs text-slate-500 pt-1 border-t border-slate-200">
        <span>Gesamtbetrag</span>
        <span className="font-semibold text-slate-900">{formatCHF(totalAmount)}</span>
      </div>
    </div>
  )
}
