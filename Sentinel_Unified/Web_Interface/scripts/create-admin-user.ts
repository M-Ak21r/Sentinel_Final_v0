/**
 * Script to create an admin user in MongoDB
 * Run with: npx tsx scripts/create-admin-user.ts
 */

import { getCollection, closeDb } from '../lib/mongo'
import bcrypt from 'bcryptjs'

async function createAdminUser() {
  try {
    console.log('🔗 Connecting to MongoDB...')
    
    const usersCollection = await getCollection('users')
    
    // Admin credentials
    const email = 'admin@sentinel.com'
    const password = 'admin123' // Change this to your desired password
    const name = 'Admin User'
    
    // Check if admin already exists
    const existingUser = await usersCollection.findOne({ email })
    if (existingUser) {
      console.log('❌ Admin user already exists!')
      return
    }
    
    // Hash password
    const hashedPassword = await bcrypt.hash(password, 10)
    
    // Insert user
    const result = await usersCollection.insertOne({
      name,
      email,
      password: hashedPassword,
      createdAt: new Date(),
    })
    
    console.log('✅ Admin user created successfully!')
    console.log('📧 Email:', email)
    console.log('🔑 Password:', password)
    console.log('🆔 User ID:', result.insertedId)
    console.log('\n⚠️  Please change the password after first login!')
    
  } catch (error) {
    console.error('❌ Error creating admin user:', error)
  } finally {
    await closeDb()
    process.exit(0)
  }
}

createAdminUser()
