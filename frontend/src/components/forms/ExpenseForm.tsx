'use client'

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ExpenseFormData, AllocationMethod } from '@/lib/types'
import { expensesApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { AllocationExplainer } from '@/components/expenses/AllocationExplainer'
import { toast } from 'sonner'

const expenseSchema = z.object({
  title: z.string().min(2, 'Titel eingeben'),
  vendor: z.string().min(2, 'Lieferant eingeben'),
  amount: z.coerce.number().min(0.01, 'Betrag eingeben'),
  vat_rate: z.coerce.number().min(0).max(100),
  expense_date: z.string().min(1, 'Datum eingeben'),
  category: z.string().min(1, 'Kategorie wählen'),
  allocation_method: z.string().min(1, 'Zuteilungsmethode wählen'),
  custom_split_a: z.coerce.number().optional(),
  custom_split_b: z.coerce.number().optional(),
  notes: z.string().optional(),
})

type ExpenseFormValues = z.infer<typeof expenseSchema>

const CATEGORIES = [
  { value: 'maintenance', label: 'Unterhalt' },
  { value: 'repair', label: 'Reparaturen' },
  { value: 'insurance', label: 'Versicherung' },
  { value: 'utilities', label: 'Nebenkosten' },
  { value: 'management', label: 'Verwaltung' },
  { value: 'legal', label: 'Rechtliches' },
  { value: 'accounting', label: 'Buchhaltung' },
  { value: 'cleaning', label: 'Reinigung' },
  { value: 'landscaping', label: 'Gartenpflege' },
  { value: 'advertising', label: 'Werbung' },
  { value: 'office', label: 'Büro' },
  { value: 'travel', label: 'Reisen' },
  { value: 'other', label: 'Sonstiges' },
]

const ALLOCATION_METHODS = [
  { value: 'split_equal', label: 'Gleichmässig (50/50)' },
  { value: 'split_by_revenue', label: 'Nach Einnahmenanteil' },
  { value: 'manager_a_only', label: 'Nur Verwalter A' },
  { value: 'manager_b_only', label: 'Nur Verwalter B' },
  { value: 'split_custom', label: 'Benutzerdefiniert' },
]

const VAT_RATES = [
  { value: '0', label: '0% (MwSt-befreit)' },
  { value: '2.6', label: '2.6% (reduzierter Satz)' },
  { value: '3.8', label: '3.8% (Sondersatz Beherbergung)' },
  { value: '8.1', label: '8.1% (Normalsatz)' },
]

interface ExpenseFormProps {
  onSuccess?: () => void
  defaultValues?: Partial<ExpenseFormData>
  uploadedFileUrl?: string
}

export function ExpenseForm({ onSuccess, defaultValues, uploadedFileUrl }: ExpenseFormProps) {
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<ExpenseFormValues>({
    resolver: zodResolver(expenseSchema),
    defaultValues: {
      title: defaultValues?.title ?? '',
      vendor: defaultValues?.vendor ?? '',
      amount: defaultValues?.amount ?? 0,
      vat_rate: defaultValues?.vat_rate ?? 8.1,
      expense_date: defaultValues?.expense_date ?? new Date().toISOString().split('T')[0],
      category: defaultValues?.category ?? '',
      allocation_method: defaultValues?.allocation_method ?? 'split_equal',
      notes: defaultValues?.notes ?? '',
    },
  })

  const watchedAmount = watch('amount')
  const watchedVatRate = watch('vat_rate')
  const watchedAllocation = watch('allocation_method') as AllocationMethod
  const watchedCustomA = watch('custom_split_a')
  const watchedCustomB = watch('custom_split_b')

  const vatAmount = watchedAmount * (watchedVatRate / 100)
  const totalAmount = watchedAmount + vatAmount

  // Auto-calc custom split B
  useEffect(() => {
    if (watchedCustomA !== undefined) {
      setValue('custom_split_b', 100 - (watchedCustomA ?? 0))
    }
  }, [watchedCustomA, setValue])

  const onSubmit = async (data: ExpenseFormValues) => {
    setIsLoading(true)
    try {
      await expensesApi.createExpense({
        ...data,
        category: data.category as ExpenseFormData['category'],
        allocation_method: data.allocation_method as AllocationMethod,
      })
      toast.success('Ausgabe erstellt')
      onSuccess?.()
    } catch {
      toast.error('Fehler beim Erstellen der Ausgabe')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {/* Title + Vendor */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="title">Titel *</Label>
          <Input id="title" placeholder="Heizkostenabrechnung" {...register('title')} className="mt-1.5" />
          {errors.title && <p className="text-xs text-red-600 mt-1">{errors.title.message}</p>}
        </div>
        <div>
          <Label htmlFor="vendor">Lieferant *</Label>
          <Input id="vendor" placeholder="Stadtwerke AG" {...register('vendor')} className="mt-1.5" />
          {errors.vendor && <p className="text-xs text-red-600 mt-1">{errors.vendor.message}</p>}
        </div>
      </div>

      {/* Amount + VAT + Date */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <Label htmlFor="amount">Betrag (CHF) *</Label>
          <Input id="amount" type="number" step="0.01" placeholder="0.00" {...register('amount')} className="mt-1.5" />
          {errors.amount && <p className="text-xs text-red-600 mt-1">{errors.amount.message}</p>}
        </div>
        <div>
          <Label htmlFor="vat_rate">MwSt-Satz</Label>
          <select
            id="vat_rate"
            {...register('vat_rate')}
            className="mt-1.5 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {VAT_RATES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>
        <div>
          <Label htmlFor="expense_date">Datum *</Label>
          <Input id="expense_date" type="date" {...register('expense_date')} className="mt-1.5" />
          {errors.expense_date && <p className="text-xs text-red-600 mt-1">{errors.expense_date.message}</p>}
        </div>
      </div>

      {/* Amount breakdown */}
      {watchedAmount > 0 && (
        <div className="bg-slate-50 rounded-lg p-3 text-xs space-y-1 border border-slate-200">
          <div className="flex justify-between text-slate-600">
            <span>Nettobetrag</span>
            <span className="font-medium">CHF {watchedAmount.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>MwSt ({watchedVatRate}%)</span>
            <span className="font-medium">CHF {vatAmount.toFixed(2)}</span>
          </div>
          <div className="flex justify-between font-semibold text-slate-900 pt-1 border-t border-slate-300">
            <span>Gesamtbetrag</span>
            <span>CHF {totalAmount.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Category + Allocation */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="category">Kategorie *</Label>
          <select
            id="category"
            {...register('category')}
            className="mt-1.5 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value="">Kategorie wählen</option>
            {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          {errors.category && <p className="text-xs text-red-600 mt-1">{errors.category.message}</p>}
        </div>
        <div>
          <Label htmlFor="allocation_method">Kostenzuteilung *</Label>
          <select
            id="allocation_method"
            {...register('allocation_method')}
            className="mt-1.5 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {ALLOCATION_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
        </div>
      </div>

      {/* Custom split */}
      {watchedAllocation === 'split_custom' && (
        <div className="grid grid-cols-2 gap-4 bg-slate-50 rounded-lg p-3">
          <div>
            <Label htmlFor="custom_split_a">Verwalter A (%)</Label>
            <Input
              id="custom_split_a"
              type="number"
              min={0}
              max={100}
              {...register('custom_split_a')}
              className="mt-1.5"
            />
          </div>
          <div>
            <Label htmlFor="custom_split_b">Verwalter B (%)</Label>
            <Input
              id="custom_split_b"
              type="number"
              min={0}
              max={100}
              readOnly
              value={100 - (watchedCustomA ?? 50)}
              className="mt-1.5 bg-slate-100"
            />
          </div>
        </div>
      )}

      {/* Allocation preview */}
      {totalAmount > 0 && (
        <AllocationExplainer
          allocationMethod={watchedAllocation}
          totalAmount={totalAmount}
          customSplitA={watchedCustomA}
          customSplitB={watchedCustomB}
        />
      )}

      {/* Notes */}
      <div>
        <Label htmlFor="notes">Bemerkungen</Label>
        <textarea
          id="notes"
          rows={3}
          placeholder="Optionale Notizen..."
          {...register('notes')}
          className="mt-1.5 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500 resize-none"
        />
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? 'Wird gespeichert...' : 'Ausgabe zur Genehmigung einreichen'}
        </Button>
      </div>
    </form>
  )
}
