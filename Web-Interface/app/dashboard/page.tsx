'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/app/components/Sidebar'

interface DashboardStats {
  totalCameras: number
  onlineFeeds: number
  events24h: number
  criticalAlerts: number
}

export default function DashboardPage() {
  const router = useRouter()
  const [stats, setStats] = useState<DashboardStats>({
    totalCameras: 0,
    onlineFeeds: 0,
    events24h: 0,
    criticalAlerts: 0,
  })
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/auth/login')
      return
    }
    fetchStats()
  }, [router])

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/dashboard/stats', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2 text-[#1f1a17]">Security Dashboard</h1>
            <p className="text-gray-700">Real-time monitoring and event tracking</p>
          </div>

          {isLoading ? (
            <div className="text-center py-12">Loading dashboard...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <StatCard
                title="Total Cameras"
                value={stats.totalCameras}
                icon="📹"
                color="blue"
              />
              <StatCard
                title="Online Feeds"
                value={stats.onlineFeeds}
                icon="🟢"
                color="green"
              />
              <StatCard
                title="Events (24h)"
                value={stats.events24h}
                icon="📊"
                color="purple"
              />
              <StatCard
                title="Critical Alerts"
                value={stats.criticalAlerts}
                icon="🚨"
                color="red"
              />
            </div>
          )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 glass p-6 rounded-lg">
                <h2 className="text-xl font-bold mb-4 text-[#1f1a17]">Recent Activity</h2>
                <div className="space-y-3">
                  {[
                    { time: '2 min ago', event: 'Motion detected at Front Gate' },
                    { time: '5 min ago', event: 'Camera 3 went offline' },
                    { time: '12 min ago', event: 'Unauthorized access attempt blocked' },
                    { time: '25 min ago', event: 'All systems operational' },
                  ].map((item, idx) => (
                    <div key={idx} className="flex items-center justify-between py-2 border-b border-gray-300 last:border-0">
                      <span className="text-gray-800">{item.event}</span>
                      <span className="text-gray-600 text-sm">{item.time}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass p-6 rounded-lg">
                <h2 className="text-xl font-bold mb-4 text-[#1f1a17]">System Status</h2>
                <div className="space-y-4">
                  <StatusItem label="Primary Server" status="online" />
                  <StatusItem label="Database" status="online" />
                  <StatusItem label="Backup Storage" status="online" />
                  <StatusItem label="Network" status="online" />
                </div>
              </div>
            </div>
        </div>
      </main>
    </div>
  )
}

function StatCard({
  title,
  value,
  icon,
  color,
}: {
  title: string
  value: number
  icon: string
  color: string
}) {
  const colorClasses = {
    blue: 'bg-blue-100 border-blue-200 text-blue-800',
    green: 'bg-emerald-100 border-emerald-200 text-emerald-800',
    purple: 'bg-purple-100 border-purple-200 text-purple-800',
    red: 'bg-red-100 border-red-200 text-red-800',
  }

  return (
    <div className={`glass p-6 rounded-lg border ${colorClasses[color as keyof typeof colorClasses]}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-700 text-sm">{title}</p>
          <p className="text-3xl font-bold mt-2 text-[#1f1a17]">{value}</p>
        </div>
        <span className="text-4xl">{icon}</span>
      </div>
    </div>
  )
}

function StatusItem({ label, status }: { label: string; status: 'online' | 'offline' }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-gray-800">{label}</span>
      <span className={`flex items-center space-x-2 text-sm ${status === 'online' ? 'text-emerald-700' : 'text-red-700'}`}>
        <span className={`w-2 h-2 rounded-full ${status === 'online' ? 'bg-emerald-600' : 'bg-red-600'}`}></span>
        <span>{status}</span>
      </span>
    </div>
  )
}
