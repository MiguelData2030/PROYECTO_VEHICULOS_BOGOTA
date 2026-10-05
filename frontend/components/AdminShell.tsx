'use client';

import { useEffect, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { BarChart3, Car, Target, Users, LogOut, Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth';

const tabs = [
  { href: '/admin', label: 'Dashboard', icon: BarChart3 },
  { href: '/admin/inventario', label: 'Inventario', icon: Car },
  { href: '/admin/oportunidades', label: 'Oportunidades', icon: Target },
  { href: '/admin/leads', label: 'Leads', icon: Users },
];

/**
 * Wraps every /admin page: redirects to /login when there is no session and
 * renders the admin sub-navigation.
 */
export default function AdminShell({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.push('/login');
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="pt-16 flex items-center justify-center min-h-[80vh]">
        <Loader2 className="w-10 h-10 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="pt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <nav className="flex gap-1 mb-6 overflow-x-auto border-b border-border">
          {tabs.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 -mb-px transition-colors ${
                  active
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-400 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-display font-bold text-white">{title}</h1>
            {subtitle && <p className="text-gray-400 text-sm">{subtitle}</p>}
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <span className="text-gray-500 text-sm hidden sm:block">Hola, {user.username}</span>
            {actions}
            <button
              onClick={() => { logout(); router.push('/'); }}
              className="btn-ghost p-2 text-gray-500 hover:text-red-400"
              title="Cerrar sesión"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>

        {children}
      </div>
    </div>
  );
}
