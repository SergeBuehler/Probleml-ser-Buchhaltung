'use client'

import { useState, useEffect } from 'react'
import { Plus, Search, Building2, Edit2, Trash2, Eye } from 'lucide-react'
import Link from 'next/link'
import { propertiesApi } from '@/lib/api'
import { Property } from '@/lib/types'
import { formatCHF, formatDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell, TableFooter
} from '@/components/ui/table'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from '@/components/ui/dialog'
import { toast } from 'sonner'

const STATUS_LABELS: Record<string, string> = {
  active: 'Aktiv',
  inactive: 'Inaktiv',
  pending: 'Ausstehend',
}

const TYPE_LABELS: Record<string, string> = {
  residential: 'Wohnen',
  commercial: 'Gewerbe',
  mixed: 'Gemischt',
  industrial: 'Industrie',
}

export default function PropertiesPage() {
  const [properties, setProperties] = useState<Property[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [managerFilter, setManagerFilter] = useState('all')
  const [deleteTarget, setDeleteTarget] = useState<Property | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    loadProperties()
  }, [])

  const loadProperties = async () => {
    setIsLoading(true)
    try {
      const response = await propertiesApi.getProperties({ page_size: 100 })
      setProperties(response.data)
    } catch {
      toast.error('Fehler beim Laden der Liegenschaften')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setIsDeleting(true)
    try {
      await propertiesApi.deleteProperty(deleteTarget.id)
      setProperties(prev => prev.filter(p => p.id !== deleteTarget.id))
      toast.success('Liegenschaft gelöscht')
      setDeleteTarget(null)
    } catch {
      toast.error('Fehler beim Löschen der Liegenschaft')
    } finally {
      setIsDeleting(false)
    }
  }

  const filtered = properties.filter(p => {
    const matchSearch = !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.address.toLowerCase().includes(search.toLowerCase()) ||
      p.city.toLowerCase().includes(search.toLowerCase())
    const matchManager = managerFilter === 'all' ||
      p.assigned_manager?.manager_label === managerFilter
    return matchSearch && matchManager
  })

  const totalAnnualRevenue = filtered.reduce((sum, p) => sum + p.annual_management_fee, 0)
  const managerARevenue = filtered
    .filter(p => p.assigned_manager?.manager_label === 'A')
    .reduce((sum, p) => sum + p.annual_management_fee, 0)
  const managerBRevenue = filtered
    .filter(p => p.assigned_manager?.manager_label === 'B')
    .reduce((sum, p) => sum + p.annual_management_fee, 0)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Liegenschaften</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {properties.length} Liegenschaften verwaltet
          </p>
        </div>
        <Button asChild>
          <Link href="/dashboard/properties/new">
            <Plus className="w-4 h-4 mr-2" />
            Neue Liegenschaft
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Suchen..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <select
          value={managerFilter}
          onChange={(e) => setManagerFilter(e.target.value)}
          className="text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="all">Alle Verwalter</option>
          <option value="A">Verwalter A</option>
          <option value="B">Verwalter B</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12" />)}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Liegenschaft</TableHead>
                <TableHead>Verwalter</TableHead>
                <TableHead>Typ</TableHead>
                <TableHead>Start</TableHead>
                <TableHead className="text-right">Monatsgebühr</TableHead>
                <TableHead className="text-right">Jahresgebühr</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Aktionen</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-12 text-slate-400">
                    <Building2 className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p className="text-sm">Keine Liegenschaften gefunden</p>
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((property) => (
                  <TableRow key={property.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium text-slate-900">{property.name}</div>
                        <div className="text-xs text-slate-500">{property.address}, {property.city}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-xs font-bold text-blue-700">
                          {property.assigned_manager?.manager_label ?? '?'}
                        </div>
                        <span className="text-sm text-slate-700">{property.assigned_manager?.full_name ?? '-'}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-slate-600">{TYPE_LABELS[property.property_type] ?? property.property_type}</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-slate-600">{formatDate(property.management_start_date)}</span>
                    </TableCell>
                    <TableCell className="text-right font-medium text-slate-900">
                      {formatCHF(property.annual_management_fee / 12)}
                    </TableCell>
                    <TableCell className="text-right font-semibold text-slate-900">
                      {formatCHF(property.annual_management_fee)}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          property.status === 'active' ? 'success' :
                          property.status === 'pending' ? 'warning' : 'secondary'
                        }
                      >
                        {STATUS_LABELS[property.status]}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Link href={`/dashboard/properties/${property.id}`}>
                          <button className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors">
                            <Eye className="w-4 h-4" />
                          </button>
                        </Link>
                        <Link href={`/dashboard/properties/${property.id}`}>
                          <button className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded transition-colors">
                            <Edit2 className="w-4 h-4" />
                          </button>
                        </Link>
                        <button
                          onClick={() => setDeleteTarget(property)}
                          className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
            {filtered.length > 0 && (
              <TableFooter>
                <TableRow>
                  <TableCell colSpan={4} className="font-semibold text-slate-700">
                    Total ({filtered.length} Liegenschaften)
                  </TableCell>
                  <TableCell className="text-right font-semibold text-slate-900">
                    {formatCHF(totalAnnualRevenue / 12)}
                  </TableCell>
                  <TableCell className="text-right font-bold text-slate-900">
                    {formatCHF(totalAnnualRevenue)}
                  </TableCell>
                  <TableCell colSpan={2} />
                </TableRow>
                <TableRow>
                  <TableCell colSpan={4} className="text-sm text-blue-700 font-medium">
                    Verwalter A
                  </TableCell>
                  <TableCell className="text-right text-sm text-blue-700">
                    {formatCHF(managerARevenue / 12)}
                  </TableCell>
                  <TableCell className="text-right text-sm font-semibold text-blue-700">
                    {formatCHF(managerARevenue)}
                  </TableCell>
                  <TableCell colSpan={2} />
                </TableRow>
                <TableRow>
                  <TableCell colSpan={4} className="text-sm text-orange-600 font-medium">
                    Verwalter B
                  </TableCell>
                  <TableCell className="text-right text-sm text-orange-600">
                    {formatCHF(managerBRevenue / 12)}
                  </TableCell>
                  <TableCell className="text-right text-sm font-semibold text-orange-600">
                    {formatCHF(managerBRevenue)}
                  </TableCell>
                  <TableCell colSpan={2} />
                </TableRow>
              </TableFooter>
            )}
          </Table>
        )}
      </div>

      {/* Delete confirmation */}
      <Dialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Liegenschaft löschen</DialogTitle>
            <DialogDescription>
              Sind Sie sicher, dass Sie die Liegenschaft <strong>{deleteTarget?.name}</strong> löschen möchten? Diese Aktion kann nicht rückgängig gemacht werden.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Abbrechen</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? 'Wird gelöscht...' : 'Löschen'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
