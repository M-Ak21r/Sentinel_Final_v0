'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/app/components/Sidebar'

export default function SettingsPage() {
  const router = useRouter()
  const [settings, setSettings] = useState({ theme: 'dark', notifications: true })

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      router.push('/auth/login')
    }
  }, [router])

  return (
    <div className="flex">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">
        <div className="max-w-3xl mx-auto">
          <div className="mb-8">
            <h1 className="text-4xl font-bold mb-2">Settings</h1>
            <p className="text-gray-400">Manage your dashboard preferences</p>
          </div>

          <div className="space-y-6">
            <div className="glass p-6 rounded-lg">
              <h2 className="text-xl font-bold mb-4">General Settings</h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-3 border-b border-gray-700">
                  <label className="text-gray-300">Theme</label>
                  <select className="bg-gray-700 px-3 py-1 rounded border border-gray-600">
                    <option>Dark Mode</option>
                    <option>Light Mode</option>
                  </select>
                </div>
                <div className="flex items-center justify-between py-3 border-b border-gray-700">
                  <label className="text-gray-300">Notifications</label>
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                </div>
                <div className="flex items-center justify-between py-3">
                  <label className="text-gray-300">Email Alerts</label>
                  <input type="checkbox" defaultChecked className="w-4 h-4" />
                </div>
              </div>
            </div>

            <div className="glass p-6 rounded-lg">
              <h2 className="text-xl font-bold mb-4">Security</h2>
              <button className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded transition">
                Change Password
              </button>
            </div>

            <div className="glass p-6 rounded-lg">
              <h2 className="text-xl font-bold mb-4">Danger Zone</h2>
              <button className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded transition">
                Delete Account
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
