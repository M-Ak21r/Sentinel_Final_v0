import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Security Dashboard',
  description: 'Real-time security system monitoring and management',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-[#f5ecdc] text-gray-900 min-h-screen">{children}</body>
    </html>
  )
}
