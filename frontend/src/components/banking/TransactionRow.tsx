import { BankTransaction } from '@/lib/types'
import { formatCHF, formatDate } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface TransactionRowProps {
  transaction: BankTransaction
  compact?: boolean
}

const STATUS_LABELS: Record<string, string> = {
  reconciled: 'Abgestimmt',
  pending: 'Ausstehend',
  ignored: 'Ignoriert',
}

export function TransactionRow({ transaction, compact }: TransactionRowProps) {
  const isDebit = transaction.amount < 0

  return (
    <div className={cn('flex items-center gap-4 py-3 hover:bg-slate-50 rounded-lg px-2 transition-colors', compact ? 'py-2' : '')}>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="text-sm font-medium text-slate-900 truncate">{transaction.description}</div>
            {transaction.counterparty_name && (
              <div className="text-xs text-slate-500 truncate">{transaction.counterparty_name}</div>
            )}
          </div>
          <div className={cn('text-sm font-semibold whitespace-nowrap', isDebit ? 'text-red-600' : 'text-green-600')}>
            {isDebit ? '-' : '+'}{formatCHF(Math.abs(transaction.amount))}
          </div>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-xs text-slate-400">{formatDate(transaction.transaction_date)}</span>
          <Badge
            variant={
              transaction.reconciliation_status === 'reconciled' ? 'success' :
              transaction.reconciliation_status === 'ignored' ? 'outline' : 'warning'
            }
          >
            {STATUS_LABELS[transaction.reconciliation_status]}
          </Badge>
          {transaction.matched_expense && (
            <span className="text-xs text-blue-600 truncate">
              → {transaction.matched_expense.title}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
