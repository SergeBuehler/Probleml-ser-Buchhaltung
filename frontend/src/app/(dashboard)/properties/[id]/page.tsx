'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Building2, Edit2, FileText, Upload, MapPin, Calendar, User, Clock } from 'lucide-react'
import Link from 'next/link'
import { propertiesApi } from '@/lib/api'
import { Property } from '@/lib/types'
import { formatCHF, formatDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { PropertyForm } from '@/components/forms/PropertyForm'
import { RevenueCalculator } from '@/components/properties/RevenueCalculator'
import { toast } from 'sonner'

const STATUS_LABELS: Record<string, string> = {
  active: 'Aktiv',
  inactive: 'Inaktiv',
  pending: 'Ausstehend',
}

const TYPE_LABELS: Record<string, string> = {
  residential: 'Wohnliegenschaft',
  commercial: 'Gewerbeliegenschaft',
  mixed: 'Gemischte Liegenschaft',
  industrial: 'Industrie',
}

export default function PropertyDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [property, setProperty] = useState<Property | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showEditDialog, setShowEditDialog] = useState(false)

  useEffect(() => {
    if (params.id) {
      loadProperty(Number(params.id))
    }
  }, [params.id])

  const loadProperty = async (id: number) => {
    setIsLoading(true)
    try {
      const p = await propertiesApi.getProperty(id)
      setProperty(p)
    } catch {
      toast.error('Liegenschaft nicht gefunden')
      router.push('/dashboard/properties')
    } finally {
      setIsLoading(false)
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

  if (!property) return null

  return (
    <div className="space-y-5 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/dashboard/properties">
              <ArrowLeft className="w-4 h-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-900">{property.name}</h1>
            <div className="flex items-center gap-2 mt-0.5">
              <Badge variant={property.status === 'active' ? 'success' : 'secondary'}>
                {STATUS_LABELS[property.status]}
              </Badge>
              <span className="text-xs text-slate-500">{TYPE_LABELS[property.property_type]}</span>
            </div>
          </div>
        </div>
        <Button onClick={() => setShowEditDialog(true)}>
          <Edit2 className="w-4 h-4 mr-2" />
          Bearbeiten
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Main info */}
        <div className="lg:col-span-2 space-y-5">
          {/* Property details */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
              <Building2 className="w-4 h-4 text-slate-400" />
              Liegenschaftsdetails
            </h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-slate-500 mb-1 flex items-center gap-1.5">
                  <MapPin className="w-3 h-3" /> Adresse
                </div>
                <div className="text-sm text-slate-900">
                  {property.address}<br />
                  {property.postal_code} {property.city}, {property.canton}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1 flex items-center gap-1.5">
                  <User className="w-3 h-3" /> Verwalter
                </div>
                <div className="text-sm text-slate-900">
                  {property.assigned_manager?.full_name}
                  <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-medium">
                    {property.assigned_manager?.manager_label}
                  </span>
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1 flex items-center gap-1.5">
                  <Calendar className="w-3 h-3" /> Verwaltungsbeginn
                </div>
                <div className="text-sm text-slate-900">{formatDate(property.management_start_date)}</div>
              </div>
              {property.management_end_date && (
                <div>
                  <div className="text-xs text-slate-500 mb-1">Verwaltungsende</div>
                  <div className="text-sm text-slate-900">{formatDate(property.management_end_date)}</div>
                </div>
              )}
              <div>
                <div className="text-xs text-slate-500 mb-1">Jahresverwaltungsgebühr</div>
                <div className="text-lg font-bold text-slate-900">{formatCHF(property.annual_management_fee)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">Monatliche Gebühr</div>
                <div className="text-lg font-bold text-slate-900">{formatCHF(property.annual_management_fee / 12)}</div>
              </div>
            </div>

            {property.notes && (
              <div className="mt-4 pt-4 border-t border-slate-100">
                <div className="text-xs text-slate-500 mb-1">Bemerkungen</div>
                <p className="text-sm text-slate-700">{property.notes}</p>
              </div>
            )}
          </div>

          {/* Revenue calculator */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h2 className="font-semibold text-slate-900 mb-4">Einnahmenberechnung</h2>
            <RevenueCalculator
              annualFee={property.annual_management_fee}
              startDate={property.management_start_date}
            />
          </div>

          {/* Documents */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-slate-900 flex items-center gap-2">
                <FileText className="w-4 h-4 text-slate-400" />
                Dokumente
              </h2>
              <Button variant="outline" size="sm">
                <Upload className="w-3.5 h-3.5 mr-1.5" />
                Hochladen
              </Button>
            </div>
            <div className="text-sm text-slate-400 text-center py-8">
              Keine Dokumente vorhanden
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Quick stats */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
            <h3 className="font-semibold text-slate-900 text-sm">Schnellübersicht</h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Jahresgebühr</span>
                <span className="font-semibold text-slate-900">{formatCHF(property.annual_management_fee)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Monatsgebühr</span>
                <span className="font-semibold text-slate-900">{formatCHF(property.annual_management_fee / 12)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Status</span>
                <Badge variant={property.status === 'active' ? 'success' : 'secondary'} className="text-xs">
                  {STATUS_LABELS[property.status]}
                </Badge>
              </div>
            </div>
          </div>

          {/* Timestamps */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
            <h3 className="font-semibold text-slate-900 text-sm flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              Änderungshistorie
            </h3>
            <div className="space-y-2 text-xs text-slate-500">
              <div>
                <div className="text-slate-600 font-medium">Erstellt</div>
                <div>{formatDate(property.created_at)}</div>
              </div>
              <div>
                <div className="text-slate-600 font-medium">Zuletzt geändert</div>
                <div>{formatDate(property.updated_at)}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Edit dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Liegenschaft bearbeiten</DialogTitle>
          </DialogHeader>
          <PropertyForm
            defaultValues={property}
            isEdit
            propertyId={property.id}
            onSuccess={(updated) => {
              setProperty(updated)
              setShowEditDialog(false)
              toast.success('Liegenschaft aktualisiert')
            }}
          />
        </DialogContent>
      </Dialog>
    </div>
  )
}
