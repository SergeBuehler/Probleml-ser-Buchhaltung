'use client'

import { useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import Link from 'next/link'
import { PropertyForm } from '@/components/forms/PropertyForm'
import { Property } from '@/lib/types'
import { Button } from '@/components/ui/button'

export default function NewPropertyPage() {
  const router = useRouter()

  const handleSuccess = (property: Property) => {
    router.push(`/dashboard/properties/${property.id}`)
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/dashboard/properties">
            <ArrowLeft className="w-4 h-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-xl font-bold text-slate-900">Neue Liegenschaft</h1>
          <p className="text-sm text-slate-500">Neue Liegenschaft zur Verwaltung hinzufügen</p>
        </div>
      </div>

      {/* Form card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <PropertyForm onSuccess={handleSuccess} />
      </div>
    </div>
  )
}
