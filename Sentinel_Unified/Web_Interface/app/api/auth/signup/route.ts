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
    const { name, email, password } = body
    const normalizedEmail = (email || '').trim().toLowerCase()

    // Validate input
    if (!name || !normalizedEmail || !password) {
      return NextResponse.json({ message: 'Missing required fields' }, { status: 400 })
    }

    console.log('🔄 [SIGNUP] Attempting MongoDB connection...')
    try {
      const usersCollection = await getCollection<User>('users')
      console.log('✅ [SIGNUP] Connected to MongoDB users collection')

      // Check if user exists
      const userExists = await usersCollection.findOne({ email: normalizedEmail })
      if (userExists) {
        console.log('⚠️  [SIGNUP] User already exists:', normalizedEmail)
        return NextResponse.json({ message: 'User already exists' }, { status: 409 })
      }

      // Hash password
      const hashedPassword = await bcrypt.hash(password, 10)
      console.log('✓ [SIGNUP] Password hashed')

      // Create new user
      const result = await usersCollection.insertOne({
        name,
        email: normalizedEmail,
        password: hashedPassword,
        createdAt: new Date(),
      })
      console.log('✅ [SIGNUP] User saved to MongoDB! ID:', result.insertedId)
      console.log('📧 [SIGNUP] Email:', normalizedEmail)
      console.log('👤 [SIGNUP] Name:', name)

      const userId = result.insertedId.toString()

      // Create mock JWT token
      const token = Buffer.from(
        JSON.stringify({ id: userId, email: normalizedEmail, name })
      ).toString('base64')

      return NextResponse.json(
        {
          token,
          user: { id: userId, name, email },
        },
        { status: 201 }
      )
    } catch (dbError) {
      console.error('=' .repeat(60))
      console.error('❌ [SIGNUP] MongoDB CONNECTION FAILED!')
      console.error('Error type:', (dbError as any)?.name)
      console.error('Error message:', (dbError as any)?.message)
      console.error('Stack:', (dbError as any)?.stack)
      console.error('=' .repeat(60))
      console.warn('⚠️  [SIGNUP] FALLING BACK TO MOCK USERS (IN-MEMORY ONLY)')
      console.warn('⚠️  [SIGNUP] User will NOT be saved to database!')
      console.warn('⚠️  [SIGNUP] User will be lost on server restart!')
      
      // Fallback to mock users if database is not available
      if (mockUsers[email]) {
        return NextResponse.json({ message: 'User already exists' }, { status: 409 })
      }

      // Hash password
      const hashedPassword = await bcrypt.hash(password, 10)
      const userId = `mock_${Date.now()}`

      // Store in mock users
      mockUsers[email] = {
        id: userId,
        name,
        email,
        password: hashedPassword,
      }
      console.log('⚠️  [SIGNUP] User stored in MOCK memory (temporary):', email)

      const token = Buffer.from(
        JSON.stringify({ id: userId, email, name })
      ).toString('base64')

      return NextResponse.json(
        {
          token,
          user: { id: userId, name, email },
        },
        { status: 201 }
      )
    }
  } catch (error) {
    console.error('Signup error:', error)
    return NextResponse.json({ message: 'Invalid request' }, { status: 400 })
  }
}
