'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, Building2, Receipt, CreditCard, RefreshCw } from 'lucide-react'
import { reportsApi } from '@/lib/api'
import { DashboardData } from '@/lib/types'
import { formatCHF, formatDate, formatPercent } from '@/lib/utils'
import { KPICard } from '@/components/dashboard/KPICard'
import { RevenueChart } from '@/components/dashboard/RevenueChart'
import { ManagerSplit } from '@/components/dashboard/ManagerSplit'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { toast } from 'sonner'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const EXPENSE_STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  pending_approval: 'Ausstehend',
  approved: 'Genehmigt',
  rejected: 'Abgelehnt',
  paid: 'Bezahlt',
  cancelled: 'Storniert',
}

const EXPENSE_STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'outline' | 'info'> = {
  draft: 'secondary',
  pending_approval: 'warning',
  approved: 'success',
  rejected: 'destructive',
  paid: 'info',
  cancelled: 'outline',
}

const CATEGORY_LABELS: Record<string, string> = {
  maintenance: 'Unterhalt',
  repair: 'Reparaturen',
  insurance: 'Versicherung',
  utilities: 'Nebenkosten',
  management: 'Verwaltung',
  legal: 'Rechtliches',
  accounting: 'Buchhaltung',
  cleaning: 'Reinigung',
  landscaping: 'Gartenpflege',
  advertising: 'Werbung',
  office: 'Büro',
  travel: 'Reisen',
  other: 'Sonstiges',
}

const CATEGORY_COLORS = [
  '#3b82f6', '#f97316', '#8b5cf6', '#10b981', '#f59e0b',
  '#ef4444', '#06b6d4', '#ec4899', '#84cc16', '#6366f1',
]

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Skeleton className="h-80 xl:col-span-2 rounded-xl" />
        <Skeleton className="h-80 rounded-xl" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
    </div>
  )
}

export default function DashboardPage() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [data, setData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchData = async (yr: number, refresh = false) => {
    if (refresh) setIsRefreshing(true)
    else setIsLoading(true)
    try {
      const dashboard = await reportsApi.getDashboard(yr)
      setData(dashboard)
    } catch {
      toast.error('Fehler beim Laden der Dashboard-Daten')
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchData(year)
  }, [year])

  if (isLoading) return <LoadingSkeleton />

  // Fallback demo data for display when API is not connected
  const d: DashboardData = data ?? {
    year,
    total_revenue_ytd: 186400,
    manager_a_revenue: 111840,
    manager_b_revenue: 74560,
    manager_a_percentage: 0.6,
    manager_b_percentage: 0.4,
    open_expenses_count: 8,
    open_expenses_total: 12450,
    pending_reconciliation_count: 5,
    monthly_revenue: Array.from({ length: 12 }, (_, i) => ({
      month: i + 1,
      month_name: ['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'][i],
      manager_a_revenue: 8000 + Math.random() * 4000,
      manager_b_revenue: 5000 + Math.random() * 3000,
      total_revenue: 0,
    })).map(m => ({ ...m, total_revenue: m.manager_a_revenue + m.manager_b_revenue })),
    expense_by_category: [
      { category: 'maintenance', amount: 8200, count: 12 },
      { category: 'insurance', amount: 5600, count: 4 },
      { category: 'utilities', amount: 3400, count: 8 },
      { category: 'management', amount: 2800, count: 6 },
      { category: 'repair', amount: 2100, count: 5 },
    ],
    bank_accounts: [],
    recent_expenses: [],
    properties_count: 14,
    active_properties: 12,
  }

  const expenseCategoryChartData = d.expense_by_category.slice(0, 5).map((item, idx) => ({
    name: CATEGORY_LABELS[item.category] ?? item.category,
    value: item.amount,
    color: CATEGORY_COLORS[idx],
  }))

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">Übersicht für das Jahr {year}</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="text-sm border border-slate-300 rounded-md px-3 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {[currentYear, currentYear - 1, currentYear - 2].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
          <button
            onClick={() => fetchData(year, true)}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900 border border-slate-300 rounded-md px-3 py-1.5 bg-white hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Aktualisieren
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <KPICard
          title="Jahresumsatz"
          value={formatCHF(d.total_revenue_ytd)}
          subtitle={`${d.active_properties} aktive Liegenschaften`}
          icon={TrendingUp}
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        />

        <KPICard
          title="Verwalter A – Anteil"
          value={formatPercent(d.manager_a_percentage)}
          subtitle={formatCHF(d.manager_a_revenue)}
          icon={Building2}
          iconColor="text-blue-600"
          iconBg="bg-blue-50"
        >
          <div className="mt-3">
            <Progress value={d.manager_a_percentage * 100} className="h-1.5" />
          </div>
        </KPICard>

        <KPICard
          title="Verwalter B – Anteil"
          value={formatPercent(d.manager_b_percentage)}
          subtitle={formatCHF(d.manager_b_revenue)}
          icon={Building2}
          iconColor="text-orange-500"
          iconBg="bg-orange-50"
        >
          <div className="mt-3">
            <Progress
              value={d.manager_b_percentage * 100}
              className="h-1.5 [&>div]:bg-orange-400"
            />
          </div>
        </KPICard>

        <KPICard
          title="Offene Ausgaben"
          value={String(d.open_expenses_count)}
          subtitle={`${formatCHF(d.open_expenses_total)} ausstehend`}
          icon={Receipt}
          iconColor="text-amber-600"
          iconBg="bg-amber-50"
        >
          {d.pending_reconciliation_count > 0 && (
            <div className="mt-2 text-xs text-slate-500">
              {d.pending_reconciliation_count} Bankabgleiche ausstehend
            </div>
          )}
        </KPICard>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2">
          <RevenueChart data={d.monthly_revenue} year={year} />
        </div>
        <ManagerSplit
          managerARevenue={d.manager_a_revenue}
          managerBRevenue={d.manager_b_revenue}
        />
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Expense categories */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <h3 className="font-semibold text-slate-900 mb-1">Ausgaben nach Kategorie</h3>
          <p className="text-xs text-slate-500 mb-4">Top-Ausgabenkategorien</p>
          <div className="flex items-center gap-4">
            <ResponsiveContainer width={110} height={110}>
              <PieChart>
                <Pie
                  data={expenseCategoryChartData}
                  cx="50%"
                  cy="50%"
                  outerRadius={50}
                  dataKey="value"
                  paddingAngle={2}
                >
                  {expenseCategoryChartData.map((entry, idx) => (
                    <Cell key={idx} fill={entry.color} strokeWidth={0} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: number) => formatCHF(value)}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-2">
              {expenseCategoryChartData.map((item) => (
                <div key={item.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-xs text-slate-600">{item.name}</span>
                  </div>
                  <span className="text-xs font-medium text-slate-900">{formatCHF(item.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Recent expenses */}
        <div className="xl:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-slate-900">Letzte Ausgaben</h3>
              <p className="text-xs text-slate-500 mt-0.5">Neueste Buchungen</p>
            </div>
            <a href="/dashboard/expenses" className="text-xs text-red-600 hover:text-red-700 font-medium">
              Alle anzeigen →
            </a>
          </div>
          {d.recent_expenses.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
              <Receipt className="w-8 h-8 mb-2" />
              <p className="text-sm">Keine aktuellen Ausgaben</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-50">
              {d.recent_expenses.slice(0, 8).map((expense) => (
                <div key={expense.id} className="flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                      <Receipt className="w-4 h-4 text-slate-500" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-slate-900 truncate max-w-[180px]">
                        {expense.title}
                      </div>
                      <div className="text-xs text-slate-500">
                        {expense.vendor} · {formatDate(expense.expense_date)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={EXPENSE_STATUS_VARIANTS[expense.status]}>
                      {EXPENSE_STATUS_LABELS[expense.status]}
                    </Badge>
                    <span className="text-sm font-semibold text-slate-900 text-right min-w-[80px]">
                      {formatCHF(expense.total_amount)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bank accounts */}
      {d.bank_accounts.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-900">Bankkonten</h3>
            <a href="/dashboard/banking" className="text-xs text-red-600 hover:text-red-700 font-medium">
              Banking →
            </a>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {d.bank_accounts.map((account) => (
              <div key={account.id} className="flex items-center gap-3 p-3 border border-slate-100 rounded-lg">
                <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
                  <CreditCard className="w-5 h-5 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-900 truncate">{account.account_name}</div>
                  <div className="text-xs text-slate-500">{account.bank_name}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-slate-900">{formatCHF(account.balance)}</div>
                  <div className={`text-xs ${account.connection_status === 'connected' ? 'text-green-600' : 'text-amber-600'}`}>
                    {account.connection_status === 'connected' ? 'Verbunden' : 'Getrennt'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
