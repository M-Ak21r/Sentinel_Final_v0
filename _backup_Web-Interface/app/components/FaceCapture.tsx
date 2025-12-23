'use client'

import { useEffect, useRef, useState } from 'react'

interface FaceCaptureProps {
  onCapture: (descriptor: number[], imageBase64: string) => void
  onCancel: () => void
}

declare global {
  interface Window {
    faceapi: any
  }
}

export default function FaceCapture({ onCapture, onCancel }: FaceCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [faceDetected, setFaceDetected] = useState(false)
  const [modelsLoaded, setModelsLoaded] = useState(false)

  useEffect(() => {
    const initializeCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 } },
        })

        if (videoRef.current) {
          videoRef.current.srcObject = stream
          videoRef.current.onloadedmetadata = () => {
            videoRef.current?.play()
            setIsLoading(false)
          }
        }
      } catch (err) {
        setError('Camera access denied. Please allow camera permissions.')
        console.error('Camera error:', err)
      }
    }

    const loadModels = async () => {
      try {
        // Load face-api models from CDN
        const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/'
        // @ts-ignore
        if (typeof window !== 'undefined' && window.faceapi) {
          // @ts-ignore
          await window.faceapi.nets.tinyFaceDetector.load(MODEL_URL)
          // @ts-ignore
          await window.faceapi.nets.faceLandmark68Net.load(MODEL_URL)
          // @ts-ignore
          await window.faceapi.nets.faceRecognitionNet.load(MODEL_URL)
          setModelsLoaded(true)
        }
      } catch (err) {
        console.error('Model loading error:', err)
        setError('Failed to load face detection models')
      }
    }

    // Load script
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/dist/face-api.js'
    script.onload = () => {
      loadModels()
      initializeCamera()
    }
    script.onerror = () => {
      setError('Failed to load face detection library')
    }
    document.body.appendChild(script)

    return () => {
      if (videoRef.current?.srcObject) {
        const tracks = (videoRef.current.srcObject as MediaStream).getTracks()
        tracks.forEach(track => track.stop())
      }
    }
  }, [])

  useEffect(() => {
    if (!modelsLoaded || !videoRef.current || isLoading) return

    const detectFace = async () => {
      try {
        // @ts-ignore
        if (!window.faceapi) return

        // @ts-ignore
        const detections = await window.faceapi
          .detectAllFaces(videoRef.current, new window.faceapi.TinyFaceDetectorOptions())
          .withFaceLandmarks()
          .withFaceDescriptors()

        setFaceDetected(detections.length > 0)
      } catch (err) {
        console.error('Detection error:', err)
      }
    }

    const interval = setInterval(detectFace, 500)
    return () => clearInterval(interval)
  }, [modelsLoaded, isLoading])

  const captureFrame = async () => {
    if (!videoRef.current || !canvasRef.current) return

    try {
      setIsLoading(true)

      const canvas = canvasRef.current
      const video = videoRef.current
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight

      const ctx = canvas.getContext('2d')
      if (!ctx) return

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      const imageBase64 = canvas.toDataURL('image/png').split(',')[1]

      // Detect face and get descriptor
      // @ts-ignore
      const detections = await window.faceapi
        .detectAllFaces(video, new window.faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptors()

      if (detections.length === 0) {
        setError('No face detected. Please try again.')
        return
      }

      // Use first detected face
      const descriptor = Array.from(detections[0].descriptor) as number[]

      onCapture(descriptor, imageBase64)
      setIsLoading(false)
    } catch (err) {
      console.error('Capture error:', err)
      setError('Failed to capture face')
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-2xl max-w-md w-full p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Scan Face</h2>

        <div className="relative bg-gray-900 rounded-lg overflow-hidden mb-4" style={{ aspectRatio: '4/3' }}>
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
              <div className="text-white text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-2"></div>
                <p>Initializing camera...</p>
              </div>
            </div>
          )}

          <video
            ref={videoRef}
            className="w-full h-full object-cover"
            playsInline
            muted
            style={{ display: isLoading ? 'none' : 'block' }}
          />

          {faceDetected && !isLoading && (
            <div className="absolute top-4 right-4 bg-green-500 text-white px-3 py-1 rounded-full text-sm font-semibold">
              ✓ Face Detected
            </div>
          )}

          {!faceDetected && !isLoading && (
            <div className="absolute top-4 right-4 bg-red-500 text-white px-3 py-1 rounded-full text-sm font-semibold">
              ✗ No Face
            </div>
          )}
        </div>

        <canvas ref={canvasRef} className="hidden" />

        {error && <div className="bg-red-100 text-red-800 p-3 rounded-lg mb-4 text-sm">{error}</div>}

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 px-4 py-2 bg-gray-300 text-gray-900 font-semibold rounded-lg hover:bg-gray-400 transition"
          >
            Cancel
          </button>
          <button
            onClick={captureFrame}
            disabled={!faceDetected || isLoading}
            className="flex-1 px-4 py-2 bg-gradient-to-r from-[#8b2e3a] to-[#4c0f14] text-white font-semibold rounded-lg hover:from-[#a03745] hover:to-[#5f1219] disabled:bg-gray-400 disabled:cursor-not-allowed transition"
          >
            {isLoading ? 'Processing...' : 'Capture'}
          </button>
        </div>

        <p className="text-gray-600 text-xs mt-4 text-center">
          Position your face in the camera frame and make sure it's clearly visible.
        </p>
      </div>
    </div>
  )
}
