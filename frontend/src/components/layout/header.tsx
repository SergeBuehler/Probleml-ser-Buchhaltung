'use client'

import { usePathname } from 'next/navigation'
import { Bell, ChevronRight, User, Settings, LogOut } from 'lucide-react'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/lib/auth'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import Link from 'next/link'

const routeLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  properties: 'Liegenschaften',
  expenses: 'Ausgaben',
  banking: 'Banking',
  payroll: 'Lohnbuchhaltung',
  accounting: 'Buchhaltung',
  reports: 'Berichte',
  settings: 'Einstellungen',
  new: 'Neu',
}

function getBreadcrumbs(pathname: string) {
  const parts = pathname.split('/').filter(Boolean)
  const breadcrumbs: { label: string; href: string }[] = []
  let currentPath = ''

  for (const part of parts) {
    currentPath += `/${part}`
    const label = routeLabels[part] ?? part
    breadcrumbs.push({ label, href: currentPath })
  }

  return breadcrumbs
}

export function Header() {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const router = useRouter()
  const breadcrumbs = getBreadcrumbs(pathname)

  const handleLogout = async () => {
    try {
      await logout()
      router.push('/login')
      toast.success('Erfolgreich abgemeldet')
    } catch {
      router.push('/login')
    }
  }

  const initials = user
    ? `${user.first_name?.[0] ?? ''}${user.last_name?.[0] ?? ''}`.toUpperCase()
    : '??'

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm">
        {breadcrumbs.map((crumb, idx) => (
          <span key={crumb.href} className="flex items-center gap-1.5">
            {idx > 0 && <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
            {idx === breadcrumbs.length - 1 ? (
              <span className="font-semibold text-slate-900">{crumb.label}</span>
            ) : (
              <Link href={crumb.href} className="text-slate-500 hover:text-slate-700 transition-colors">
                {crumb.label}
              </Link>
            )}
          </span>
        ))}
      </nav>

      {/* Right side actions */}
      <div className="flex items-center gap-3">
        {/* Notifications */}
        <button className="relative w-9 h-9 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-600 rounded-full" />
        </button>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2.5 pl-2 pr-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors">
              <div className="w-7 h-7 rounded-full bg-red-600 flex items-center justify-center text-white text-xs font-bold">
                {initials}
              </div>
              <div className="text-left hidden sm:block">
                <div className="text-xs font-semibold text-slate-900 leading-tight">
                  {user?.full_name ?? 'Benutzer'}
                </div>
                <div className="text-xs text-slate-500 leading-tight">
                  {user?.role === 'admin' ? 'Administrator' : user?.role === 'manager' ? 'Verwalter' : 'Betrachter'}
                </div>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuLabel>
              <div className="font-semibold text-slate-900">{user?.full_name}</div>
              <div className="text-xs text-slate-500 font-normal">{user?.email}</div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings" className="flex items-center gap-2 cursor-pointer">
                <User className="w-4 h-4" />
                Mein Profil
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/dashboard/settings" className="flex items-center gap-2 cursor-pointer">
                <Settings className="w-4 h-4" />
                Einstellungen
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={handleLogout}
              className="flex items-center gap-2 text-red-600 cursor-pointer focus:text-red-600 focus:bg-red-50"
            >
              <LogOut className="w-4 h-4" />
              Abmelden
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
