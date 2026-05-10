'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Image, X, Scan, CheckCircle2, AlertCircle } from 'lucide-react'
import { expensesApi } from '@/lib/api'
import { OCRData } from '@/lib/types'
import { Button } from '@/components/ui/button'
import { formatCHF } from '@/lib/utils'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface UploadedFile {
  file: File
  preview?: string
  fileUrl?: string
  filename?: string
}

interface ExpenseUploadProps {
  onFileUploaded?: (fileUrl: string, filename: string) => void
  onOCRComplete?: (data: OCRData) => void
  expenseId?: number
}

export function ExpenseUpload({ onFileUploaded, onOCRComplete, expenseId }: ExpenseUploadProps) {
  const [uploadedFile, setUploadedFile] = useState<UploadedFile | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isOCRLoading, setIsOCRLoading] = useState(false)
  const [ocrData, setOcrData] = useState<OCRData | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    const preview = file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
    setUploadedFile({ file, preview })
    setOcrData(null)

    setIsUploading(true)
    try {
      const result = await expensesApi.uploadReceipt(file)
      setUploadedFile(prev => prev ? { ...prev, fileUrl: result.file_url, filename: result.filename } : null)
      onFileUploaded?.(result.file_url, result.filename)
      toast.success('Datei erfolgreich hochgeladen')
    } catch {
      toast.error('Fehler beim Hochladen der Datei')
    } finally {
      setIsUploading(false)
    }
  }, [onFileUploaded])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.jpg', '.jpeg', '.png', '.heic', '.webp'],
      'application/pdf': ['.pdf'],
    },
    maxFiles: 1,
    maxSize: 20 * 1024 * 1024, // 20MB
  })

  const handleOCR = async () => {
    if (!expenseId) return
    setIsOCRLoading(true)
    try {
      const result = await expensesApi.triggerOCR(expenseId)
      if (result.ocr_data) {
        setOcrData(result.ocr_data)
        onOCRComplete?.(result.ocr_data)
        toast.success('OCR-Auswertung abgeschlossen')
      }
    } catch {
      toast.error('Fehler bei der OCR-Auswertung')
    } finally {
      setIsOCRLoading(false)
    }
  }

  const clearFile = () => {
    if (uploadedFile?.preview) URL.revokeObjectURL(uploadedFile.preview)
    setUploadedFile(null)
    setOcrData(null)
  }

  return (
    <div className="space-y-4">
      {!uploadedFile ? (
        <div
          {...getRootProps()}
          className={cn(
            'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all',
            isDragActive
              ? 'border-red-400 bg-red-50'
              : 'border-slate-300 hover:border-slate-400 hover:bg-slate-50'
          )}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center">
              <Upload className="w-6 h-6 text-slate-500" />
            </div>
            <div>
              <p className="font-medium text-slate-900">
                {isDragActive ? 'Datei hier ablegen' : 'Beleg hochladen'}
              </p>
              <p className="text-sm text-slate-500 mt-1">
                PDF, JPG, PNG, HEIC (max. 20 MB)
              </p>
            </div>
            <Button type="button" variant="outline" size="sm">
              Datei auswählen
            </Button>
          </div>
        </div>
      ) : (
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          {/* File preview header */}
          <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-200">
            <div className="flex items-center gap-3">
              {uploadedFile.file.type === 'application/pdf' ? (
                <FileText className="w-5 h-5 text-red-600" />
              ) : (
                <Image className="w-5 h-5 text-blue-600" />
              )}
              <div>
                <div className="text-sm font-medium text-slate-900">{uploadedFile.file.name}</div>
                <div className="text-xs text-slate-500">
                  {(uploadedFile.file.size / 1024).toFixed(0)} KB
                  {isUploading && <span className="ml-2 text-blue-600">Wird hochgeladen...</span>}
                  {uploadedFile.fileUrl && !isUploading && (
                    <span className="ml-2 text-green-600 flex items-center gap-1 inline-flex">
                      <CheckCircle2 className="w-3 h-3" /> Hochgeladen
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={clearFile}
              className="p-1 text-slate-400 hover:text-red-600 rounded transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Image preview */}
          {uploadedFile.preview && (
            <div className="p-4 flex justify-center bg-slate-100">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={uploadedFile.preview}
                alt="Beleg"
                className="max-h-48 object-contain rounded"
              />
            </div>
          )}

          {/* OCR section */}
          {uploadedFile.fileUrl && expenseId && (
            <div className="p-4 border-t border-slate-100">
              {!ocrData ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleOCR}
                  disabled={isOCRLoading}
                  className="w-full"
                >
                  <Scan className="w-4 h-4 mr-2" />
                  {isOCRLoading ? 'OCR wird ausgeführt...' : 'Beleg automatisch erkennen (OCR)'}
                </Button>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium text-green-700">
                    <CheckCircle2 className="w-4 h-4" />
                    OCR-Ergebnis
                    <span className="ml-auto text-xs text-slate-500">
                      Genauigkeit: {(ocrData.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {ocrData.vendor && (
                      <div className="bg-green-50 rounded p-2">
                        <div className="text-slate-500">Lieferant</div>
                        <div className="font-medium text-slate-900">{ocrData.vendor}</div>
                      </div>
                    )}
                    {ocrData.amount && (
                      <div className="bg-green-50 rounded p-2">
                        <div className="text-slate-500">Betrag</div>
                        <div className="font-medium text-slate-900">{formatCHF(ocrData.amount)}</div>
                      </div>
                    )}
                    {ocrData.date && (
                      <div className="bg-green-50 rounded p-2">
                        <div className="text-slate-500">Datum</div>
                        <div className="font-medium text-slate-900">{ocrData.date}</div>
                      </div>
                    )}
                    {ocrData.vat_amount && (
                      <div className="bg-green-50 rounded p-2">
                        <div className="text-slate-500">MwSt.</div>
                        <div className="font-medium text-slate-900">{formatCHF(ocrData.vat_amount)}</div>
                      </div>
                    )}
                  </div>
                  {ocrData.confidence < 0.7 && (
                    <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 rounded p-2">
                      <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                      Niedrige Erkennungsgenauigkeit – bitte manuell überprüfen
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
