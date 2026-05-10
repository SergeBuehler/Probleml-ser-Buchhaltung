'use client'

import { useState } from 'react'
import { Building2, Users, Settings, Bell, CreditCard, Shield, Save, Plus, Trash2 } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { useAuth } from '@/lib/auth'

const CANTONS = [
  'AG', 'AI', 'AR', 'BE', 'BL', 'BS', 'FR', 'GE', 'GL', 'GR',
  'JU', 'LU', 'NE', 'NW', 'OW', 'SG', 'SH', 'SO', 'SZ', 'TG',
  'TI', 'UR', 'VD', 'VS', 'ZG', 'ZH',
]

export default function SettingsPage() {
  const { user } = useAuth()
  const [isSaving, setIsSaving] = useState(false)

  const [companyForm, setCompanyForm] = useState({
    name: 'ImmoManager GmbH',
    legal_name: 'ImmoManager Liegenschaftsverwaltung GmbH',
    uid_number: 'CHE-123.456.789',
    address: 'Bahnhofstrasse 10',
    city: 'Zürich',
    postal_code: '8001',
    canton: 'ZH',
    phone: '+41 44 123 45 67',
    email: 'info@immomanager.ch',
    bank_iban: 'CH93 0076 2011 6238 5295 7',
    vat_number: 'CHE-123.456.789 MWST',
  })

  const [payrollSettings, setPayrollSettings] = useState({
    ahv_rate_employee: 5.3,
    iv_rate_employee: 0.7,
    eo_rate_employee: 0.25,
    alv_rate_employee: 1.1,
    ahv_rate_employer: 5.3,
    iv_rate_employer: 0.7,
    eo_rate_employer: 0.25,
    alv_rate_employer: 1.1,
    fak_rate_employer: 1.5,
    bvg_plan: 'Standard',
  })

  const [notifications, setNotifications] = useState({
    expense_submitted: true,
    expense_approved: true,
    expense_rejected: true,
    year_end_reminder: true,
    bank_sync_complete: false,
    payroll_due: true,
  })

  const handleSaveCompany = async () => {
    setIsSaving(true)
    setTimeout(() => {
      setIsSaving(false)
      toast.success('Firmenangaben gespeichert')
    }, 800)
  }

  const handleSavePayroll = async () => {
    setIsSaving(true)
    setTimeout(() => {
      setIsSaving(false)
      toast.success('Lohneinstellungen gespeichert')
    }, 800)
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Einstellungen</h1>
        <p className="text-sm text-slate-500 mt-0.5">Firmen- und Systemkonfiguration</p>
      </div>

      <Tabs defaultValue="company">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="company" className="flex items-center gap-1.5">
            <Building2 className="w-3.5 h-3.5" /> Firma
          </TabsTrigger>
          <TabsTrigger value="users" className="flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" /> Benutzer
          </TabsTrigger>
          <TabsTrigger value="managers" className="flex items-center gap-1.5">
            <Settings className="w-3.5 h-3.5" /> Verwalter
          </TabsTrigger>
          <TabsTrigger value="payroll" className="flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5" /> Lohnbuchhaltung
          </TabsTrigger>
          <TabsTrigger value="notifications" className="flex items-center gap-1.5">
            <Bell className="w-3.5 h-3.5" /> Benachrichtigungen
          </TabsTrigger>
          <TabsTrigger value="banking" className="flex items-center gap-1.5">
            <CreditCard className="w-3.5 h-3.5" /> Banking
          </TabsTrigger>
        </TabsList>

        {/* Company tab */}
        <TabsContent value="company" className="mt-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-5">
            <h2 className="font-semibold text-slate-900">Firmenangaben</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label>Firmenname</Label>
                <Input
                  value={companyForm.name}
                  onChange={e => setCompanyForm(p => ({ ...p, name: e.target.value }))}
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label>Juristischer Name</Label>
                <Input
                  value={companyForm.legal_name}
                  onChange={e => setCompanyForm(p => ({ ...p, legal_name: e.target.value }))}
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label>UID-Nummer</Label>
                <Input
                  value={companyForm.uid_number}
                  onChange={e => setCompanyForm(p => ({ ...p, uid_number: e.target.value }))}
                  className="mt-1.5"
                  placeholder="CHE-123.456.789"
                />
              </div>
              <div>
                <Label>MWST-Nummer</Label>
                <Input
                  value={companyForm.vat_number ?? ''}
                  onChange={e => setCompanyForm(p => ({ ...p, vat_number: e.target.value }))}
                  className="mt-1.5"
                  placeholder="CHE-123.456.789 MWST"
                />
              </div>
              <div>
                <Label>Strasse</Label>
                <Input
                  value={companyForm.address}
                  onChange={e => setCompanyForm(p => ({ ...p, address: e.target.value }))}
                  className="mt-1.5"
                />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <Label>PLZ</Label>
                  <Input
                    value={companyForm.postal_code}
                    onChange={e => setCompanyForm(p => ({ ...p, postal_code: e.target.value }))}
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label>Ort</Label>
                  <Input
                    value={companyForm.city}
                    onChange={e => setCompanyForm(p => ({ ...p, city: e.target.value }))}
                    className="mt-1.5"
                  />
                </div>
                <div>
                  <Label>Kanton</Label>
                  <select
                    value={companyForm.canton}
                    onChange={e => setCompanyForm(p => ({ ...p, canton: e.target.value }))}
                    className="mt-1.5 w-full h-10 rounded-md border border-slate-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    {CANTONS.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <Label>Telefon</Label>
                <Input
                  value={companyForm.phone}
                  onChange={e => setCompanyForm(p => ({ ...p, phone: e.target.value }))}
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label>E-Mail</Label>
                <Input
                  type="email"
                  value={companyForm.email}
                  onChange={e => setCompanyForm(p => ({ ...p, email: e.target.value }))}
                  className="mt-1.5"
                />
              </div>
              <div className="sm:col-span-2">
                <Label>Bank IBAN</Label>
                <Input
                  value={companyForm.bank_iban}
                  onChange={e => setCompanyForm(p => ({ ...p, bank_iban: e.target.value }))}
                  className="mt-1.5"
                  placeholder="CH93 0076 2011 6238 5295 7"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <Button onClick={handleSaveCompany} disabled={isSaving}>
                <Save className="w-4 h-4 mr-2" />
                {isSaving ? 'Wird gespeichert...' : 'Speichern'}
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* Users tab */}
        <TabsContent value="users" className="mt-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Benutzerverwaltung</h2>
              <Button size="sm">
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                Einladen
              </Button>
            </div>
            <div className="divide-y divide-slate-100">
              {[
                { name: 'Max Muster', email: 'max@immomanager.ch', role: 'admin', label: 'A', active: true },
                { name: 'Anna Müller', email: 'anna@immomanager.ch', role: 'manager', label: 'B', active: true },
              ].map((u) => (
                <div key={u.email} className="flex items-center justify-between px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-red-600 flex items-center justify-center text-white text-sm font-bold">
                      {u.name[0]}
                    </div>
                    <div>
                      <div className="font-medium text-slate-900">{u.name}</div>
                      <div className="text-sm text-slate-500">{u.email}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">Verwalter {u.label}</Badge>
                    <Badge variant={u.role === 'admin' ? 'default' : 'outline'}>
                      {u.role === 'admin' ? 'Admin' : 'Verwalter'}
                    </Badge>
                    {u.active ? (
                      <Badge variant="success">Aktiv</Badge>
                    ) : (
                      <Badge variant="secondary">Inaktiv</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </TabsContent>

        {/* Managers tab */}
        <TabsContent value="managers" className="mt-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-5">
            <h2 className="font-semibold text-slate-900">Verwalterkonfiguration</h2>
            <p className="text-sm text-slate-500">
              Definieren Sie, welche Benutzer als Verwalter A und B fungieren. Dies beeinflusst die Einnahmenverteilung und Kostenzuteilung.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="border border-blue-200 rounded-xl p-4 bg-blue-50">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">A</div>
                  <span className="font-semibold text-blue-900">Verwalter A</span>
                </div>
                <div>
                  <Label>Zugewiesener Benutzer</Label>
                  <select className="mt-1.5 w-full h-10 rounded-md border border-blue-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500">
                    <option>Max Muster</option>
                    <option>Anna Müller</option>
                  </select>
                </div>
              </div>
              <div className="border border-orange-200 rounded-xl p-4 bg-orange-50">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-full bg-orange-500 flex items-center justify-center text-white text-sm font-bold">B</div>
                  <span className="font-semibold text-orange-900">Verwalter B</span>
                </div>
                <div>
                  <Label>Zugewiesener Benutzer</Label>
                  <select className="mt-1.5 w-full h-10 rounded-md border border-orange-200 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500">
                    <option>Anna Müller</option>
                    <option>Max Muster</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="flex justify-end">
              <Button>
                <Save className="w-4 h-4 mr-2" />
                Speichern
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* Payroll settings tab */}
        <TabsContent value="payroll" className="mt-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-5">
            <h2 className="font-semibold text-slate-900">Lohnbuchhaltungseinstellungen</h2>

            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Arbeitnehmerabzüge (%)</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { key: 'ahv_rate_employee', label: 'AHV' },
                  { key: 'iv_rate_employee', label: 'IV' },
                  { key: 'eo_rate_employee', label: 'EO' },
                  { key: 'alv_rate_employee', label: 'ALV' },
                ].map(({ key, label }) => (
                  <div key={key}>
                    <Label>{label} (%)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={(payrollSettings as Record<string, number | string>)[key]}
                      onChange={e => setPayrollSettings(p => ({ ...p, [key]: parseFloat(e.target.value) }))}
                      className="mt-1.5"
                    />
                  </div>
                ))}
              </div>
            </div>

            <Separator />

            <div>
              <h3 className="text-sm font-semibold text-slate-700 mb-3">Arbeitgeberbeiträge (%)</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { key: 'ahv_rate_employer', label: 'AHV' },
                  { key: 'iv_rate_employer', label: 'IV' },
                  { key: 'eo_rate_employer', label: 'EO' },
                  { key: 'alv_rate_employer', label: 'ALV' },
                  { key: 'fak_rate_employer', label: 'FAK' },
                ].map(({ key, label }) => (
                  <div key={key}>
                    <Label>{label} (%)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      value={(payrollSettings as Record<string, number | string>)[key]}
                      onChange={e => setPayrollSettings(p => ({ ...p, [key]: parseFloat(e.target.value) }))}
                      className="mt-1.5"
                    />
                  </div>
                ))}
              </div>
            </div>

            <Separator />

            <div>
              <Label>BVG-Plan</Label>
              <select
                value={payrollSettings.bvg_plan}
                onChange={e => setPayrollSettings(p => ({ ...p, bvg_plan: e.target.value }))}
                className="mt-1.5 w-full max-w-xs h-10 rounded-md border border-slate-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value="Standard">Standard</option>
                <option value="Kader">Kader</option>
                <option value="Minimal">Minimal (BVG-Minimum)</option>
              </select>
            </div>

            <div className="flex justify-end">
              <Button onClick={handleSavePayroll} disabled={isSaving}>
                <Save className="w-4 h-4 mr-2" />
                {isSaving ? 'Wird gespeichert...' : 'Speichern'}
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* Notifications tab */}
        <TabsContent value="notifications" className="mt-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
            <h2 className="font-semibold text-slate-900">Benachrichtigungseinstellungen</h2>
            <div className="space-y-4">
              {[
                { key: 'expense_submitted', label: 'Neue Ausgabe eingereicht', desc: 'Bei neuen Ausgaben zur Genehmigung' },
                { key: 'expense_approved', label: 'Ausgabe genehmigt', desc: 'Wenn Ihre Ausgabe genehmigt wurde' },
                { key: 'expense_rejected', label: 'Ausgabe abgelehnt', desc: 'Wenn Ihre Ausgabe abgelehnt wurde' },
                { key: 'year_end_reminder', label: 'Jahresabschluss-Erinnerung', desc: 'Erinnerung vor dem Jahresabschluss' },
                { key: 'bank_sync_complete', label: 'Banksynchronisierung', desc: 'Nach erfolgreicher Banksynchronisierung' },
                { key: 'payroll_due', label: 'Lohnzahlung fällig', desc: 'Erinnerung bei fälligen Lohnzahlungen' },
              ].map(({ key, label, desc }) => (
                <div key={key} className="flex items-center justify-between py-2">
                  <div>
                    <div className="text-sm font-medium text-slate-900">{label}</div>
                    <div className="text-xs text-slate-500">{desc}</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={(notifications as Record<string, boolean>)[key]}
                      onChange={e => setNotifications(p => ({ ...p, [key]: e.target.checked }))}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-red-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600" />
                  </label>
                </div>
              ))}
            </div>
            <div className="flex justify-end pt-2">
              <Button onClick={() => toast.success('Benachrichtigungen gespeichert')}>
                <Save className="w-4 h-4 mr-2" />
                Speichern
              </Button>
            </div>
          </div>
        </TabsContent>

        {/* Banking tab */}
        <TabsContent value="banking" className="mt-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">Bankverbindungen</h2>
              <Button size="sm">
                <Plus className="w-3.5 h-3.5 mr-1.5" />
                Konto verbinden
              </Button>
            </div>
            <div className="p-5">
              <div className="text-sm text-slate-500 text-center py-8">
                <CreditCard className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                <p>Verbinden Sie Ihr Bankkonto über Open Banking</p>
                <Button variant="outline" size="sm" className="mt-3">
                  Konto verbinden
                </Button>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
