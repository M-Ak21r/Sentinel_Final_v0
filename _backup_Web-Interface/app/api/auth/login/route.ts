import { NextRequest, NextResponse } from 'next/server'
import { getCollection } from '@/lib/mongo'
import bcrypt from 'bcryptjs'
import { mockUsers } from '@/lib/mock-users'

interface User {
  _id?: any
  name: string
  email: string
  password: string
  createdAt: Date
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email, password } = body
    const normalizedEmail = (email || '').trim().toLowerCase()

    // Validate input
    if (!normalizedEmail || !password) {
      return NextResponse.json({ message: 'Missing credentials' }, { status: 400 })
    }

    try {
      const usersCollection = await getCollection<User>('users')
      console.log('✓ Connected to users collection')

      // Find user
      const user = await usersCollection.findOne({ email: normalizedEmail })
      console.log('User lookup result:', user ? 'Found' : 'Not found')

      if (!user) {
        return NextResponse.json({ message: 'Invalid credentials' }, { status: 401 })
      }

      // Compare passwords
      const isPasswordValid = await bcrypt.compare(password, user.password)
      if (!isPasswordValid) {
        return NextResponse.json({ message: 'Invalid credentials' }, { status: 401 })
      }

      const userId = user._id.toString()

      // Create mock JWT token
      const token = Buffer.from(
        JSON.stringify({ id: userId, email: user.email, name: user.name })
      ).toString('base64')

      return NextResponse.json({
        token,
        user: { id: userId, name: user.name, email: user.email },
      })
    } catch (dbError) {
      console.error('❌ Database error during login:', dbError)
      console.error('Error type:', (dbError as any)?.name)
      console.error('Error message:', (dbError as any)?.message)
      
      // Fallback to mock users if database is not available
      const mockUser = mockUsers[email]
      if (!mockUser) {
        return NextResponse.json({ message: 'Invalid credentials' }, { status: 401 })
      }

      const isPasswordValid = await bcrypt.compare(password, mockUser.password)
      if (!isPasswordValid) {
        return NextResponse.json({ message: 'Invalid credentials' }, { status: 401 })
      }

      const token = Buffer.from(
        JSON.stringify({ id: mockUser.id, email: mockUser.email, name: mockUser.name })
      ).toString('base64')

      return NextResponse.json({
        token,
        user: { id: mockUser.id, name: mockUser.name, email: mockUser.email },
      })
    }
  } catch (error) {
    console.error('Login error:', error)
    return NextResponse.json({ message: 'Invalid request' }, { status: 400 })
  }
}
