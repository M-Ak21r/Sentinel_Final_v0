'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/app/components/Sidebar'
import LiveFeedComponent from '@/app/components/LiveFeed'

export default function FeedsPage() {
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/auth/login')
    }
  }, [router])

  return (
    <div className="flex">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Live Feeds</h1>
            <p className="text-gray-700">Real-time camera feeds and monitoring</p>
          </div>

          <LiveFeedComponent />
        </div>
      </main>
    </div>
  )
}
