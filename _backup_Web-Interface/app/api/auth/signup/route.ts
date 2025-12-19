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

    try {
      const usersCollection = await getCollection<User>('users')
      console.log('✓ Connected to users collection')

      // Check if user exists
      const userExists = await usersCollection.findOne({ email: normalizedEmail })
      if (userExists) {
        return NextResponse.json({ message: 'User already exists' }, { status: 409 })
      }

      // Hash password
      const hashedPassword = await bcrypt.hash(password, 10)
      console.log('✓ Password hashed')

      // Create new user
      const result = await usersCollection.insertOne({
        name,
        email: normalizedEmail,
        password: hashedPassword,
        createdAt: new Date(),
      })
      console.log('✓ User inserted into MongoDB:', result.insertedId)

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
      console.error('❌ Database error during signup:', dbError)
      console.error('Error type:', (dbError as any)?.name)
      console.error('Error message:', (dbError as any)?.message)
      
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
