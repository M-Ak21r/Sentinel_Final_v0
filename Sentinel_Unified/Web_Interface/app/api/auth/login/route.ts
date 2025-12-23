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

    console.log('🔄 [LOGIN] Attempting MongoDB connection...')
    try {
      const usersCollection = await getCollection<User>('users')
      console.log('✅ [LOGIN] Connected to MongoDB users collection')

      // Find user
      const user = await usersCollection.findOne({ email: normalizedEmail })
      console.log('🔍 [LOGIN] User lookup for:', normalizedEmail)
      console.log('📝 [LOGIN] Result:', user ? '✅ User found in MongoDB' : '❌ User not found')

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
      console.error('=' .repeat(60))
      console.error('❌ [LOGIN] MongoDB CONNECTION FAILED!')
      console.error('Error type:', (dbError as any)?.name)
      console.error('Error message:', (dbError as any)?.message)
      console.error('Stack:', (dbError as any)?.stack)
      console.error('=' .repeat(60))
      console.warn('⚠️  [LOGIN] FALLING BACK TO MOCK USERS (IN-MEMORY ONLY)')
      console.warn('⚠️  [LOGIN] Only users created in this session will work!')
      
      // Fallback to mock users if database is not available
      const mockUser = mockUsers[email]
      console.log('🔍 [LOGIN] Checking mock users for:', email)
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
