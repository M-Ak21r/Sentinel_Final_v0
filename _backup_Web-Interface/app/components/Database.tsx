'use client'

import { useEffect, useState } from 'react'

interface DatabaseRecord {
  id: string
  timestamp: string
  event: string
  location: string
  severity: 'low' | 'medium' | 'high'
}

export default function DatabaseComponent() {
  const [records, setRecords] = useState<DatabaseRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    fetchRecords()
  }, [])

  const fetchRecords = async () => {
    try {
      const response = await fetch('/api/database/records', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setRecords(data)
      }
    } catch (error) {
      console.error('Failed to fetch records:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'medium':
        return 'bg-amber-100 text-amber-800 border-amber-200'
      case 'low':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200'
      default:
        return ''
    }
  }

  if (isLoading) {
    return <div className="text-center py-8">Loading database...</div>
  }

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold mb-6 text-[#1f1a17]">Event Database</h2>
      {records.length === 0 ? (
        <div className="text-center py-8 text-gray-600">No records found</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-300">
                <th className="text-left px-4 py-3 text-gray-700 font-semibold">Timestamp</th>
                <th className="text-left px-4 py-3 text-gray-700 font-semibold">Event</th>
                <th className="text-left px-4 py-3 text-gray-700 font-semibold">Location</th>
                <th className="text-left px-4 py-3 text-gray-700 font-semibold">Severity</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id} className="border-b border-gray-200 hover:bg-gray-100 transition">
                  <td className="px-4 py-3">{record.timestamp}</td>
                  <td className="px-4 py-3">{record.event}</td>
                  <td className="px-4 py-3">{record.location}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-3 py-1 rounded-full border text-xs font-semibold ${getSeverityColor(
                        record.severity
                      )}`}
                    >
                      {record.severity}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
