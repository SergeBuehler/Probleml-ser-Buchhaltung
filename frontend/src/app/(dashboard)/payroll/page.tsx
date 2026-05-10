'use client'

import { useState, useEffect } from 'react'
import { Users, FileText, Plus, ChevronDown, ChevronUp } from 'lucide-react'
import { payrollApi } from '@/lib/api'
import { Employee, PayrollPeriod, SalaryCertificate } from '@/lib/types'
import { formatCHF } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { SwissDeductionsTable } from '@/components/payroll/SwissDeductionsTable'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { toast } from 'sonner'

const MONTHS = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
]

const SWISS_RATES = {
  ahv_iv_eo_employee: 6.25, // AHV 5.3% + IV 0.7% + EO 0.25%
  alv_employee: 1.1,
  ahv_iv_eo_employer: 6.25,
  alv_employer: 1.1,
  fak_employer: 1.5,
}

export default function PayrollPage() {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [payrollPeriods, setPayrollPeriods] = useState<PayrollPeriod[]>([])
  const [certificates, setCertificates] = useState<SalaryCertificate[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null)
  const [selectedPeriod, setSelectedPeriod] = useState<PayrollPeriod | null>(null)
  const [showDeductionsDialog, setShowDeductionsDialog] = useState(false)
  const [isCalculating, setIsCalculating] = useState(false)

  const currentYear = new Date().getFullYear()
  const currentMonth = new Date().getMonth() + 1
  const [selectedYear, setSelectedYear] = useState(currentYear)
  const [selectedMonth, setSelectedMonth] = useState(currentMonth)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    loadPayrollPeriods()
  }, [selectedYear, selectedMonth])

  const loadData = async () => {
    setIsLoading(true)
    try {
      const [emps, certs] = await Promise.all([
        payrollApi.getEmployees(),
        payrollApi.getSalaryCertificates(currentYear).catch(() => []),
      ])
      setEmployees(emps)
      setCertificates(certs)
      await loadPayrollPeriods()
    } catch {
      toast.error('Fehler beim Laden der Lohndaten')
    } finally {
      setIsLoading(false)
    }
  }

  const loadPayrollPeriods = async () => {
    try {
      const response = await payrollApi.getPayrollPeriods({
        year: selectedYear,
        month: selectedMonth,
        page_size: 50,
      })
      setPayrollPeriods(response.data)
    } catch {
      // Silently fail
    }
  }

  const handleCalculate = async (employeeId: number) => {
    setIsCalculating(true)
    try {
      const period = await payrollApi.calculatePayroll(employeeId, selectedYear, selectedMonth)
      setPayrollPeriods(prev => {
        const idx = prev.findIndex(p => p.employee_id === employeeId)
        if (idx >= 0) {
          const next = [...prev]
          next[idx] = period
          return next
        }
        return [...prev, period]
      })
      toast.success('Lohnberechnung abgeschlossen')
    } catch {
      toast.error('Fehler bei der Lohnberechnung')
    } finally {
      setIsCalculating(false)
    }
  }

  const handleGenerateCertificate = async (employeeId: number) => {
    try {
      await payrollApi.generateSalaryCertificate(employeeId, selectedYear)
      toast.success('Lohnausweis erstellt')
      const certs = await payrollApi.getSalaryCertificates(selectedYear)
      setCertificates(certs)
    } catch {
      toast.error('Fehler beim Erstellen des Lohnausweises')
    }
  }

  const getPeriodForEmployee = (employeeId: number) =>
    payrollPeriods.find(p => p.employee_id === employeeId)

  const totalGross = payrollPeriods.reduce((sum, p) => sum + p.gross_salary, 0)
  const totalNet = payrollPeriods.reduce((sum, p) => sum + p.net_salary, 0)
  const totalEmployerCost = payrollPeriods.reduce((sum, p) => sum + p.employer_total_cost, 0)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Lohnbuchhaltung</h1>
          <p className="text-sm text-slate-500 mt-0.5">{employees.length} Mitarbeitende</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => handleGenerateCertificate(0)}>
            <FileText className="w-4 h-4 mr-2" />
            Lohnausweise {selectedYear}
          </Button>
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Mitarbeitende hinzufügen
          </Button>
        </div>
      </div>

      {/* Swiss rates info */}
      <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
        <h3 className="text-sm font-semibold text-blue-800 mb-2">Schweizer Lohnabzüge {currentYear}</h3>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-xs">
          {[
            { label: 'AHV/IV/EO AN', value: `${SWISS_RATES.ahv_iv_eo_employee}%` },
            { label: 'ALV AN', value: `${SWISS_RATES.alv_employee}%` },
            { label: 'AHV/IV/EO AG', value: `${SWISS_RATES.ahv_iv_eo_employer}%` },
            { label: 'ALV AG', value: `${SWISS_RATES.alv_employer}%` },
            { label: 'FAK AG', value: `~${SWISS_RATES.fak_employer}%` },
          ].map(item => (
            <div key={item.label} className="bg-white rounded-md p-2 border border-blue-100">
              <div className="text-blue-600 font-medium">{item.value}</div>
              <div className="text-slate-500">{item.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Period selector */}
      <div className="flex items-center gap-3">
        <select
          value={selectedMonth}
          onChange={(e) => setSelectedMonth(Number(e.target.value))}
          className="text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          {MONTHS.map((m, i) => (
            <option key={i + 1} value={i + 1}>{m}</option>
          ))}
        </select>
        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(Number(e.target.value))}
          className="text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          {[currentYear, currentYear - 1, currentYear - 2].map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        <span className="text-sm text-slate-600 font-medium">
          {MONTHS[selectedMonth - 1]} {selectedYear}
        </span>
      </div>

      {/* Payroll summary table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-900">Lohnabrechnung {MONTHS[selectedMonth - 1]} {selectedYear}</h2>
        </div>
        {isLoading ? (
          <div className="p-4 space-y-3">
            {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-14" />)}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Mitarbeitende/r</TableHead>
                <TableHead className="text-right">Bruttogehalt</TableHead>
                <TableHead className="text-right">AHV/IV/EO</TableHead>
                <TableHead className="text-right">ALV</TableHead>
                <TableHead className="text-right">BVG</TableHead>
                <TableHead className="text-right">Nettogehalt</TableHead>
                <TableHead className="text-right">Arbeitgeberkosten</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {employees.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-12 text-slate-400">
                    <Users className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    <p className="text-sm">Keine Mitarbeitenden erfasst</p>
                  </TableCell>
                </TableRow>
              ) : (
                employees.map((employee) => {
                  const period = getPeriodForEmployee(employee.id)
                  return (
                    <TableRow key={employee.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">
                            {employee.first_name?.[0]}{employee.last_name?.[0]}
                          </div>
                          <div>
                            <div className="text-sm font-medium text-slate-900">{employee.full_name}</div>
                            <div className="text-xs text-slate-500">{employee.work_percentage}% Pensum</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right text-sm font-medium">
                        {formatCHF(period?.gross_salary ?? employee.gross_monthly_salary)}
                      </TableCell>
                      <TableCell className="text-right text-sm text-red-600">
                        {period ? `-${formatCHF(period.deductions.ahv_employee + period.deductions.iv_employee + period.deductions.eo_employee)}` : '-'}
                      </TableCell>
                      <TableCell className="text-right text-sm text-red-600">
                        {period ? `-${formatCHF(period.deductions.alv_employee)}` : '-'}
                      </TableCell>
                      <TableCell className="text-right text-sm text-red-600">
                        {period ? `-${formatCHF(period.deductions.bvg_employee)}` : '-'}
                      </TableCell>
                      <TableCell className="text-right text-sm font-bold text-green-700">
                        {period ? formatCHF(period.net_salary) : '-'}
                      </TableCell>
                      <TableCell className="text-right text-sm font-bold text-blue-700">
                        {period ? formatCHF(period.employer_total_cost) : '-'}
                      </TableCell>
                      <TableCell>
                        {period ? (
                          <Badge variant={period.status === 'paid' ? 'success' : period.status === 'calculated' ? 'info' : 'secondary'}>
                            {period.status === 'paid' ? 'Bezahlt' : period.status === 'calculated' ? 'Berechnet' : 'Entwurf'}
                          </Badge>
                        ) : (
                          <Badge variant="outline">Ausstehend</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleCalculate(employee.id)}
                            disabled={isCalculating}
                          >
                            Berechnen
                          </Button>
                          {period && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setSelectedEmployee(employee)
                                setSelectedPeriod(period)
                                setShowDeductionsDialog(true)
                              }}
                            >
                              Details
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        )}

        {/* Summary footer */}
        {payrollPeriods.length > 0 && (
          <div className="bg-slate-50 border-t border-slate-200 px-4 py-3 grid grid-cols-3 gap-4">
            <div>
              <div className="text-xs text-slate-500">Total Brutto</div>
              <div className="font-bold text-slate-900">{formatCHF(totalGross)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Total Netto</div>
              <div className="font-bold text-green-700">{formatCHF(totalNet)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Total Arbeitgeberkosten</div>
              <div className="font-bold text-blue-700">{formatCHF(totalEmployerCost)}</div>
            </div>
          </div>
        )}
      </div>

      {/* Vacation + 13th salary accruals */}
      {payrollPeriods.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-3">Ferienguthaben (Rückstellung)</h3>
            <div className="space-y-2">
              {payrollPeriods.map(p => (
                <div key={p.id} className="flex justify-between text-sm">
                  <span className="text-slate-600">{p.employee.full_name}</span>
                  <span className="font-medium text-slate-900">{formatCHF(p.vacation_accrual)}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-3">13. Monatslohn (Rückstellung)</h3>
            <div className="space-y-2">
              {payrollPeriods.map(p => (
                <div key={p.id} className="flex justify-between text-sm">
                  <span className="text-slate-600">{p.employee.full_name}</span>
                  <span className="font-medium text-slate-900">{formatCHF(p.thirteenth_salary_accrual)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Deductions detail dialog */}
      <Dialog open={showDeductionsDialog} onOpenChange={setShowDeductionsDialog}>
        <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Lohndetails – {selectedEmployee?.full_name}</DialogTitle>
          </DialogHeader>
          {selectedPeriod && (
            <SwissDeductionsTable
              grossSalary={selectedPeriod.gross_salary}
              deductions={selectedPeriod.deductions}
              netSalary={selectedPeriod.net_salary}
              employerTotalCost={selectedPeriod.employer_total_cost}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
