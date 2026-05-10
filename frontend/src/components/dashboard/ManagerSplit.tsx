'use client'

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { formatCHF, formatPercent } from '@/lib/utils'

interface ManagerSplitProps {
  managerARevenue: number
  managerBRevenue: number
  managerAName?: string
  managerBName?: string
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number }> }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-sm">
        <p className="font-semibold text-slate-900">{payload[0].name}</p>
        <p className="text-slate-600">{formatCHF(payload[0].value)}</p>
      </div>
    )
  }
  return null
}

export function ManagerSplit({
  managerARevenue,
  managerBRevenue,
  managerAName = 'Verwalter A',
  managerBName = 'Verwalter B',
}: ManagerSplitProps) {
  const total = managerARevenue + managerBRevenue
  const percentA = total > 0 ? (managerARevenue / total) * 100 : 50
  const percentB = total > 0 ? (managerBRevenue / total) * 100 : 50

  const data = [
    { name: managerAName, value: managerARevenue, color: '#3b82f6' },
    { name: managerBName, value: managerBRevenue, color: '#fb923c' },
  ]

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <h3 className="font-semibold text-slate-900 mb-1">Einnahmenverteilung</h3>
      <p className="text-xs text-slate-500 mb-4">Aufteilung zwischen den Verwaltern</p>

      <div className="flex items-center gap-6">
        <div className="relative w-32 h-32 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={38}
                outerRadius={56}
                startAngle={90}
                endAngle={-270}
                paddingAngle={2}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={index} fill={entry.color} strokeWidth={0} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          {/* Center label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <div className="text-xs font-bold text-slate-900">{formatPercent(percentA / 100)}</div>
            <div className="text-xs text-slate-400">/ {formatPercent(percentB / 100)}</div>
          </div>
        </div>

        <div className="flex-1 space-y-3">
          {data.map((entry) => (
            <div key={entry.name}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: entry.color }} />
                  <span className="text-sm text-slate-700 font-medium">{entry.name}</span>
                </div>
                <span className="text-sm font-semibold text-slate-900">
                  {total > 0 ? formatPercent(entry.value / total) : '50.0%'}
                </span>
              </div>
              <div className="text-xs text-slate-500 ml-4.5 ml-5">{formatCHF(entry.value)}</div>
              <div className="mt-1 h-1.5 rounded-full bg-slate-100 overflow-hidden ml-5">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${total > 0 ? (entry.value / total) * 100 : 50}%`,
                    backgroundColor: entry.color,
                  }}
                />
              </div>
            </div>
          ))}

          <div className="pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-500">Total</span>
              <span className="text-sm font-bold text-slate-900">{formatCHF(total)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
