'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'

export default function SignupPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState<string>('')
  const [isLoading, setIsLoading] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      setIsLoading(false)
      return
    }

    try {
      const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          password: formData.password,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.message || 'Signup failed')
      }

      const data = await response.json()
      localStorage.setItem('token', data.token)
      router.push('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f9f3e5] via-[#f4ead7] to-[#eadcc4] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="glass p-8 rounded-lg shadow-2xl fade-in border border-sentinel/30">
          <div className="flex items-center gap-3 mb-6">
            <div className="h-16 w-16 rounded-xl bg-sentinel/10 border border-sentinel/40 flex items-center justify-center">
              <Image src="/sentinel-logo.svg" alt="Sentinel" width={48} height={48} priority />
            </div>
            <div>
              <p className="text-sentinel text-xs uppercase tracking-[0.2em] font-semibold">Sentinel Secure</p>
              <h1 className="text-3xl font-bold text-[#1f1a17]">Create Account</h1>
            </div>
          </div>
          <p className="text-gray-700 mb-8">Join your security dashboard</p>

          {error && (
            <div className="bg-red-100 border border-red-200 text-red-800 px-4 py-3 rounded-lg mb-6 slide-in">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-gray-800 text-sm font-medium mb-2">
                Full Name
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 bg-white border border-[#d9cbb2] rounded-lg text-gray-900 placeholder-gray-600 focus:outline-none focus:border-sentinel transition"
                placeholder="John Doe"
              />
            </div>

            <div>
              <label className="block text-gray-800 text-sm font-medium mb-2">
                Email Address
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 bg-white border border-[#d9cbb2] rounded-lg text-gray-900 placeholder-gray-600 focus:outline-none focus:border-sentinel transition"
                placeholder="your@email.com"
              />
            </div>

            <div>
              <label className="block text-gray-800 text-sm font-medium mb-2">
                Password
              </label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 bg-white border border-[#d9cbb2] rounded-lg text-gray-900 placeholder-gray-600 focus:outline-none focus:border-sentinel transition"
                placeholder="••••••••"
              />
            </div>

            <div>
              <label className="block text-gray-800 text-sm font-medium mb-2">
                Confirm Password
              </label>
              <input
                type="password"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                required
                className="w-full px-4 py-2 bg-white border border-[#d9cbb2] rounded-lg text-gray-900 placeholder-gray-600 focus:outline-none focus:border-sentinel transition"
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-[#8b2e3a] to-[#4c0f14] hover:from-[#a03745] hover:to-[#5f1219] disabled:bg-gray-300 disabled:from-gray-300 disabled:to-gray-300 text-white font-bold py-3 rounded-lg transition duration-200 shadow-lg"
            >
              {isLoading ? 'Creating account...' : 'Sign Up'}
            </button>
          </form>

          <p className="text-center text-gray-700 mt-6">
            Already have an account?{' '}
            <Link
              href="/auth/login"
              className="text-sentinel hover:text-sentinel/80 font-semibold transition"
            >
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
