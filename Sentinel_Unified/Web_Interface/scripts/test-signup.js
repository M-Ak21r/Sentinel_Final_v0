/**
 * Signup Test Script
 * Run with: node scripts/test-signup.js
 * 
 * This script will:
 * 1. Test the signup API endpoint
 * 2. Create a test user
 * 3. Verify the user is saved to MongoDB
 */

require('dotenv').config({ path: '.env.local' })
const { MongoClient } = require('mongodb')
const bcrypt = require('bcryptjs')

async function testSignup() {
  console.log('🧪 Testing User Signup and MongoDB Storage')
  console.log('=' .repeat(60))
  
  const uri = process.env.MONGODB_URI
  const dbName = process.env.MONGODB_DB || 'security_dashboard'
  
  if (!uri) {
    console.error('❌ MONGODB_URI not found')
    return
  }
  
  const client = new MongoClient(uri)
  
  try {
    // Test user data
    const testUser = {
      name: 'Test User',
      email: 'test@sentinel.com',
      password: 'test123',
    }
    
    console.log('\n1️⃣  Connecting to MongoDB...')
    await client.connect()
    console.log('✅ Connected')
    
    const db = client.db(dbName)
    const usersCollection = db.collection('users')
    
    // Check if test user already exists
    console.log('\n2️⃣  Checking if test user exists...')
    const existing = await usersCollection.findOne({ email: testUser.email })
    
    if (existing) {
      console.log('⚠️  Test user already exists')
      console.log('   Email:', existing.email)
      console.log('   Name:', existing.name)
      console.log('   ID:', existing._id)
      console.log('\n   Deleting old test user...')
      await usersCollection.deleteOne({ _id: existing._id })
      console.log('✅ Old test user deleted')
    } else {
      console.log('✅ No existing test user found')
    }
    
    // Create new test user
    console.log('\n3️⃣  Creating new test user...')
    console.log('   Name:', testUser.name)
    console.log('   Email:', testUser.email)
    console.log('   Password:', testUser.password)
    
    // Hash password
    console.log('\n4️⃣  Hashing password...')
    const hashedPassword = await bcrypt.hash(testUser.password, 10)
    console.log('✅ Password hashed')
    console.log('   Hash:', hashedPassword.substring(0, 20) + '...')
    
    // Insert user
    console.log('\n5️⃣  Inserting user into MongoDB...')
    const result = await usersCollection.insertOne({
      name: testUser.name,
      email: testUser.email,
      password: hashedPassword,
      createdAt: new Date(),
    })
    console.log('✅ User inserted successfully!')
    console.log('   User ID:', result.insertedId)
    
    // Verify insertion
    console.log('\n6️⃣  Verifying user was saved...')
    const savedUser = await usersCollection.findOne({ _id: result.insertedId })
    
    if (savedUser) {
      console.log('✅ User found in database!')
      console.log('   ID:', savedUser._id)
      console.log('   Name:', savedUser.name)
      console.log('   Email:', savedUser.email)
      console.log('   Password Hash:', savedUser.password.substring(0, 20) + '...')
      console.log('   Created:', savedUser.createdAt)
      
      // Test password verification
      console.log('\n7️⃣  Testing password verification...')
      const isValid = await bcrypt.compare(testUser.password, savedUser.password)
      
      if (isValid) {
        console.log('✅ Password verification works!')
      } else {
        console.log('❌ Password verification failed!')
      }
      
      console.log('\n' + '=' .repeat(60))
      console.log('✅ SUCCESS! MongoDB is saving users correctly!')
      console.log('\n📝 Test credentials:')
      console.log('   Email:', testUser.email)
      console.log('   Password:', testUser.password)
      console.log('\nYou can now login with these credentials.')
      
    } else {
      console.log('❌ User not found after insertion!')
      console.log('This should not happen. Check database permissions.')
    }
    
  } catch (error) {
    console.error('\n❌ Error during test:', error.message)
    console.error('Full error:', error)
  } finally {
    await client.close()
    console.log('\n👋 Test completed')
  }
}

testSignup()
