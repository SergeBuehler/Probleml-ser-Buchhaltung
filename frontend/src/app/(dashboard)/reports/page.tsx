'use client'

import { useState } from 'react'
import {
  BarChart3, FileSpreadsheet, FileText, Download, Clock, RefreshCw
} from 'lucide-react'
import { reportsApi } from '@/lib/api'
import { ReportType } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'

interface ReportOption {
  type: ReportType
  label: string
  description: string
  icon: React.ElementType
  color: string
  bgColor: string
}

const REPORT_OPTIONS: ReportOption[] = [
  {
    type: 'annual_report',
    label: 'Jahresbericht',
    description: 'Vollständige Jahresübersicht mit Einnahmen, Ausgaben und Verteilung',
    icon: BarChart3,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },
  {
    type: 'payroll_report',
    label: 'Lohnbericht',
    description: 'Alle Lohnzahlungen mit Abzügen und Arbeitgeberbeiträgen',
    icon: FileText,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  {
    type: 'cost_allocation',
    label: 'Kostenzuteilung',
    description: 'Detaillierte Aufschlüsselung der Ausgaben nach Verwalter',
    icon: FileSpreadsheet,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
  },
  {
    type: 'bank_reconciliation',
    label: 'Bankabstimmung',
    description: 'Status aller Bankkonten und Abstimmungsbericht',
    icon: FileText,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
  },
  {
    type: 'audit_report',
    label: 'Revisionsbericht',
    description: 'Prüfungsbereiter Bericht mit allen Belegen und Nachweisen',
    icon: FileText,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
  },
  {
    type: 'revenue_summary',
    label: 'Einnahmenübersicht',
    description: 'Zusammenfassung aller Einnahmen nach Liegenschaft',
    icon: BarChart3,
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
  },
]

interface RecentExport {
  id: string
  label: string
  format: string
  year: number
  date: string
  size: string
}

export default function ReportsPage() {
  const currentYear = new Date().getFullYear()
  const [selectedType, setSelectedType] = useState<ReportType>('annual_report')
  const [selectedYear, setSelectedYear] = useState(currentYear)
  const [managerFilter, setManagerFilter] = useState<'all' | 'manager_a' | 'manager_b'>('all')
  const [isGenerating, setIsGenerating] = useState(false)
  const [isExporting, setIsExporting] = useState<string | null>(null)
  const [recentExports] = useState<RecentExport[]>([
    { id: '1', label: 'Jahresbericht 2025', format: 'PDF', year: 2025, date: '10.05.2026', size: '2.4 MB' },
    { id: '2', label: 'Lohnbericht 2025', format: 'XLSX', year: 2025, date: '10.05.2026', size: '450 KB' },
    { id: '3', label: 'Kostenzuteilung Q1 2026', format: 'PDF', year: 2026, date: '05.04.2026', size: '1.1 MB' },
  ])

  const selectedOption = REPORT_OPTIONS.find(r => r.type === selectedType)!

  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      const result = await reportsApi.generateReport({
        type: selectedType,
        year: selectedYear,
        manager_filter: managerFilter,
        include_details: true,
      })
      toast.success('Bericht erfolgreich erstellt')
      // Open report URL if available
      if (result.report_url) {
        window.open(result.report_url, '_blank')
      }
    } catch {
      toast.error('Fehler beim Erstellen des Berichts')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleExportExcel = async () => {
    setIsExporting('excel')
    try {
      const blob = await reportsApi.exportExcel(selectedYear, selectedType)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `immo-${selectedType}-${selectedYear}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Excel-Export heruntergeladen')
    } catch {
      toast.error('Fehler beim Excel-Export')
    } finally {
      setIsExporting(null)
    }
  }

  const handleExportPDF = async () => {
    setIsExporting('pdf')
    try {
      const blob = await reportsApi.exportPDF(selectedYear, selectedType)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `immo-${selectedType}-${selectedYear}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      toast.success('PDF-Export heruntergeladen')
    } catch {
      toast.error('Fehler beim PDF-Export')
    } finally {
      setIsExporting(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">Berichte</h1>
        <p className="text-sm text-slate-500 mt-0.5">Erstellen und exportieren Sie Berichte</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Report selector + config */}
        <div className="xl:col-span-1 space-y-4">
          {/* Report types */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <h2 className="font-semibold text-slate-900 mb-3 text-sm">Berichtstyp</h2>
            <div className="space-y-1.5">
              {REPORT_OPTIONS.map((option) => {
                const Icon = option.icon
                return (
                  <button
                    key={option.type}
                    onClick={() => setSelectedType(option.type)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-sm flex items-center gap-3 transition-colors ${
                      selectedType === option.type
                        ? `${option.bgColor} border border-current ${option.color}`
                        : 'hover:bg-slate-50 text-slate-700 border border-transparent'
                    }`}
                  >
                    <div className={`w-7 h-7 rounded-md flex items-center justify-center ${option.bgColor}`}>
                      <Icon className={`w-4 h-4 ${option.color}`} />
                    </div>
                    <span className="font-medium">{option.label}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Filters */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-3">
            <h2 className="font-semibold text-slate-900 text-sm">Filter</h2>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Jahr</label>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="w-full text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                {[currentYear, currentYear - 1, currentYear - 2].map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">Verwalter</label>
              <select
                value={managerFilter}
                onChange={(e) => setManagerFilter(e.target.value as typeof managerFilter)}
                className="w-full text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value="all">Alle Verwalter</option>
                <option value="manager_a">Verwalter A</option>
                <option value="manager_b">Verwalter B</option>
              </select>
            </div>
          </div>
        </div>

        {/* Preview + actions */}
        <div className="xl:col-span-2 space-y-4">
          {/* Selected report info */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-start gap-4 mb-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${selectedOption.bgColor}`}>
                <selectedOption.icon className={`w-6 h-6 ${selectedOption.color}`} />
              </div>
              <div className="flex-1">
                <h2 className="font-semibold text-slate-900 text-lg">{selectedOption.label}</h2>
                <p className="text-sm text-slate-500 mt-0.5">{selectedOption.description}</p>
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="outline">{selectedYear}</Badge>
                  {managerFilter !== 'all' && (
                    <Badge variant="secondary">
                      {managerFilter === 'manager_a' ? 'Verwalter A' : 'Verwalter B'}
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            {/* Generate + Export buttons */}
            <div className="flex flex-wrap gap-2">
              <Button onClick={handleGenerate} disabled={isGenerating}>
                <RefreshCw className={`w-4 h-4 mr-2 ${isGenerating ? 'animate-spin' : ''}`} />
                {isGenerating ? 'Wird erstellt...' : 'Bericht erstellen'}
              </Button>
              <Button
                variant="outline"
                onClick={handleExportExcel}
                disabled={isExporting !== null}
              >
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                {isExporting === 'excel' ? 'Exportiert...' : 'Excel (.xlsx)'}
              </Button>
              <Button
                variant="outline"
                onClick={handleExportPDF}
                disabled={isExporting !== null}
              >
                <FileText className="w-4 h-4 mr-2" />
                {isExporting === 'pdf' ? 'Exportiert...' : 'PDF'}
              </Button>
            </div>
          </div>

          {/* Preview placeholder */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h3 className="font-semibold text-slate-900 mb-4">Berichtsvorschau</h3>
            <div className="border-2 border-dashed border-slate-200 rounded-lg p-12 text-center">
              <BarChart3 className="w-10 h-10 mx-auto mb-3 text-slate-300" />
              <p className="text-sm text-slate-400">
                Klicken Sie auf &quot;Bericht erstellen&quot; um eine Vorschau zu generieren
              </p>
            </div>
          </div>

          {/* Recent exports */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100">
              <h3 className="font-semibold text-slate-900">Letzte Exporte</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {recentExports.map((exp) => (
                <div key={exp.id} className="flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                      {exp.format === 'PDF' ? (
                        <FileText className="w-4 h-4 text-red-600" />
                      ) : (
                        <FileSpreadsheet className="w-4 h-4 text-green-600" />
                      )}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-slate-900">{exp.label}</div>
                      <div className="text-xs text-slate-500 flex items-center gap-2">
                        <Clock className="w-3 h-3" />
                        {exp.date} · {exp.size}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{exp.format}</Badge>
                    <Button variant="ghost" size="icon" className="h-7 w-7">
                      <Download className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
