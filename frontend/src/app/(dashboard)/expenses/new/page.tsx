'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { ExpenseUpload } from '@/components/expenses/ExpenseUpload'
import { ExpenseForm } from '@/components/forms/ExpenseForm'
import { OCRData } from '@/lib/types'

export default function NewExpensePage() {
  const router = useRouter()
  const [uploadedFileUrl, setUploadedFileUrl] = useState<string>()
  const [ocrData, setOCRData] = useState<OCRData | null>(null)

  const handleOCRComplete = (data: OCRData) => {
    setOCRData(data)
  }

  const handleSuccess = () => {
    router.push('/dashboard/expenses')
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/expenses">
            <ArrowLeft className="w-4 h-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-xl font-bold text-slate-900">Neue Ausgabe</h1>
          <p className="text-sm text-slate-500">Ausgabe erfassen und Beleg hochladen</p>
        </div>
      </div>

      {/* Upload section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h2 className="font-semibold text-slate-900 mb-4">Beleg hochladen</h2>
        <ExpenseUpload
          onFileUploaded={(url) => setUploadedFileUrl(url)}
          onOCRComplete={handleOCRComplete}
        />
      </div>

      {/* Form section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h2 className="font-semibold text-slate-900 mb-4">Ausgabedetails</h2>
        <ExpenseForm
          onSuccess={handleSuccess}
          uploadedFileUrl={uploadedFileUrl}
          defaultValues={ocrData ? {
            vendor: ocrData.vendor,
            amount: ocrData.amount,
            expense_date: ocrData.date,
          } : undefined}
        />
      </div>
    </div>
  )
}
