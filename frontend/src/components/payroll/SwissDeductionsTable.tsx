import { SwissDeductions } from '@/lib/types'
import { formatCHF } from '@/lib/utils'

interface SwissDeductionsTableProps {
  grossSalary: number
  deductions: SwissDeductions
  netSalary: number
  employerTotalCost: number
}

interface DeductionLine {
  label: string
  rate: string
  employeeAmount: number
  employerAmount?: number
}

export function SwissDeductionsTable({
  grossSalary,
  deductions,
  netSalary,
  employerTotalCost,
}: SwissDeductionsTableProps) {
  const employeeDeductions: DeductionLine[] = [
    { label: 'AHV (Alters- und Hinterlassenenversicherung)', rate: '5.30%', employeeAmount: deductions.ahv_employee },
    { label: 'IV (Invalidenversicherung)', rate: '0.70%', employeeAmount: deductions.iv_employee },
    { label: 'EO (Erwerbsersatzordnung)', rate: '0.25%', employeeAmount: deductions.eo_employee },
    { label: 'ALV (Arbeitslosenversicherung)', rate: '1.10%', employeeAmount: deductions.alv_employee },
    { label: 'NBU (Nichtberufsunfallversicherung)', rate: 'variabel', employeeAmount: deductions.nbu_employee },
    { label: 'BVG (Berufliche Vorsorge)', rate: 'variabel', employeeAmount: deductions.bvg_employee },
  ]

  const employerContributions: { label: string; rate: string; amount: number }[] = [
    { label: 'AHV Arbeitgeberbeitrag', rate: '5.30%', amount: deductions.ahv_employer },
    { label: 'IV Arbeitgeberbeitrag', rate: '0.70%', amount: deductions.iv_employer },
    { label: 'EO Arbeitgeberbeitrag', rate: '0.25%', amount: deductions.eo_employer },
    { label: 'ALV Arbeitgeberbeitrag', rate: '1.10%', amount: deductions.alv_employer },
    { label: 'FAK (Familienzulagen)', rate: '~1.50%', amount: deductions.fam_employer },
    { label: 'BU (Berufsunfallversicherung)', rate: 'variabel', amount: deductions.bu_employer },
    { label: 'BVG Arbeitgeberbeitrag', rate: 'variabel', amount: deductions.bvg_employer },
  ]

  const totalEmployeeDeductions = employeeDeductions.reduce((sum, d) => sum + d.employeeAmount, 0)

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200">
      {/* Gross salary */}
      <div className="bg-slate-50 px-4 py-3 border-b border-slate-200">
        <div className="flex justify-between items-center">
          <span className="font-semibold text-slate-900 text-sm">Bruttogehalt</span>
          <span className="font-bold text-slate-900 text-base">{formatCHF(grossSalary)}</span>
        </div>
      </div>

      {/* Employee deductions */}
      <div className="px-4 py-2 bg-red-50 border-b border-slate-200">
        <div className="text-xs font-semibold text-red-700 uppercase tracking-wide">Arbeitnehmerabzüge</div>
      </div>
      <div className="divide-y divide-slate-100">
        {employeeDeductions.map((line) => (
          <div key={line.label} className="flex items-center justify-between px-4 py-2.5">
            <div className="flex-1 min-w-0">
              <span className="text-sm text-slate-700">{line.label}</span>
              <span className="ml-2 text-xs text-slate-400">({line.rate})</span>
            </div>
            <span className="text-sm text-red-600 font-medium tabular-nums whitespace-nowrap ml-4">
              -{formatCHF(line.employeeAmount)}
            </span>
          </div>
        ))}
      </div>

      {/* Total deductions */}
      <div className="bg-red-50 px-4 py-2.5 border-t border-slate-200">
        <div className="flex justify-between items-center">
          <span className="text-sm font-semibold text-red-700">Total Abzüge</span>
          <span className="text-sm font-bold text-red-700">-{formatCHF(totalEmployeeDeductions)}</span>
        </div>
      </div>

      {/* Net salary */}
      <div className="bg-green-50 px-4 py-3 border-t border-slate-300">
        <div className="flex justify-between items-center">
          <span className="font-bold text-green-800 text-sm">Nettogehalt</span>
          <span className="font-bold text-green-800 text-lg">{formatCHF(netSalary)}</span>
        </div>
      </div>

      {/* Employer contributions */}
      <div className="px-4 py-2 bg-blue-50 border-t border-slate-200">
        <div className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Arbeitgeberbeiträge</div>
      </div>
      <div className="divide-y divide-slate-100">
        {employerContributions.map((line) => (
          <div key={line.label} className="flex items-center justify-between px-4 py-2.5">
            <div className="flex-1 min-w-0">
              <span className="text-sm text-slate-700">{line.label}</span>
              <span className="ml-2 text-xs text-slate-400">({line.rate})</span>
            </div>
            <span className="text-sm text-blue-600 font-medium tabular-nums whitespace-nowrap ml-4">
              {formatCHF(line.amount)}
            </span>
          </div>
        ))}
      </div>

      {/* Total employer cost */}
      <div className="bg-blue-50 px-4 py-3 border-t border-slate-300">
        <div className="flex justify-between items-center">
          <span className="font-bold text-blue-800 text-sm">Gesamtkosten Arbeitgeber</span>
          <span className="font-bold text-blue-800 text-lg">{formatCHF(employerTotalCost)}</span>
        </div>
      </div>
    </div>
  )
}
