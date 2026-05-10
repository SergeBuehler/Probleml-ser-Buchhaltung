import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface KPICardProps {
  title: string
  value: string
  subtitle?: string
  change?: number
  changeLabel?: string
  icon?: LucideIcon
  iconColor?: string
  iconBg?: string
  children?: React.ReactNode
  className?: string
}

export function KPICard({
  title,
  value,
  subtitle,
  change,
  changeLabel,
  icon: Icon,
  iconColor = 'text-red-600',
  iconBg = 'bg-red-50',
  children,
  className,
}: KPICardProps) {
  const isPositive = change !== undefined && change > 0
  const isNegative = change !== undefined && change < 0

  return (
    <div className={cn('bg-white rounded-xl border border-slate-200 p-5 shadow-sm', className)}>
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{title}</p>
        {Icon && (
          <div className={cn('w-9 h-9 rounded-lg flex items-center justify-center', iconBg)}>
            <Icon className={cn('w-5 h-5', iconColor)} />
          </div>
        )}
      </div>

      <div className="mb-2">
        <div className="text-2xl font-bold text-slate-900">{value}</div>
        {subtitle && <div className="text-xs text-slate-500 mt-0.5">{subtitle}</div>}
      </div>

      {change !== undefined && (
        <div className={cn('flex items-center gap-1 text-xs font-medium', isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-slate-500')}>
          {isPositive ? (
            <TrendingUp className="w-3.5 h-3.5" />
          ) : isNegative ? (
            <TrendingDown className="w-3.5 h-3.5" />
          ) : (
            <Minus className="w-3.5 h-3.5" />
          )}
          {isPositive ? '+' : ''}{change.toFixed(1)}%
          {changeLabel && <span className="text-slate-400 font-normal ml-1">{changeLabel}</span>}
        </div>
      )}

      {children}
    </div>
  )
}
