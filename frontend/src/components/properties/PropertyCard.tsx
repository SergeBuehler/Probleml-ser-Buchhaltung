import { Building2, MapPin, Calendar, TrendingUp } from 'lucide-react'
import { Property } from '@/lib/types'
import { formatCHF, formatDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'

interface PropertyCardProps {
  property: Property
}

const statusLabels: Record<string, string> = {
  active: 'Aktiv',
  inactive: 'Inaktiv',
  pending: 'Ausstehend',
}

const typeLabels: Record<string, string> = {
  residential: 'Wohnen',
  commercial: 'Gewerbe',
  mixed: 'Gemischt',
  industrial: 'Industrie',
}

export function PropertyCard({ property }: PropertyCardProps) {
  return (
    <Link href={`/dashboard/properties/${property.id}`}>
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-slate-300 transition-all cursor-pointer group">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center group-hover:bg-blue-100 transition-colors">
              <Building2 className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-slate-900 group-hover:text-blue-700 transition-colors">
                {property.name}
              </h3>
              <Badge variant={property.status === 'active' ? 'success' : property.status === 'pending' ? 'warning' : 'secondary'}>
                {statusLabels[property.status]}
              </Badge>
            </div>
          </div>
          <Badge variant="secondary">{typeLabels[property.property_type]}</Badge>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="truncate">{property.address}, {property.postal_code} {property.city}</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Calendar className="w-3.5 h-3.5 flex-shrink-0" />
            <span>Seit {formatDate(property.management_start_date)}</span>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-2 gap-3">
          <div>
            <div className="text-xs text-slate-500">Monatsgebühr</div>
            <div className="text-sm font-semibold text-slate-900">
              {formatCHF(property.annual_management_fee / 12)}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Jahresgebühr</div>
            <div className="text-sm font-semibold text-slate-900">
              {formatCHF(property.annual_management_fee)}
            </div>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">
            {property.assigned_manager?.manager_label ?? 'V'}
          </div>
          <span className="text-xs text-slate-500">
            {property.assigned_manager?.full_name ?? 'Unbekannter Verwalter'}
          </span>
        </div>
      </div>
    </Link>
  )
}
