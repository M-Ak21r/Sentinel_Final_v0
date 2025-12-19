'use client'

import { useEffect, useState } from 'react'

interface LiveFeed {
  id: string
  name: string
  status: 'online' | 'offline'
  lastUpdate: string
}

export default function LiveFeedComponent() {
  const [feeds, setFeeds] = useState<LiveFeed[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchFeeds()
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
      }
    } catch (error) {
      console.error('Failed to fetch feeds:', error)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return <div className="text-center py-8">Loading feeds...</div>
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold mb-6 text-[#1f1a17]">Live Feeds</h2>
      {feeds.length === 0 ? (
        <div className="text-center py-8 text-gray-600">No feeds configured yet</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {feeds.map((feed) => (
            <div key={feed.id} className="glass p-4 rounded-lg">
              <div className="aspect-video bg-[#e7dbc2] rounded-lg mb-3 flex items-center justify-center border border-[#d6c7aa]">
                <span className="text-gray-700">🎥 Camera Feed</span>
              </div>
              <h3 className="font-semibold">{feed.name}</h3>
              <div className="flex items-center justify-between mt-2 text-sm">
                <span
                  className={`${
                    feed.status === 'online' ? 'text-emerald-700' : 'text-red-700'
                  } flex items-center space-x-1`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      feed.status === 'online' ? 'bg-emerald-600' : 'bg-red-600'
                    }`}
                  ></span>
                  <span>{feed.status}</span>
                </span>
                <span className="text-gray-600">{feed.lastUpdate}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
