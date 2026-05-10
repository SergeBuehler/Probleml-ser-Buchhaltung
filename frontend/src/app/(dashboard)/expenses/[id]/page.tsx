'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, FileText, CheckCircle2, XCircle, Clock, User, DivideCircle } from 'lucide-react'
import Link from 'next/link'
import { expensesApi } from '@/lib/api'
import { Expense, ExpenseAuditLog, ExpenseAllocation } from '@/lib/types'
import { formatCHF, formatDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { AllocationExplainer } from '@/components/expenses/AllocationExplainer'
import { toast } from 'sonner'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '@/components/ui/dialog'

const STATUS_LABELS: Record<string, string> = {
  draft: 'Entwurf',
  pending_approval: 'Zur Genehmigung',
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
  maintenance: 'Unterhalt', repair: 'Reparaturen', insurance: 'Versicherung',
  utilities: 'Nebenkosten', management: 'Verwaltung', legal: 'Rechtliches',
  accounting: 'Buchhaltung', cleaning: 'Reinigung', landscaping: 'Gartenpflege',
  advertising: 'Werbung', office: 'Büro', travel: 'Reisen', other: 'Sonstiges',
}

export default function ExpenseDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [expense, setExpense] = useState<Expense | null>(null)
  const [auditLog, setAuditLog] = useState<ExpenseAuditLog[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showRejectDialog, setShowRejectDialog] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [isActing, setIsActing] = useState(false)

  useEffect(() => {
    if (params.id) {
      loadExpense(Number(params.id))
    }
  }, [params.id])

  const loadExpense = async (id: number) => {
    setIsLoading(true)
    try {
      const [exp, logs] = await Promise.all([
        expensesApi.getExpense(id),
        expensesApi.getAuditLog(id).catch(() => []),
      ])
      setExpense(exp)
      setAuditLog(logs)
    } catch {
      toast.error('Ausgabe nicht gefunden')
      router.push('/dashboard/expenses')
    } finally {
      setIsLoading(false)
    }
  }

  const handleApprove = async () => {
    if (!expense) return
    setIsActing(true)
    try {
      const updated = await expensesApi.approveExpense(expense.id)
      setExpense(updated)
      toast.success('Ausgabe genehmigt')
    } catch {
      toast.error('Fehler beim Genehmigen')
    } finally {
      setIsActing(false)
    }
  }

  const handleReject = async () => {
    if (!expense || !rejectReason.trim()) return
    setIsActing(true)
    try {
      const updated = await expensesApi.rejectExpense(expense.id, rejectReason)
      setExpense(updated)
      setShowRejectDialog(false)
      toast.success('Ausgabe abgelehnt')
    } catch {
      toast.error('Fehler beim Ablehnen')
    } finally {
      setIsActing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    )
  }

  if (!expense) return null

  const canAct = expense.status === 'pending_approval'

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/expenses">
              <ArrowLeft className="w-4 h-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-900">{expense.title}</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <Badge variant={STATUS_VARIANTS[expense.status]}>
                {STATUS_LABELS[expense.status]}
              </Badge>
              <span className="text-xs text-slate-500">{formatDate(expense.expense_date)}</span>
            </div>
          </div>
        </div>
        {canAct && (
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setShowRejectDialog(true)}>
              <XCircle className="w-4 h-4 mr-2 text-red-500" />
              Ablehnen
            </Button>
            <Button variant="success" onClick={handleApprove} disabled={isActing}>
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Genehmigen
            </Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-5">
          {/* Expense details */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h2 className="font-semibold text-slate-900 mb-4">Ausgabedetails</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-slate-500 mb-0.5">Lieferant</div>
                <div className="text-sm font-medium text-slate-900">{expense.vendor}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-0.5">Datum</div>
                <div className="text-sm font-medium text-slate-900">{formatDate(expense.expense_date)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-0.5">Kategorie</div>
                <div className="text-sm font-medium text-slate-900">{CATEGORY_LABELS[expense.category]}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-0.5">Eingereicht von</div>
                <div className="text-sm font-medium text-slate-900">{expense.submitted_by?.full_name}</div>
              </div>
            </div>

            {/* Amount breakdown */}
            <div className="mt-4 pt-4 border-t border-slate-100">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Nettobetrag</span>
                  <span className="text-slate-900">{formatCHF(expense.amount)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">MwSt ({expense.vat_rate}%)</span>
                  <span className="text-slate-900">{formatCHF(expense.vat_amount)}</span>
                </div>
                <div className="flex justify-between font-semibold text-slate-900 pt-2 border-t border-slate-100">
                  <span>Gesamtbetrag</span>
                  <span className="text-lg">{formatCHF(expense.total_amount)}</span>
                </div>
              </div>
            </div>

            {expense.notes && (
              <div className="mt-4 pt-4 border-t border-slate-100">
                <div className="text-xs text-slate-500 mb-1">Bemerkungen</div>
                <p className="text-sm text-slate-700">{expense.notes}</p>
              </div>
            )}
          </div>

          {/* Allocation breakdown */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <DivideCircle className="w-4 h-4 text-slate-400" />
              Kostenzuteilung
            </h2>
            <AllocationExplainer
              allocationMethod={expense.allocation_method}
              totalAmount={expense.total_amount}
              customSplitA={expense.custom_split_a}
              customSplitB={expense.custom_split_b}
            />
          </div>

          {/* OCR data */}
          {expense.ocr_data && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <h2 className="font-semibold text-slate-900 mb-4">OCR-Ergebnis</h2>
              <div className="grid grid-cols-2 gap-3 text-sm">
                {expense.ocr_data.vendor && (
                  <div className="bg-slate-50 rounded p-2">
                    <div className="text-xs text-slate-500">Lieferant (OCR)</div>
                    <div className="font-medium text-slate-900">{expense.ocr_data.vendor}</div>
                  </div>
                )}
                {expense.ocr_data.amount && (
                  <div className="bg-slate-50 rounded p-2">
                    <div className="text-xs text-slate-500">Betrag (OCR)</div>
                    <div className="font-medium text-slate-900">{formatCHF(expense.ocr_data.amount)}</div>
                  </div>
                )}
                <div className="col-span-2 bg-slate-50 rounded p-2">
                  <div className="text-xs text-slate-500">Erkennungsgenauigkeit</div>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="flex-1 h-2 bg-slate-200 rounded-full">
                      <div
                        className="h-full bg-green-500 rounded-full"
                        style={{ width: `${expense.ocr_data.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-xs font-medium text-slate-900">
                      {(expense.ocr_data.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Receipt preview */}
          {expense.receipt_url && (
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
                <FileText className="w-4 h-4 text-slate-400" />
                Beleg
              </h2>
              <a
                href={expense.receipt_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-red-600 hover:underline flex items-center gap-2"
              >
                <FileText className="w-4 h-4" />
                {expense.receipt_filename ?? 'Beleg anzeigen'}
              </a>
            </div>
          )}
        </div>

        {/* Sidebar: Audit log */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <h3 className="font-semibold text-slate-900 mb-4 flex items-center gap-2 text-sm">
              <Clock className="w-4 h-4 text-slate-400" />
              Aktivitätsprotokoll
            </h3>
            {auditLog.length === 0 ? (
              <p className="text-xs text-slate-400">Keine Aktivitäten</p>
            ) : (
              <div className="space-y-3">
                {auditLog.map((log) => (
                  <div key={log.id} className="flex gap-2.5">
                    <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <User className="w-3 h-3 text-slate-500" />
                    </div>
                    <div>
                      <div className="text-xs font-medium text-slate-900">{log.action}</div>
                      <div className="text-xs text-slate-500">{log.performed_by?.full_name}</div>
                      <div className="text-xs text-slate-400">{formatDate(log.created_at)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {expense.approved_by && (
            <div className="bg-green-50 rounded-xl border border-green-200 p-4">
              <div className="flex items-center gap-2 text-green-700 text-sm font-medium mb-1">
                <CheckCircle2 className="w-4 h-4" />
                Genehmigt
              </div>
              <div className="text-xs text-green-600">
                {expense.approved_by.full_name}
                {expense.approved_at && <> · {formatDate(expense.approved_at)}</>}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reject dialog */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Ausgabe ablehnen</DialogTitle>
            <DialogDescription>Bitte geben Sie einen Grund für die Ablehnung an.</DialogDescription>
          </DialogHeader>
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Ablehnungsgrund..."
            rows={3}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 resize-none"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRejectDialog(false)}>Abbrechen</Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={isActing || !rejectReason.trim()}
            >
              Ablehnen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
