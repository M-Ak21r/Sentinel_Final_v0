/**
 * Script to create an admin user in MongoDB
 * Run with: node scripts/create-admin-user.js
 */

require('dotenv').config({ path: '.env.local' })
const { MongoClient } = require('mongodb')
const bcrypt = require('bcryptjs')

async function createAdminUser() {
  const client = new MongoClient(process.env.MONGODB_URI)
  
  try {
    console.log('🔗 Connecting to MongoDB...')
    await client.connect()
    console.log('✅ Connected!')
    
    const db = client.db(process.env.MONGODB_DB || 'security_dashboard')
    const usersCollection = db.collection('users')
    
    // Admin credentials - CHANGE THESE!
    const email = 'admin@sentinel.com'
    const password = 'admin123'
    const name = 'Admin User'
    
    // Check if admin already exists
    const existingUser = await usersCollection.findOne({ email })
    if (existingUser) {
      console.log('❌ Admin user already exists with email:', email)
      return
    }
    
    // Hash password
    console.log('🔐 Hashing password...')
    const hashedPassword = await bcrypt.hash(password, 10)
    
    // Insert user
    console.log('💾 Creating user in database...')
    const result = await usersCollection.insertOne({
      name,
      email,
      password: hashedPassword,
      createdAt: new Date(),
    })
    
    console.log('\n✅ Admin user created successfully!')
    console.log('=' .repeat(50))
    console.log('📧 Email:', email)
    console.log('🔑 Password:', password)
    console.log('🆔 User ID:', result.insertedId)
    console.log('=' .repeat(50))
    console.log('\n⚠️  Please change the password after first login!')
    
  } catch (error) {
    console.error('❌ Error creating admin user:', error)
    console.error('Error details:', error.message)
  } finally {
    await client.close()
    console.log('\n👋 Connection closed')
  }
}

createAdminUser()
