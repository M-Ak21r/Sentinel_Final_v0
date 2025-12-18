'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/app/components/Sidebar'
import FaceCapture from '@/app/components/FaceCapture'

interface AuthorizedFace {
  id: string
  name: string
  email?: string
  createdAt?: string
  imagePreview?: string
}

export default function FacesPage() {
  const router = useRouter()
  const [faces, setFaces] = useState<AuthorizedFace[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showCapture, setShowCapture] = useState<boolean | string>(false)
  const [personName, setPersonName] = useState('')
  const [personEmail, setPersonEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState<string | null>(null)
  
  // New state for file upload
  const [showUpload, setShowUpload] = useState(false)
  const [uploadName, setUploadName] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/auth/login')
      return
    }
    fetchFaces()
  }, [router])

  const fetchFaces = async () => {
    try {
      setIsLoading(true)
      const response = await fetch('/api/faces', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setFaces(data.faces)
      } else {
        setError('Failed to load faces')
      }
    } catch (err) {
      setError('Error loading faces')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCaptureFace = async (descriptor: number[], imageBase64: string) => {
    if (!personName.trim()) {
      setError('Please enter a name for this person')
      return
    }

    try {
      setIsLoading(true)
      const response = await fetch('/api/faces', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          name: personName,
          email: personEmail,
          faceDescriptor: descriptor,
          imageBase64,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        setSuccess(`${personName} has been registered successfully!`)
        setPersonName('')
        setPersonEmail('')
        setShowCapture(false)
        setError(null)
        setTimeout(() => setSuccess(null), 3000)
        fetchFaces()
      } else {
        const data = await response.json()
        setError(data.message || 'Failed to register face')
      }
    } catch (err) {
      setError('Error registering face')
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteFace = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to remove ${name}?`)) return

    try {
      setIsDeleting(id)
      const response = await fetch(`/api/faces/${id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })

      if (response.ok) {
        setSuccess(`${name} has been removed`)
        setTimeout(() => setSuccess(null), 3000)
        fetchFaces()
      } else {
        setError('Failed to delete face')
      }
    } catch (err) {
      setError('Error deleting face')
      console.error(err)
    } finally {
      setIsDeleting(null)
    }
  }

  const handleFileUpload = async () => {
    if (!uploadName.trim()) {
      setError('Please enter a name')
      return
    }

    if (!uploadFile) {
      setError('Please select a file')
      return
    }

    try {
      setIsUploading(true)
      setError(null)

      const formData = new FormData()
      formData.append('name', uploadName)
      formData.append('file', uploadFile)

      const response = await fetch('/api/faces/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setSuccess('Agent Authorized. Neural Nets Updated.')
        setUploadName('')
        setUploadFile(null)
        setShowUpload(false)
        setTimeout(() => setSuccess(null), 3000)
      } else {
        setError(data.message || 'Failed to upload face')
      }
    } catch (err) {
      setError('Error uploading face')
      console.error(err)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-gray-900">
      <Sidebar />

      <main className="flex-1 overflow-auto ml-20 md:ml-64 px-4 md:px-8 pb-12">
        <div className="pt-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2">Authorized Personnel Database</h1>
              <p className="text-gray-400">Manage facial recognition for authorized personnel</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  if (!showUpload) {
                    setUploadName('')
                    setUploadFile(null)
                    setError(null)
                  }
                  setShowUpload(!showUpload)
                  setShowCapture(false)
                }}
                className="px-6 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white font-semibold rounded-lg transition shadow-lg"
              >
                {showUpload ? '✕ Close' : '+ Upload Photo'}
              </button>
              <button
                onClick={() => {
                  if (!showCapture) {
                    setPersonName('')
                    setPersonEmail('')
                    setError(null)
                  }
                  setShowCapture(!showCapture)
                  setShowUpload(false)
                }}
                className="px-6 py-3 bg-gradient-to-r from-[#8b2e3a] to-[#4c0f14] hover:from-[#a03745] hover:to-[#5f1219] text-white font-semibold rounded-lg transition shadow-lg"
              >
                {showCapture ? '✕ Close' : '+ Scan Face'}
              </button>
            </div>
          </div>

          {/* Upload Photo Form - NEW FEATURE */}
          {showUpload && (
            <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg p-6 mb-8 border border-green-600">
              <h2 className="text-xl font-bold text-white mb-4">
                <span className="text-green-400">⚡</span> AUTHORIZE NEW AGENT
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left Side - Upload Form */}
                <div>
                  <div className="mb-4">
                    <label className="block text-gray-300 text-sm font-medium mb-2">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      value={uploadName}
                      onChange={(e) => setUploadName(e.target.value)}
                      placeholder="e.g., John Doe"
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
                      disabled={isUploading}
                    />
                  </div>

                  <div className="mb-4">
                    <label className="block text-gray-300 text-sm font-medium mb-2">
                      Reference Photo *
                    </label>
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) {
                          setUploadFile(file)
                        }
                      }}
                      className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-600 file:text-white hover:file:bg-green-700 focus:outline-none focus:border-green-500"
                      disabled={isUploading}
                    />
                    {uploadFile && (
                      <p className="text-green-400 text-sm mt-2">
                        ✓ {uploadFile.name}
                      </p>
                    )}
                  </div>

                  {error && (
                    <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded-lg mb-4">
                      {error}
                    </div>
                  )}

                  <button
                    onClick={handleFileUpload}
                    disabled={!uploadName.trim() || !uploadFile || isUploading}
                    className="w-full px-4 py-3 bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition shadow-lg uppercase tracking-wider"
                  >
                    {isUploading ? (
                      <span className="flex items-center justify-center">
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Uploading & Training...
                      </span>
                    ) : (
                      'AUTHORIZE NEW AGENT'
                    )}
                  </button>
                </div>

                {/* Right Side - Info/Placeholder */}
                <div className="bg-gray-700 bg-opacity-50 rounded-lg p-6 flex flex-col justify-center">
                  <div className="text-center">
                    <div className="text-4xl mb-4">🗄️</div>
                    <h3 className="text-lg font-bold text-white mb-2">Existing Database</h3>
                    <p className="text-gray-400 text-sm mb-4">
                      [Managed via File System]
                    </p>
                    <p className="text-gray-500 text-xs">
                      Uploaded faces are stored in the shared data directory and automatically synced with Python services for real-time recognition.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Add Face Form */}
          {showCapture && (
            <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg p-6 mb-8 border border-gray-700">
              <h2 className="text-xl font-bold text-white mb-4">Register New Person</h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">Full Name *</label>
                  <input
                    type="text"
                    value={personName}
                    onChange={(e) => setPersonName(e.target.value)}
                    placeholder="e.g., John Doe"
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#d9534f]"
                  />
                </div>

                <div>
                  <label className="block text-gray-300 text-sm font-medium mb-2">Email (Optional)</label>
                  <input
                    type="email"
                    value={personEmail}
                    onChange={(e) => setPersonEmail(e.target.value)}
                    placeholder="john@example.com"
                    className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-[#d9534f]"
                  />
                </div>
              </div>

              {error && (
                <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded-lg mb-4">
                  {error}
                </div>
              )}

              <button
                onClick={() => setShowCapture('capture')}
                disabled={!personName.trim() || isLoading}
                className="w-full px-4 py-3 bg-gradient-to-r from-[#8b2e3a] to-[#4c0f14] hover:from-[#a03745] hover:to-[#5f1219] disabled:bg-gray-600 text-white font-semibold rounded-lg transition"
              >
                {isLoading ? 'Processing...' : 'Start Face Scan'}
              </button>

              {/* Face Capture Modal */}
              {showCapture === 'capture' && (
                <FaceCapture
                  onCapture={(descriptor, imageBase64) => {
                    handleCaptureFace(descriptor, imageBase64)
                  }}
                  onCancel={() => setShowCapture(true)}
                />
              )}
            </div>
          )}

          {/* Success Message */}
          {success && (
            <div className="bg-green-900 border border-green-700 text-green-100 px-4 py-3 rounded-lg mb-6">
              ✓ {success}
            </div>
          )}

          {/* Faces Grid */}
          {isLoading ? (
            <div className="flex items-center justify-center h-96">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#d9534f] mx-auto mb-4"></div>
                <p className="text-gray-400">Loading authorized faces...</p>
              </div>
            </div>
          ) : faces.length === 0 ? (
            <div className="bg-gray-800 rounded-lg p-12 text-center border border-gray-700">
              <p className="text-gray-400 text-lg mb-4">No authorized faces registered yet</p>
              <p className="text-gray-500">Add your first authorized person using the "Add Face" button above</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {faces.map((face) => (
                <div key={face.id} className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-lg overflow-hidden border border-gray-700 hover:border-gray-600 transition">
                  {/* Face Image */}
                  <div className="aspect-square bg-gray-700 flex items-center justify-center overflow-hidden">
                    {face.imagePreview ? (
                      <img src={face.imagePreview} alt={face.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <svg
                          className="w-16 h-16 text-gray-600"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
                        </svg>
                      </div>
                    )}
                  </div>

                  {/* Face Info */}
                  <div className="p-4">
                    <h3 className="text-lg font-bold text-white mb-1">{face.name}</h3>
                    {face.email && <p className="text-gray-400 text-sm mb-3">{face.email}</p>}
                    {face.createdAt && (
                      <p className="text-gray-500 text-xs mb-4">
                        Added: {new Date(face.createdAt).toLocaleDateString()}
                      </p>
                    )}

                    <button
                      onClick={() => handleDeleteFace(face.id, face.name)}
                      disabled={isDeleting === face.id}
                      className="w-full px-4 py-2 bg-red-900 hover:bg-red-800 disabled:bg-gray-600 text-white font-semibold rounded-lg transition text-sm"
                    >
                      {isDeleting === face.id ? 'Removing...' : 'Remove'}
                    </button>
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
