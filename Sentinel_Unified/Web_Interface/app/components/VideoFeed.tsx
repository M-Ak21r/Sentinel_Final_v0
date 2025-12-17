'use client'

import { useState } from 'react'

interface VideoFeedProps {
  src: string
  label: string
}

export default function VideoFeed({ src, label }: VideoFeedProps) {
  const [hasError, setHasError] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)

  const handleError = () => {
    setHasError(true)
  }

  const handleRetry = () => {
    setIsRetrying(true)
    setHasError(false)
    
    // Force a reload by adding a timestamp to the src
    const img = document.getElementById(`video-${label}`) as HTMLImageElement
    if (img) {
      img.src = `${src}?t=${Date.now()}`
    }
    
    // Reset retrying state after a delay
    setTimeout(() => {
      setIsRetrying(false)
    }, 2000)
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      {/* Label */}
      <div className="bg-slate-900 px-4 py-2 border-b border-slate-700">
        <h3 className="text-cyan-400 font-semibold text-sm uppercase tracking-wide">
          {label}
        </h3>
      </div>

      {/* Video Feed */}
      <div className="relative aspect-video bg-slate-950">
        {hasError ? (
          // NO SIGNAL Placeholder
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-950">
            <div className="text-center space-y-4">
              <div className="text-6xl mb-4">📡</div>
              <div className="text-red-500 text-2xl font-bold uppercase tracking-wider">
                NO SIGNAL
              </div>
              <div className="text-slate-400 text-sm">
                Camera feed unavailable
              </div>
              <button
                onClick={handleRetry}
                disabled={isRetrying}
                className={`mt-4 px-6 py-2 rounded-lg font-semibold transition-all ${
                  isRetrying
                    ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                    : 'bg-cyan-600 hover:bg-cyan-500 text-white'
                }`}
              >
                {isRetrying ? 'Retrying...' : 'RETRY CONNECTION'}
              </button>
            </div>
          </div>
        ) : (
          // Live Stream
          // eslint-disable-next-line @next/next/no-img-element
          <img
            id={`video-${label}`}
            src={src}
            alt={`${label} video feed`}
            className="w-full h-full object-cover"
            onError={handleError}
          />
        )}
        
        {/* Live Indicator */}
        {!hasError && (
          <div className="absolute top-3 left-3 flex items-center space-x-2 bg-black bg-opacity-60 px-3 py-1 rounded-full">
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
            <span className="text-white text-xs font-semibold">LIVE</span>
          </div>
        )}
      </div>
    </div>
  )
}
