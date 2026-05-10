'use client'

import { useState, useEffect } from 'react'
import { BookOpen, Lock, Unlock, AlertTriangle, CheckCircle2, TrendingUp } from 'lucide-react'
import { accountingApi } from '@/lib/api'
import { FiscalYear, AccountingEntry } from '@/lib/types'
import { formatCHF, formatDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '@/components/ui/dialog'
import { toast } from 'sonner'

const YEAR_STATUS_LABELS: Record<string, string> = {
  open: 'Offen',
  closing: 'In Abschluss',
  closed: 'Abgeschlossen',
}

const YEAR_STATUS_VARIANTS: Record<string, 'default' | 'secondary' | 'destructive' | 'success' | 'warning' | 'outline' | 'info'> = {
  open: 'success',
  closing: 'warning',
  closed: 'secondary',
}

const ENTRY_TYPE_LABELS: Record<string, string> = {
  revenue: 'Einnahmen',
  expense: 'Ausgaben',
  payroll: 'Lohnbuchhaltung',
  transfer: 'Transfer',
  adjustment: 'Anpassung',
}

export default function AccountingPage() {
  const [fiscalYears, setFiscalYears] = useState<FiscalYear[]>([])
  const [entries, setEntries] = useState<AccountingEntry[]>([])
  const [selectedYear, setSelectedYear] = useState<FiscalYear | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showCloseDialog, setShowCloseDialog] = useState(false)
  const [isClosing, setIsClosing] = useState(false)
  const [closeNotes, setCloseNotes] = useState('')
  const [entriesTotal, setEntriesTotal] = useState(0)
  const [entryTypeFilter, setEntryTypeFilter] = useState('all')

  useEffect(() => {
    loadFiscalYears()
  }, [])

  useEffect(() => {
    if (selectedYear) {
      loadEntries(selectedYear.year)
    }
  }, [selectedYear, entryTypeFilter])

  const loadFiscalYears = async () => {
    setIsLoading(true)
    try {
      const years = await accountingApi.getFiscalYears()
      setFiscalYears(years)
      if (years.length > 0) {
        setSelectedYear(years[0])
      }
    } catch {
      toast.error('Fehler beim Laden der Geschäftsjahre')
    } finally {
      setIsLoading(false)
    }
  }

  const loadEntries = async (year: number) => {
    try {
      const response = await accountingApi.getAccountingEntries({
        fiscal_year: year,
        entry_type: entryTypeFilter !== 'all' ? entryTypeFilter : undefined,
        page_size: 50,
      })
      setEntries(response.data)
      setEntriesTotal(response.total)
    } catch {
      toast.error('Fehler beim Laden der Buchungen')
    }
  }

  const handleCloseYear = async () => {
    if (!selectedYear) return
    setIsClosing(true)
    try {
      const updated = await accountingApi.closeYear(selectedYear.year, closeNotes)
      setFiscalYears(prev => prev.map(y => y.year === updated.year ? updated : y))
      setSelectedYear(updated)
      setShowCloseDialog(false)
      toast.success(`Geschäftsjahr ${selectedYear.year} abgeschlossen`)
    } catch {
      toast.error('Fehler beim Jahresabschluss')
    } finally {
      setIsClosing(false)
    }
  }

  const currentYear = selectedYear

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Buchhaltung</h1>
          <p className="text-sm text-slate-500 mt-0.5">Jahresabschluss und Buchungsübersicht</p>
        </div>
        {currentYear?.status === 'open' && (
          <Button variant="warning" onClick={() => setShowCloseDialog(true)}>
            <Lock className="w-4 h-4 mr-2" />
            Jahresabschluss {currentYear.year}
          </Button>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-5">
        {/* Fiscal year selector */}
        <div className="xl:col-span-1 bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h2 className="font-semibold text-slate-900 mb-3 text-sm">Geschäftsjahre</h2>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-10" />)}
            </div>
          ) : (
            <div className="space-y-1">
              {fiscalYears.map((year) => (
                <button
                  key={year.id}
                  onClick={() => setSelectedYear(year)}
                  className={`w-full text-left px-3 py-2.5 rounded-md text-sm flex items-center justify-between transition-colors ${
                    selectedYear?.year === year.year
                      ? 'bg-red-50 text-red-700 border border-red-200'
                      : 'hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <span className="font-medium">{year.year}</span>
                  <Badge variant={YEAR_STATUS_VARIANTS[year.status]}>
                    {YEAR_STATUS_LABELS[year.status]}
                  </Badge>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Main content */}
        <div className="xl:col-span-3 space-y-5">
          {currentYear && (
            <>
              {/* Year summary */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="font-semibold text-slate-900 flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-slate-400" />
                    Jahresergebnis {currentYear.year}
                  </h2>
                  <div className="flex items-center gap-2">
                    <Badge variant={YEAR_STATUS_VARIANTS[currentYear.status]}>
                      {YEAR_STATUS_LABELS[currentYear.status]}
                    </Badge>
                    {currentYear.status === 'closed' ? (
                      <Lock className="w-4 h-4 text-slate-400" />
                    ) : (
                      <Unlock className="w-4 h-4 text-green-500" />
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-4">
                  <div className="bg-green-50 rounded-lg p-3">
                    <div className="text-xs text-green-600 font-medium mb-1">Gesamteinnahmen</div>
                    <div className="text-lg font-bold text-green-800">{formatCHF(currentYear.total_revenue)}</div>
                  </div>
                  <div className="bg-red-50 rounded-lg p-3">
                    <div className="text-xs text-red-600 font-medium mb-1">Gesamtausgaben</div>
                    <div className="text-lg font-bold text-red-800">{formatCHF(currentYear.total_expenses)}</div>
                  </div>
                  <div className={`${currentYear.net_income >= 0 ? 'bg-blue-50' : 'bg-red-50'} rounded-lg p-3`}>
                    <div className={`text-xs font-medium mb-1 ${currentYear.net_income >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                      Nettoergebnis
                    </div>
                    <div className={`text-lg font-bold ${currentYear.net_income >= 0 ? 'text-blue-800' : 'text-red-800'}`}>
                      {formatCHF(currentYear.net_income)}
                    </div>
                  </div>
                </div>

                {/* Manager breakdown */}
                <div className="border-t border-slate-100 pt-4">
                  <h3 className="text-sm font-semibold text-slate-700 mb-3">Verwalteraufteilung</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="border border-blue-100 rounded-lg p-3">
                      <div className="text-xs text-blue-600 font-medium mb-2">Verwalter A</div>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Einnahmen</span>
                          <span className="text-green-600 font-medium">{formatCHF(currentYear.manager_a_revenue)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Ausgaben</span>
                          <span className="text-red-600 font-medium">{formatCHF(currentYear.manager_a_expenses)}</span>
                        </div>
                        <div className="flex justify-between border-t border-slate-100 pt-1">
                          <span className="font-semibold text-slate-900">Netto</span>
                          <span className={`font-bold ${currentYear.manager_a_net >= 0 ? 'text-blue-700' : 'text-red-700'}`}>
                            {formatCHF(currentYear.manager_a_net)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="border border-orange-100 rounded-lg p-3">
                      <div className="text-xs text-orange-600 font-medium mb-2">Verwalter B</div>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Einnahmen</span>
                          <span className="text-green-600 font-medium">{formatCHF(currentYear.manager_b_revenue)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Ausgaben</span>
                          <span className="text-red-600 font-medium">{formatCHF(currentYear.manager_b_expenses)}</span>
                        </div>
                        <div className="flex justify-between border-t border-slate-100 pt-1">
                          <span className="font-semibold text-slate-900">Netto</span>
                          <span className={`font-bold ${currentYear.manager_b_net >= 0 ? 'text-orange-600' : 'text-red-700'}`}>
                            {formatCHF(currentYear.manager_b_net)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Settlement */}
                  {currentYear.status === 'closed' && currentYear.settlement_amount > 0 && (
                    <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
                      <TrendingUp className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                      <div className="text-sm text-amber-800">
                        <strong>Ausgleichszahlung:</strong>{' '}
                        {currentYear.settlement_direction === 'a_pays_b'
                          ? `Verwalter A schuldet Verwalter B `
                          : `Verwalter B schuldet Verwalter A `}
                        <strong>{formatCHF(currentYear.settlement_amount)}</strong>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Entries table */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                  <h2 className="font-semibold text-slate-900">Buchungen ({entriesTotal})</h2>
                  <select
                    value={entryTypeFilter}
                    onChange={(e) => setEntryTypeFilter(e.target.value)}
                    className="text-sm border border-slate-300 rounded-md px-3 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    <option value="all">Alle Typen</option>
                    {Object.entries(ENTRY_TYPE_LABELS).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Datum</TableHead>
                      <TableHead>Beschreibung</TableHead>
                      <TableHead>Typ</TableHead>
                      <TableHead>Soll-Konto</TableHead>
                      <TableHead>Haben-Konto</TableHead>
                      <TableHead className="text-right">Betrag</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entries.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-10 text-slate-400">
                          Keine Buchungen gefunden
                        </TableCell>
                      </TableRow>
                    ) : (
                      entries.map((entry) => (
                        <TableRow key={entry.id}>
                          <TableCell className="text-sm text-slate-600 whitespace-nowrap">
                            {formatDate(entry.date)}
                          </TableCell>
                          <TableCell>
                            <div className="text-sm text-slate-900">{entry.description}</div>
                            {entry.reference && (
                              <div className="text-xs text-slate-400">{entry.reference}</div>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {ENTRY_TYPE_LABELS[entry.entry_type]}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-xs text-slate-600">{entry.debit_account}</TableCell>
                          <TableCell className="text-xs text-slate-600">{entry.credit_account}</TableCell>
                          <TableCell className="text-right text-sm font-medium text-slate-900">
                            {formatCHF(entry.amount)}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Year close dialog */}
      <Dialog open={showCloseDialog} onOpenChange={setShowCloseDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Jahresabschluss {currentYear?.year}</DialogTitle>
            <DialogDescription>
              Der Jahresabschluss ist unwiderruflich. Stellen Sie sicher, dass alle Buchungen abgeschlossen sind.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-amber-800">
                Nach dem Jahresabschluss können keine Buchungen mehr für {currentYear?.year} vorgenommen werden.
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700">Bemerkungen (optional)</label>
              <textarea
                value={closeNotes}
                onChange={(e) => setCloseNotes(e.target.value)}
                rows={3}
                placeholder="Abschlussnotizen..."
                className="mt-1.5 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 resize-none"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCloseDialog(false)}>Abbrechen</Button>
            <Button variant="destructive" onClick={handleCloseYear} disabled={isClosing}>
              <Lock className="w-4 h-4 mr-2" />
              {isClosing ? 'Wird abgeschlossen...' : `Jahr ${currentYear?.year} abschliessen`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
