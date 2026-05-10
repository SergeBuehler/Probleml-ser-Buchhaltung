import { ReconciliationSuggestion } from '@/lib/types'
import { formatCHF, formatDate } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Check, X, TrendingUp } from 'lucide-react'

interface ReconciliationCardProps {
  suggestion: ReconciliationSuggestion
  onAccept: (id: number) => void
  onReject: (id: number) => void
  isLoading?: boolean
}

export function ReconciliationCard({ suggestion, onAccept, onReject, isLoading }: ReconciliationCardProps) {
  const confidence = suggestion.confidence_score * 100
  const confidenceColor = confidence >= 80 ? 'bg-green-500' : confidence >= 60 ? 'bg-amber-500' : 'bg-red-400'

  return (
    <div className="border border-slate-200 rounded-xl p-4 bg-white shadow-sm space-y-3">
      {/* Confidence score */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <TrendingUp className="w-4 h-4" />
          Übereinstimmung
        </div>
        <div className="flex items-center gap-2">
          <div className="w-24 h-2 bg-slate-200 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${confidenceColor}`}
              style={{ width: `${confidence}%` }}
            />
          </div>
          <span className="text-sm font-semibold text-slate-900">{confidence.toFixed(0)}%</span>
        </div>
      </div>

      {/* Transaction */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-blue-50 rounded-lg p-3">
          <div className="text-xs text-blue-600 font-medium mb-1">Banktransaktion</div>
          <div className="text-sm font-semibold text-slate-900 truncate">{suggestion.transaction.description}</div>
          <div className="text-xs text-slate-500">{formatDate(suggestion.transaction.transaction_date)}</div>
          <div className={`text-sm font-bold mt-1 ${suggestion.transaction.amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
            {formatCHF(suggestion.transaction.amount)}
          </div>
        </div>
        <div className="bg-orange-50 rounded-lg p-3">
          <div className="text-xs text-orange-600 font-medium mb-1">Ausgabe</div>
          <div className="text-sm font-semibold text-slate-900 truncate">{suggestion.suggested_expense.title}</div>
          <div className="text-xs text-slate-500">{suggestion.suggested_expense.vendor}</div>
          <div className="text-sm font-bold text-slate-900 mt-1">
            {formatCHF(suggestion.suggested_expense.total_amount)}
          </div>
        </div>
      </div>

      {/* Match reasons */}
      {suggestion.match_reasons.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {suggestion.match_reasons.map((reason, i) => (
            <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
              {reason}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <Button
          variant="success"
          size="sm"
          className="flex-1"
          onClick={() => onAccept(suggestion.id)}
          disabled={isLoading}
        >
          <Check className="w-3.5 h-3.5 mr-1" />
          Annehmen
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="flex-1"
          onClick={() => onReject(suggestion.id)}
          disabled={isLoading}
        >
          <X className="w-3.5 h-3.5 mr-1" />
          Ablehnen
        </Button>
      </div>
    </div>
  )
}
