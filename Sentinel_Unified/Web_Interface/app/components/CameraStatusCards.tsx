'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface CameraFeed {
  id: string
  name: string
  status: 'online' | 'offline'
  lastUpdate: string
  snapshotUrl?: string
  event?: string
  confidence?: number
  model?: string
}

interface CameraStatusCardsProps {
  showViewStreamsButton?: boolean
}

export default function CameraStatusCards({ showViewStreamsButton = false }: CameraStatusCardsProps) {
  const [feeds, setFeeds] = useState<CameraFeed[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchFeeds()
    // Refresh every 30 seconds
    const interval = setInterval(fetchFeeds, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchFeeds = async () => {
    try {
      const response = await fetch('/api/feeds', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })
      
      if (response.ok) {
        const data = await response.json()
        setFeeds(data)
        setError(null)
      } else {
        setError('Failed to fetch camera status')
      }
    } catch (error) {
      console.error('Failed to fetch feeds:', error)
      setError('Connection error')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-8 text-center">
        <div className="animate-pulse flex flex-col items-center space-y-3">
          <div className="w-12 h-12 bg-slate-700 rounded-full"></div>
          <div className="text-slate-400">Loading camera status...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-slate-800 border border-yellow-700 rounded-lg p-6">
        <div className="flex items-start space-x-3">
          <span className="text-2xl">⚠️</span>
          <div className="flex-1">
            <h3 className="font-semibold text-yellow-400 mb-2">Camera Status Unavailable</h3>
            <p className="text-slate-300 text-sm mb-3">{error}</p>
            <div className="text-slate-400 text-sm space-y-1">
              <p>Possible reasons:</p>
              <ul className="list-disc list-inside ml-2">
                <li>MongoDB not connected</li>
                <li>No camera events published yet</li>
                <li>MQTT broker not running</li>
              </ul>
            </div>
            {showViewStreamsButton && (
              <Link 
                href="/dashboard/feeds"
                className="inline-block mt-4 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-semibold transition-colors"
              >
                📹 View Live Video Streams Instead
              </Link>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (feeds.length === 0) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-lg p-8">
        <div className="text-center space-y-4">
          <div className="text-6xl mb-2">📹</div>
          <h3 className="text-xl font-semibold text-slate-200">No Camera Activity Yet</h3>
          <p className="text-slate-400 text-sm max-w-md mx-auto">
            Cameras are configured but haven't published any events to MongoDB yet. 
            Once the system detects motion, faces, or other events, they'll appear here.
          </p>
          {showViewStreamsButton && (
            <Link 
              href="/dashboard/feeds"
              className="inline-block mt-4 px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-semibold transition-colors"
            >
              📹 View Live Video Streams
            </Link>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-cyan-400">Camera Status</h2>
        <button
          onClick={fetchFeeds}
          className="px-3 py-1 text-sm bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors"
        >
          🔄 Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {feeds.map((feed) => (
          <div
            key={feed.id}
            className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden hover:border-cyan-600 transition-colors"
          >
            {/* Camera Name Header */}
            <div className="bg-slate-900 px-4 py-2 border-b border-slate-700 flex items-center justify-between">
              <h3 className="font-semibold text-cyan-400 uppercase text-sm tracking-wide">
                {feed.name}
              </h3>
              <span
                className={`flex items-center space-x-1 text-xs font-semibold ${
                  feed.status === 'online' ? 'text-emerald-400' : 'text-red-400'
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    feed.status === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
                  }`}
                ></span>
                <span>{feed.status.toUpperCase()}</span>
              </span>
            </div>

            {/* Snapshot or Placeholder */}
            <div className="aspect-video bg-slate-950 flex items-center justify-center relative">
              {feed.snapshotUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={feed.snapshotUrl}
                  alt={`${feed.name} snapshot`}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-center text-slate-500">
                  <div className="text-4xl mb-2">📷</div>
                  <div className="text-sm">No snapshot available</div>
                </div>
              )}
              
              {/* Last Update Badge */}
              <div className="absolute bottom-2 right-2 bg-black bg-opacity-70 px-2 py-1 rounded text-xs text-slate-300">
                ⏱️ {feed.lastUpdate}
              </div>
            </div>

            {/* Event Information */}
            <div className="p-4 space-y-2">
              {feed.event && (
                <div className="flex items-start space-x-2">
                  <span className="text-yellow-400 text-sm">🔔</span>
                  <div className="flex-1">
                    <p className="text-slate-200 text-sm font-medium">
                      {feed.event}
                    </p>
                    {feed.confidence && (
                      <p className="text-slate-400 text-xs mt-1">
                        Confidence: {(feed.confidence * 100).toFixed(1)}%
                      </p>
                    )}
                  </div>
                </div>
              )}
              
              {feed.model && (
                <div className="text-slate-400 text-xs">
                  Model: {feed.model}
                </div>
              )}

              {!feed.event && (
                <p className="text-slate-500 text-sm italic">
                  No recent events
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {showViewStreamsButton && (
        <div className="mt-6 text-center">
          <Link 
            href="/dashboard/feeds"
            className="inline-block px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-semibold transition-colors"
          >
            📹 View Full Video Streams
          </Link>
        </div>
      )}
    </div>
  )
}
