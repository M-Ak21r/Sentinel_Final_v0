'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/app/components/Sidebar'
import VideoFeed from '@/app/components/VideoFeed'

export default function FeedsPage() {
  const router = useRouter()

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/auth/login')
    }
  }, [router])

  return (
    <div className="flex min-h-screen bg-slate-900">
      <Sidebar />
      <main className="ml-64 flex-1 pb-24">
        {/* Header */}
        <div className="bg-slate-950 border-b border-slate-800 px-8 py-6">
          <h1 className="text-3xl font-bold text-cyan-400 uppercase tracking-wide">
            Live Camera Feeds
          </h1>
          <p className="text-slate-400 mt-1">Real-time video surveillance streams</p>
        </div>

        <div className="p-8">
          {/* Video Feeds Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-2 gap-6">
            <VideoFeed
              src={process.env.NEXT_PUBLIC_DOOR_SENTRY_URL || "http://localhost:5001/video_feed"}
              label="Door Sentry - Front Entrance"
            />
            <VideoFeed
              src={process.env.NEXT_PUBLIC_INTERIOR_WATCH_URL || "http://localhost:5002/video_feed"}
              label="Interior Watch - Main Room"
            />
          </div>

          {/* Feed Information */}
          <div className="mt-8 bg-slate-800 border border-slate-700 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-cyan-400 mb-4">Feed Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-slate-300">
              <div>
                <h3 className="font-semibold text-cyan-300 mb-2">🚪 Door Sentry</h3>
                <ul className="space-y-1 text-sm">
                  <li>• Face recognition enabled</li>
                  <li>• Gesture control active</li>
                  <li>• Motion detection: ON</li>
                  <li>• Port: 5001</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-cyan-300 mb-2">🏠 Interior Watch</h3>
                <ul className="space-y-1 text-sm">
                  <li>• Theft detection enabled</li>
                  <li>• Object tracking: ON</li>
                  <li>• Motion detection: ON</li>
                  <li>• Port: 5002</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Connection Help */}
          <div className="mt-6 bg-slate-800 border border-yellow-600 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <span className="text-2xl">⚠️</span>
              <div className="flex-1">
                <h3 className="font-semibold text-yellow-400 mb-2">Cannot see video feeds?</h3>
                <ul className="text-slate-300 text-sm space-y-1">
                  <li>1. Make sure Sentinel services are running: <code className="bg-slate-900 px-2 py-0.5 rounded text-cyan-400">python start_sentinel.py</code></li>
                  <li>2. Check that cameras are accessible at ports 5001 and 5002</li>
                  <li>3. Verify camera devices are connected and not in use by other programs</li>
                  <li>4. Click "RETRY CONNECTION" button on each feed</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
