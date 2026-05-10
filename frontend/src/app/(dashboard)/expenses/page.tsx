'use client'

import { useState, useEffect } from 'react'
import { Plus, Search, Upload, CheckSquare, Filter, Receipt } from 'lucide-react'
import Link from 'next/link'
import { expensesApi } from '@/lib/api'
import { Expense } from '@/lib/types'
import { formatCHF, formatDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { toast } from 'sonner'

const STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  pending_approval: 'Ausstehend',
  approved: 'Genehmigt',
  rejected: 'Abgelehnt',
  paid: 'Bezahlt',
  cancelled: 'Storniert',
}

const STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'outline' | 'info'> = {
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

const ALLOCATION_LABELS: Record<string, string> = {
  manager_a_only: 'Nur A',
  manager_b_only: 'Nur B',
  split_equal: '50/50',
  split_by_revenue: 'Nach Umsatz',
  split_custom: 'Individuell',
}

export default function ExpensesPage() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [allocationFilter, setAllocationFilter] = useState('all')
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)

  useEffect(() => {
    loadExpenses()
  }, [page, statusFilter, categoryFilter, allocationFilter])

  const loadExpenses = async () => {
    setIsLoading(true)
    try {
      const params = {
        page,
        page_size: 20,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        category: categoryFilter !== 'all' ? categoryFilter : undefined,
        allocation_method: allocationFilter !== 'all' ? allocationFilter : undefined,
      }
      const response = await expensesApi.getExpenses(params)
      setExpenses(response.data)
      setTotal(response.total)
    } catch {
      toast.error('Fehler beim Laden der Ausgaben')
    } finally {
      setIsLoading(false)
    }
  }

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return
    try {
      await expensesApi.bulkApprove([...selectedIds])
      toast.success(`${selectedIds.size} Ausgaben genehmigt`)
      setSelectedIds(new Set())
      loadExpenses()
    } catch {
      toast.error('Fehler beim Genehmigen')
    }
  }

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const filtered = expenses.filter(e =>
    !search ||
    e.title.toLowerCase().includes(search.toLowerCase()) ||
    e.vendor.toLowerCase().includes(search.toLowerCase())
  )

  const totalAmount = filtered.reduce((sum, e) => sum + e.total_amount, 0)
  const totalByAllocation = {
    'Nur A': filtered.filter(e => e.allocation_method === 'manager_a_only').reduce((sum, e) => sum + e.total_amount, 0),
    '50/50': filtered.filter(e => e.allocation_method === 'split_equal').reduce((sum, e) => sum + e.total_amount, 0),
    'Nur B': filtered.filter(e => e.allocation_method === 'manager_b_only').reduce((sum, e) => sum + e.total_amount, 0),
    'Nach Umsatz': filtered.filter(e => e.allocation_method === 'split_by_revenue').reduce((sum, e) => sum + e.total_amount, 0),
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Ausgaben</h1>
          <p className="text-sm text-slate-500 mt-0.5">{total} Ausgaben total</p>
        </div>
        <div className="flex items-center gap-2">
          {selectedIds.size > 0 && (
            <Button variant="success" onClick={handleBulkApprove}>
              <CheckSquare className="w-4 h-4 mr-2" />
              {selectedIds.size} genehmigen
            </Button>
          )}
          <Button variant="outline" asChild>
            <Link href="/dashboard/expenses/new">
              <Upload className="w-4 h-4 mr-2" />
              Scan / Upload
            </Link>
          </Button>
          <Button asChild>
            <Link href="/dashboard/expenses/new">
              <Plus className="w-4 h-4 mr-2" />
              Neue Ausgabe
            </Link>
          </Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Object.entries(totalByAllocation).map(([label, amount]) => (
          <div key={label} className="bg-white rounded-lg border border-slate-200 p-3 shadow-sm">
            <div className="text-xs text-slate-500 mb-1">{label}</div>
            <div className="text-sm font-bold text-slate-900">{formatCHF(amount)}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Suchen..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="all">Alle Status</option>
          {Object.entries(STATUS_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="all">Alle Kategorien</option>
          {Object.entries(CATEGORY_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
        <select
          value={allocationFilter}
          onChange={(e) => setAllocationFilter(e.target.value)}
          className="text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="all">Alle Zuteilungen</option>
          {Object.entries(ALLOCATION_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-14" />)}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <input
                    type="checkbox"
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedIds(new Set(filtered.map(ex => ex.id)))
                      } else {
                        setSelectedIds(new Set())
                      }
                    }}
                    checked={selectedIds.size === filtered.length && filtered.length > 0}
                    className="rounded border-slate-300"
                  />
                </TableHead>
                <TableHead>Datum</TableHead>
                <TableHead>Titel / Lieferant</TableHead>
                <TableHead>Kategorie</TableHead>
                <TableHead>Zuteilung</TableHead>
                <TableHead className="text-right">Netto</TableHead>
                <TableHead className="text-right">MwSt</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-12 text-slate-400">
                    <Receipt className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p className="text-sm">Keine Ausgaben gefunden</p>
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((expense) => (
                  <TableRow key={expense.id} className="cursor-pointer" onClick={() => {}}>
                    <TableCell onClick={e => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(expense.id)}
                        onChange={() => toggleSelect(expense.id)}
                        className="rounded border-slate-300"
                      />
                    </TableCell>
                    <TableCell className="text-sm text-slate-600 whitespace-nowrap">
                      {formatDate(expense.expense_date)}
                    </TableCell>
                    <TableCell>
                      <Link href={`/dashboard/expenses/${expense.id}`} className="hover:text-red-600">
                        <div className="font-medium text-slate-900 text-sm">{expense.title}</div>
                        <div className="text-xs text-slate-500">{expense.vendor}</div>
                      </Link>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-slate-600">{CATEGORY_LABELS[expense.category] ?? expense.category}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {ALLOCATION_LABELS[expense.allocation_method]}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right text-sm text-slate-700">
                      {formatCHF(expense.amount)}
                    </TableCell>
                    <TableCell className="text-right text-sm text-slate-500">
                      {formatCHF(expense.vat_amount)}
                    </TableCell>
                    <TableCell className="text-right text-sm font-semibold text-slate-900">
                      {formatCHF(expense.total_amount)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANTS[expense.status]}>
                        {STATUS_LABELS[expense.status]}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}

        {/* Footer totals */}
        {filtered.length > 0 && !isLoading && (
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
            <span className="text-xs text-slate-500">{filtered.length} Ausgaben angezeigt</span>
            <div className="text-sm font-bold text-slate-900">
              Total: {formatCHF(totalAmount)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
