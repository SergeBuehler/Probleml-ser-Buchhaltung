'use client'

import { useState, useEffect } from 'react'
import {
  CreditCard, RefreshCw, Plus, Search, Filter,
  CheckCircle2, Clock, AlertCircle
} from 'lucide-react'
import { bankingApi } from '@/lib/api'
import { BankAccount, BankTransaction, ReconciliationSuggestion } from '@/lib/types'
import { formatCHF, formatDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { TransactionRow } from '@/components/banking/TransactionRow'
import { ReconciliationCard } from '@/components/banking/ReconciliationCard'
import { toast } from 'sonner'

export default function BankingPage() {
  const [accounts, setAccounts] = useState<BankAccount[]>([])
  const [transactions, setTransactions] = useState<BankTransaction[]>([])
  const [suggestions, setSuggestions] = useState<ReconciliationSuggestion[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [search, setSearch] = useState('')
  const [reconciliationFilter, setReconciliationFilter] = useState('all')
  const [selectedAccount, setSelectedAccount] = useState<number | undefined>()
  const [total, setTotal] = useState(0)

  useEffect(() => {
    loadAll()
  }, [])

  useEffect(() => {
    loadTransactions()
  }, [reconciliationFilter, selectedAccount])

  const loadAll = async () => {
    setIsLoading(true)
    try {
      const [accs, txns, suggs] = await Promise.all([
        bankingApi.getBankAccounts(),
        bankingApi.getTransactions({ page_size: 50 }),
        bankingApi.getReconciliationSuggestions(),
      ])
      setAccounts(accs)
      setTransactions(txns.data)
      setTotal(txns.total)
      setSuggestions(suggs.filter(s => s.status === 'pending'))
    } catch {
      toast.error('Fehler beim Laden der Bankdaten')
    } finally {
      setIsLoading(false)
    }
  }

  const loadTransactions = async () => {
    try {
      const response = await bankingApi.getTransactions({
        account_id: selectedAccount,
        reconciliation_status: reconciliationFilter !== 'all' ? reconciliationFilter : undefined,
        page_size: 50,
      })
      setTransactions(response.data)
      setTotal(response.total)
    } catch {
      toast.error('Fehler beim Laden der Transaktionen')
    }
  }

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      const result = await bankingApi.syncBank(selectedAccount)
      toast.success(`${result.synced_count} Transaktionen synchronisiert`)
      loadAll()
    } catch {
      toast.error('Synchronisierung fehlgeschlagen')
    } finally {
      setIsSyncing(false)
    }
  }

  const handleAcceptSuggestion = async (id: number) => {
    try {
      await bankingApi.acceptSuggestion(id)
      setSuggestions(prev => prev.filter(s => s.id !== id))
      toast.success('Übereinstimmung bestätigt')
    } catch {
      toast.error('Fehler beim Bestätigen')
    }
  }

  const handleRejectSuggestion = async (id: number) => {
    try {
      await bankingApi.rejectSuggestion(id)
      setSuggestions(prev => prev.filter(s => s.id !== id))
      toast.success('Vorschlag abgelehnt')
    } catch {
      toast.error('Fehler beim Ablehnen')
    }
  }

  const filteredTransactions = transactions.filter(t =>
    !search ||
    t.description.toLowerCase().includes(search.toLowerCase()) ||
    (t.counterparty_name ?? '').toLowerCase().includes(search.toLowerCase())
  )

  const totalBalance = accounts.reduce((sum, a) => sum + a.balance, 0)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Banking</h1>
          <p className="text-sm text-slate-500 mt-0.5">{accounts.length} verbundene Konten</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleSync} disabled={isSyncing}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
            Synchronisieren
          </Button>
          <Button>
            <Plus className="w-4 h-4 mr-2" />
            Konto verbinden
          </Button>
        </div>
      </div>

      {/* Account cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {accounts.map((account) => (
            <button
              key={account.id}
              onClick={() => setSelectedAccount(selectedAccount === account.id ? undefined : account.id)}
              className={`text-left bg-white rounded-xl border p-4 shadow-sm hover:shadow-md transition-all ${
                selectedAccount === account.id ? 'border-red-400 ring-2 ring-red-100' : 'border-slate-200'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-blue-600" />
                  <div>
                    <div className="text-sm font-semibold text-slate-900">{account.account_name}</div>
                    <div className="text-xs text-slate-500">{account.bank_name}</div>
                  </div>
                </div>
                <Badge
                  variant={
                    account.connection_status === 'connected' ? 'success' :
                    account.connection_status === 'error' ? 'destructive' : 'warning'
                  }
                >
                  {account.connection_status === 'connected' ? 'Verbunden' :
                   account.connection_status === 'error' ? 'Fehler' : 'Trennung'}
                </Badge>
              </div>
              <div className="text-xl font-bold text-slate-900">{formatCHF(account.balance)}</div>
              <div className="text-xs text-slate-400 mt-1">{account.iban}</div>
              {account.last_sync_at && (
                <div className="text-xs text-slate-400">Sync: {formatDate(account.last_sync_at)}</div>
              )}
            </button>
          ))}

          {/* Total balance */}
          {accounts.length > 1 && (
            <div className="bg-slate-900 rounded-xl p-4 shadow-sm text-white">
              <div className="text-xs text-slate-400 mb-1">Gesamtguthaben</div>
              <div className="text-xl font-bold">{formatCHF(totalBalance)}</div>
              <div className="text-xs text-slate-400 mt-1">{accounts.length} Konten</div>
            </div>
          )}
        </div>
      )}

      {/* Main content tabs */}
      <Tabs defaultValue="transactions">
        <TabsList>
          <TabsTrigger value="transactions">
            Transaktionen
            <span className="ml-2 text-xs bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-full">
              {total}
            </span>
          </TabsTrigger>
          <TabsTrigger value="reconciliation">
            Bankabstimmung
            {suggestions.length > 0 && (
              <span className="ml-2 text-xs bg-red-600 text-white px-1.5 py-0.5 rounded-full">
                {suggestions.length}
              </span>
            )}
          </TabsTrigger>
        </TabsList>

        {/* Transactions tab */}
        <TabsContent value="transactions" className="mt-4">
          <div className="flex flex-wrap gap-3 mb-4">
            <div className="relative flex-1 min-w-[200px] max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Suchen..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              value={reconciliationFilter}
              onChange={(e) => setReconciliationFilter(e.target.value)}
              className="text-sm border border-slate-300 rounded-md px-3 py-2 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="all">Alle Status</option>
              <option value="pending">Ausstehend</option>
              <option value="reconciled">Abgestimmt</option>
              <option value="ignored">Ignoriert</option>
            </select>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm">
            {filteredTransactions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                <CreditCard className="w-8 h-8 mb-2 opacity-40" />
                <p className="text-sm">Keine Transaktionen gefunden</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 px-2">
                {filteredTransactions.map((transaction) => (
                  <TransactionRow key={transaction.id} transaction={transaction} />
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        {/* Reconciliation tab */}
        <TabsContent value="reconciliation" className="mt-4">
          <div className="mb-4">
            <div className="flex items-center gap-2 text-sm text-slate-600">
              {suggestions.length === 0 ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  Alle Transaktionen wurden abgestimmt
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 text-amber-500" />
                  {suggestions.length} Vorschläge zur Prüfung
                </>
              )}
            </div>
          </div>

          {suggestions.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
              <CheckCircle2 className="w-12 h-12 mx-auto mb-3 text-green-500 opacity-60" />
              <h3 className="font-semibold text-slate-900 mb-1">Alles abgestimmt</h3>
              <p className="text-sm text-slate-500">Keine offenen Bankabstimmungsvorschläge</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {suggestions.map((suggestion) => (
                <ReconciliationCard
                  key={suggestion.id}
                  suggestion={suggestion}
                  onAccept={handleAcceptSuggestion}
                  onReject={handleRejectSuggestion}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
