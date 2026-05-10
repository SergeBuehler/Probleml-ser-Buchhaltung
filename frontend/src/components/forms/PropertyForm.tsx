'use client'

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Property, PropertyFormData } from '@/lib/types'
import { propertiesApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RevenueCalculator } from '@/components/properties/RevenueCalculator'
import { toast } from 'sonner'

const propertySchema = z.object({
  name: z.string().min(2, 'Name muss mindestens 2 Zeichen haben'),
  address: z.string().min(5, 'Adresse eingeben'),
  city: z.string().min(2, 'Stadt eingeben'),
  postal_code: z.string().min(4, 'PLZ eingeben').max(6),
  canton: z.string().min(2, 'Kanton wählen'),
  property_type: z.enum(['residential', 'commercial', 'mixed', 'industrial']),
  assigned_manager_id: z.coerce.number().min(1, 'Verwalter wählen'),
  annual_management_fee: z.coerce.number().min(1, 'Jahresgebühr eingeben'),
  management_start_date: z.string().min(1, 'Startdatum eingeben'),
  notes: z.string().optional(),
})

type PropertyFormValues = z.infer<typeof propertySchema>

interface PropertyFormProps {
  defaultValues?: Partial<Property>
  onSuccess?: (property: Property) => void
  isEdit?: boolean
  propertyId?: number
}

const CANTONS = [
  'AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR',
  'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'SZ', 'TG',
  'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH',
]

export function PropertyForm({ defaultValues, onSuccess, isEdit, propertyId }: PropertyFormProps) {
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<PropertyFormValues>({
    resolver: zodResolver(propertySchema),
    defaultValues: {
      name: defaultValues?.name ?? '',
      address: defaultValues?.address ?? '',
      city: defaultValues?.city ?? '',
      postal_code: defaultValues?.postal_code ?? '',
      canton: defaultValues?.canton ?? 'ZH',
      property_type: defaultValues?.property_type ?? 'residential',
      assigned_manager_id: defaultValues?.assigned_manager_id ?? 0,
      annual_management_fee: defaultValues?.annual_management_fee ?? 0,
      management_start_date: defaultValues?.management_start_date ?? '',
      notes: defaultValues?.notes ?? '',
    },
  })

  const watchedFee = watch('annual_management_fee')
  const watchedStartDate = watch('management_start_date')

  const onSubmit = async (data: PropertyFormValues) => {
    setIsLoading(true)
    try {
      let result: Property
      if (isEdit && propertyId) {
        result = await propertiesApi.updateProperty(propertyId, data as PropertyFormData)
        toast.success('Liegenschaft aktualisiert')
      } else {
        result = await propertiesApi.createProperty(data as PropertyFormData)
        toast.success('Liegenschaft erstellt')
      }
      onSuccess?.(result)
    } catch {
      toast.error('Fehler beim Speichern der Liegenschaft')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      {/* Name */}
      <div>
        <Label htmlFor="name">Liegenschaftsname *</Label>
        <Input
          id="name"
          placeholder="z.B. Überbauung Musterweg"
          {...register('name')}
          className="mt-1.5"
        />
        {errors.name && <p className="text-xs text-red-600 mt-1">{errors.name.message}</p>}
      </div>

      {/* Address */}
      <div>
        <Label htmlFor="address">Strasse und Hausnummer *</Label>
        <Input
          id="address"
          placeholder="Musterstrasse 12"
          {...register('address')}
          className="mt-1.5"
        />
        {errors.address && <p className="text-xs text-red-600 mt-1">{errors.address.message}</p>}
      </div>

      {/* City + PLZ */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <Label htmlFor="postal_code">PLZ *</Label>
          <Input
            id="postal_code"
            placeholder="8001"
            {...register('postal_code')}
            className="mt-1.5"
          />
          {errors.postal_code && <p className="text-xs text-red-600 mt-1">{errors.postal_code.message}</p>}
        </div>
        <div className="col-span-2">
          <Label htmlFor="city">Ort *</Label>
          <Input
            id="city"
            placeholder="Zürich"
            {...register('city')}
            className="mt-1.5"
          />
          {errors.city && <p className="text-xs text-red-600 mt-1">{errors.city.message}</p>}
        </div>
      </div>

      {/* Canton + Type */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="canton">Kanton *</Label>
          <select
            id="canton"
            {...register('canton')}
            className="mt-1.5 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            {CANTONS.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          {errors.canton && <p className="text-xs text-red-600 mt-1">{errors.canton.message}</p>}
        </div>
        <div>
          <Label htmlFor="property_type">Liegenschaftstyp *</Label>
          <select
            id="property_type"
            {...register('property_type')}
            className="mt-1.5 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value="residential">Wohnen</option>
            <option value="commercial">Gewerbe</option>
            <option value="mixed">Gemischt</option>
            <option value="industrial">Industrie</option>
          </select>
        </div>
      </div>

      {/* Manager + Fee */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="assigned_manager_id">Zugewiesener Verwalter *</Label>
          <select
            id="assigned_manager_id"
            {...register('assigned_manager_id')}
            className="mt-1.5 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value={0}>Verwalter wählen</option>
            <option value={1}>Verwalter A</option>
            <option value={2}>Verwalter B</option>
          </select>
          {errors.assigned_manager_id && (
            <p className="text-xs text-red-600 mt-1">{errors.assigned_manager_id.message}</p>
          )}
        </div>
        <div>
          <Label htmlFor="annual_management_fee">Jahresverwaltungsgebühr (CHF) *</Label>
          <Input
            id="annual_management_fee"
            type="number"
            step="0.01"
            placeholder="12000.00"
            {...register('annual_management_fee')}
            className="mt-1.5"
          />
          {errors.annual_management_fee && (
            <p className="text-xs text-red-600 mt-1">{errors.annual_management_fee.message}</p>
          )}
        </div>
      </div>

      {/* Start date */}
      <div>
        <Label htmlFor="management_start_date">Verwaltungsbeginn *</Label>
        <Input
          id="management_start_date"
          type="date"
          {...register('management_start_date')}
          className="mt-1.5"
        />
        {errors.management_start_date && (
          <p className="text-xs text-red-600 mt-1">{errors.management_start_date.message}</p>
        )}
      </div>

      {/* Revenue preview */}
      {(watchedFee > 0 || watchedStartDate) && (
        <RevenueCalculator
          annualFee={watchedFee}
          startDate={watchedStartDate}
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
          {isLoading ? 'Wird gespeichert...' : isEdit ? 'Aktualisieren' : 'Liegenschaft erstellen'}
        </Button>
      </div>
    </form>
  )
}
