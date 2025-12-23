'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/app/components/Sidebar'
import CameraStatusCards from '@/app/components/CameraStatusCards'

interface AlertEvent {
  time: string
  event: string
  severity: 'info' | 'warning' | 'critical'
}

export default function DashboardPage() {
  const router = useRouter()
  const [isUnlocking, setIsUnlocking] = useState(false)
  const [isSilencing, setIsSilencing] = useState(false)
  const [commandStatus, setCommandStatus] = useState<string>('')

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/auth/login')
      return
    }
  }, [router])

  const handleCommand = async (action: 'UNLOCK' | 'SILENCE') => {
    const isUnlock = action === 'UNLOCK'
    const setLoading = isUnlock ? setIsUnlocking : setIsSilencing
    
    setLoading(true)
    setCommandStatus('')

    try {
      const response = await fetch('/api/system/control', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          target: isUnlock ? 'door' : 'all',
          action: action,
        }),
      })

      const data = await response.json()

      if (response.ok) {
        setCommandStatus(`✓ ${data.message}`)
        setTimeout(() => setCommandStatus(''), 3000)
      } else {
        setCommandStatus(`✗ ${data.error || 'Command failed'}`)
        setTimeout(() => setCommandStatus(''), 3000)
      }
    } catch (error) {
      console.error('Error sending command:', error)
      setCommandStatus('✗ Connection error')
      setTimeout(() => setCommandStatus(''), 3000)
    } finally {
      setLoading(false)
    }
  }

  // Placeholder alert events
  const recentAlerts: AlertEvent[] = [
    { time: '12:45 PM', event: 'Motion detected at entrance', severity: 'warning' },
    { time: '12:32 PM', event: 'Door unlocked successfully', severity: 'info' },
    { time: '12:18 PM', event: 'Unauthorized access attempt', severity: 'critical' },
    { time: '12:01 PM', event: 'System armed', severity: 'info' },
    { time: '11:50 AM', event: 'Interior camera online', severity: 'info' },
  ]

  return (
    <div className="flex min-h-screen bg-slate-900">
      <Sidebar />
      <main className="ml-64 flex-1 pb-24">
        {/* Header */}
        <div className="bg-slate-950 border-b border-slate-800 px-8 py-6">
          <h1 className="text-3xl font-bold text-cyan-400 uppercase tracking-wide">
            Security Command Center
          </h1>
          <p className="text-slate-400 mt-1">Real-time surveillance and control</p>
        </div>

        <div className="p-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Camera Status Cards - Low Bandwidth Metadata */}
            <div className="lg:col-span-2 space-y-6">
              <CameraStatusCards showViewStreamsButton={true} />

              {/* Command Status */}
              {commandStatus && (
                <div className={`p-4 rounded-lg text-center font-semibold ${
                  commandStatus.startsWith('✓')
                    ? 'bg-emerald-900 text-emerald-300 border border-emerald-700'
                    : 'bg-red-900 text-red-300 border border-red-700'
                }`}>
                  {commandStatus}
                </div>
              )}
            </div>

            {/* Live Alerts Sidebar */}
            <div className="lg:col-span-1">
              <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
                <div className="bg-slate-900 px-4 py-3 border-b border-slate-700">
                  <h2 className="text-cyan-400 font-semibold uppercase tracking-wide">
                    Live Alerts
                  </h2>
                </div>
                <div className="p-4 space-y-3 max-h-[600px] overflow-y-auto">
                  {recentAlerts.map((alert, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border ${
                        alert.severity === 'critical'
                          ? 'bg-red-900 bg-opacity-20 border-red-700'
                          : alert.severity === 'warning'
                          ? 'bg-yellow-900 bg-opacity-20 border-yellow-700'
                          : 'bg-slate-700 border-slate-600'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="text-slate-200 text-sm font-medium">
                            {alert.event}
                          </p>
                          <p className="text-slate-400 text-xs mt-1">
                            {alert.time}
                          </p>
                        </div>
                        <span
                          className={`w-2 h-2 rounded-full mt-1 ${
                            alert.severity === 'critical'
                              ? 'bg-red-500'
                              : alert.severity === 'warning'
                              ? 'bg-yellow-500'
                              : 'bg-emerald-500'
                          }`}
                        ></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Fixed Control Panel at Bottom */}
        <div className="fixed bottom-0 left-64 right-0 bg-slate-950 border-t border-slate-800 px-8 py-4">
          <div className="flex items-center justify-center space-x-4">
            <button
              onClick={() => handleCommand('UNLOCK')}
              disabled={isUnlocking}
              className={`px-8 py-3 rounded-lg font-bold uppercase tracking-wide transition-all ${
                isUnlocking
                  ? 'bg-emerald-900 text-emerald-400 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/50'
              }`}
            >
              {isUnlocking ? (
                <span className="flex items-center space-x-2">
                  <span className="animate-spin">⏳</span>
                  <span>Processing...</span>
                </span>
              ) : (
                '🔓 UNLOCK DOOR'
              )}
            </button>

            <button
              onClick={() => handleCommand('SILENCE')}
              disabled={isSilencing}
              className={`px-8 py-3 rounded-lg font-bold uppercase tracking-wide transition-all ${
                isSilencing
                  ? 'bg-orange-900 text-orange-400 cursor-not-allowed'
                  : 'bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/50'
              }`}
            >
              {isSilencing ? (
                <span className="flex items-center space-x-2">
                  <span className="animate-spin">⏳</span>
                  <span>Processing...</span>
                </span>
              ) : (
                '🔇 SILENCE ALARMS'
              )}
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
