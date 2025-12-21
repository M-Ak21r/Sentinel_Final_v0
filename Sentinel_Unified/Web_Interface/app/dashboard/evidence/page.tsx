'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/app/components/Sidebar'

interface SecurityEvent {
  id: string
  topic: string
  level?: string
  event?: string
  snapshotUrl?: string | null
  createdAt: string
  status?: string
  confidence?: number
  cameraId?: string
}

export default function EvidenceGallery() {
  const router = useRouter()
  const [events, setEvents] = useState<SecurityEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/auth/login')
      return
    }
    fetchEvents()
  }, [router])

  const fetchEvents = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/evidence', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setEvents(data.events)
      } else {
        setError('Failed to load events')
      }
    } catch (err) {
      setError('Error loading events')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getEventColor = (event?: string) => {
    if (!event) return 'text-gray-400'
    
    const eventUpper = event.toUpperCase()
    if (eventUpper.includes('INTRUDER') || eventUpper.includes('ALERT') || eventUpper.includes('UNAUTHORIZED')) {
      return 'text-red-400'
    }
    if (eventUpper.includes('ACCESS') || eventUpper.includes('AUTHORIZED')) {
      return 'text-green-400'
    }
    return 'text-yellow-400'
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleString()
    } catch {
      return timestamp
    }
  }

  return (
    <div className="flex min-h-screen bg-gray-900">
      <Sidebar />

      <main className="flex-1 overflow-auto ml-20 md:ml-64 px-4 md:px-8 pb-12">
        <div className="pt-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-white mb-2">Security Evidence Log</h1>
            <p className="text-gray-400">Recent security events and detections</p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loading ? (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
                <p className="text-gray-400">Loading evidence...</p>
              </div>
            </div>
          ) : events.length === 0 ? (
            <div className="bg-gray-800 rounded-lg p-12 text-center border border-gray-700">
              <p className="text-gray-400 text-lg mb-4">No security events recorded yet</p>
              <p className="text-gray-500">Events will appear here as they are detected</p>
            </div>
          ) : (
            // Responsive Grid: 1 col mobile, 2 col tablet, 3 col desktop
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg overflow-hidden border border-gray-700 hover:border-gray-600 transition"
                >
                  {/* Image/Snapshot */}
                  <div className="aspect-video bg-gray-700 flex items-center justify-center overflow-hidden">
                    {event.snapshotUrl ? (
                      <img
                        src={event.snapshotUrl}
                        alt={event.event || 'Event snapshot'}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <svg
                          className="w-16 h-16 text-gray-600"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" />
                        </svg>
                      </div>
                    )}
                  </div>

                  {/* Event Info */}
                  <div className="p-4">
                    {/* Event Header - Color Coded */}
                    <h3 className={`text-lg font-bold mb-2 ${getEventColor(event.event)}`}>
                      {event.event || 'UNKNOWN_EVENT'}
                    </h3>

                    {/* Status */}
                    {event.status && (
                      <p className="text-gray-400 text-sm mb-2">{event.status}</p>
                    )}

                    {/* Timestamp */}
                    <p className="text-gray-500 text-xs mb-3">
                      {formatTimestamp(event.createdAt)}
                    </p>

                    {/* Metadata */}
                    <div className="space-y-1 text-xs">
                      {event.confidence !== undefined && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Confidence:</span>
                          <span className="text-gray-300">{(event.confidence * 100).toFixed(1)}%</span>
                        </div>
                      )}
                      {event.level && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Level:</span>
                          <span className="text-gray-300">{event.level}</span>
                        </div>
                      )}
                      {event.cameraId && (
                        <div className="flex justify-between">
                          <span className="text-gray-500">Camera:</span>
                          <span className="text-gray-300">{event.cameraId}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
