'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Building2,
  Receipt,
  CreditCard,
  Users,
  BookOpen,
  BarChart3,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuth } from '@/lib/auth'
import { toast } from 'sonner'
import { useRouter } from 'next/navigation'
import { useState } from 'react'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/properties', label: 'Liegenschaften', icon: Building2 },
  { href: '/dashboard/expenses', label: 'Ausgaben', icon: Receipt },
  { href: '/dashboard/banking', label: 'Banking', icon: CreditCard },
  { href: '/dashboard/payroll', label: 'Lohnbuchhaltung', icon: Users },
  { href: '/dashboard/accounting', label: 'Buchhaltung', icon: BookOpen },
  { href: '/dashboard/reports', label: 'Berichte', icon: BarChart3 },
  { href: '/dashboard/settings', label: 'Einstellungen', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const router = useRouter()
  const [collapsed, setCollapsed] = useState(false)

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
    <aside
      className={cn(
        'flex flex-col bg-slate-900 text-white transition-all duration-300 flex-shrink-0',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Brand */}
      <div className={cn('flex items-center h-16 border-b border-slate-700/50 px-4', collapsed ? 'justify-center' : 'gap-3')}>
        <div className="w-8 h-8 bg-red-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <Building2 className="w-4.5 h-4.5 text-white w-5 h-5" />
        </div>
        {!collapsed && (
          <div>
            <div className="font-bold text-white text-sm leading-tight">ImmoManager</div>
            <div className="text-slate-400 text-xs leading-tight">Liegenschaftsverwaltung</div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href))
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all duration-150',
                collapsed ? 'justify-center' : '',
                isActive
                  ? 'bg-red-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      {/* User section */}
      <div className="border-t border-slate-700/50 p-3">
        {!collapsed ? (
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-white truncate">
                {user?.full_name ?? user?.email ?? 'Benutzer'}
              </div>
              <div className="text-xs text-slate-400 truncate">{user?.email}</div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center mb-2">
            <div className="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center text-white text-xs font-bold">
              {initials}
            </div>
          </div>
        )}
        <div className={cn('flex gap-1', collapsed ? 'flex-col items-center' : '')}>
          <button
            onClick={handleLogout}
            className={cn(
              'flex items-center gap-2 px-2 py-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-800 text-xs transition-colors',
              collapsed ? 'justify-center w-full' : 'flex-1'
            )}
            title="Abmelden"
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            {!collapsed && 'Abmelden'}
          </button>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="flex items-center justify-center p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title={collapsed ? 'Erweitern' : 'Einklappen'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </aside>
  )
}
