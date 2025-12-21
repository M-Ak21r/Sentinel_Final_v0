'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(true)
  const [user, setUser] = useState<{ name?: string } | null>(null)

  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (userData) {
      setUser(JSON.parse(userData))
    }
  }, [])

  return (
    <aside
      className={`${
        isOpen ? 'w-64' : 'w-20'
      } bg-gradient-to-b from-[#f9f1df] via-[#f3e6cc] to-[#e4d5b5] border-r border-[#d6c7aa] fixed h-screen transition-all duration-300 flex flex-col shadow-lg`}
    >
      <div className="p-4 border-b border-[#d6c7aa] flex items-center justify-between">
        {isOpen ? (
          <div className="flex items-center space-x-3">
            <div className="relative h-8 w-28">
              <Image
                src="/sentinel-logo.svg"
                alt="Sentinel"
                fill
                sizes="112px"
                className="object-contain"
              />
            </div>
          </div>
        ) : (
          <div className="h-8 w-8 rounded-full bg-sentinel/20 border border-sentinel/40 flex items-center justify-center text-sentinel font-bold">S</div>
        )}
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-1 hover:bg-[#e6d8bd] rounded transition border border-[#d6c7aa]"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      <nav className="flex-1 p-4 space-y-2">
        <NavItem href="/dashboard" icon="📊" label="Dashboard" isOpen={isOpen} />
        <NavItem href="/dashboard/feeds" icon="📹" label="Live Feeds" isOpen={isOpen} />
        <NavItem href="/dashboard/evidence" icon="📸" label="Evidence" isOpen={isOpen} />
        <NavItem href="/dashboard/database" icon="🗄️" label="Database" isOpen={isOpen} />
        <NavItem href="/dashboard/faces" icon="👤" label="Authorized Faces" isOpen={isOpen} />
        <NavItem href="/dashboard/settings" icon="⚙️" label="Settings" isOpen={isOpen} />
      </nav>

      <div className="p-4 border-t border-[#d6c7aa]">
        {isOpen && <p className="text-sm text-gray-700 mb-2">{user?.name || 'User'}</p>}
        <button
          onClick={() => {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            window.location.href = '/auth/login'
          }}
          className="w-full px-4 py-2 bg-sentinel hover:bg-sentinel/90 rounded transition text-sm text-white shadow-sm"
        >
          {isOpen ? 'Logout' : '🚪'}
        </button>
      </div>
    </aside>
  )
}

function NavItem({
  href,
  icon,
  label,
  isOpen,
}: {
  href: string
  icon: string
  label: string
  isOpen: boolean
}) {
  return (
    <Link
      href={href}
      className="flex items-center space-x-3 px-4 py-2 rounded-lg hover:bg-sentinel/10 border border-transparent hover:border-sentinel/40 transition group text-[#2f2a25]"
    >
      <span className="text-xl">{icon}</span>
      {isOpen && <span className="group-hover:translate-x-1 transition text-[#2f2a25] font-medium">{label}</span>}
    </Link>
  )
}
