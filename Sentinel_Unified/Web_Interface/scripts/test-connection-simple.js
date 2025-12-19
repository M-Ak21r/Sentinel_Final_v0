/**
 * Simple MongoDB Connection Test (with SSL workaround)
 * Run with: node scripts/test-connection-simple.js
 */

require('dotenv').config({ path: '.env.local' })
const { MongoClient } = require('mongodb')

async function testConnection() {
  const uri = process.env.MONGODB_URI
  
  console.log('🔗 Testing MongoDB Connection...\n')
  console.log('URI:', uri?.substring(0, 30) + '...')
  
  if (!uri) {
    console.error('❌ MONGODB_URI not found in .env.local')
    return
  }
  
  // Try with relaxed TLS settings
  const client = new MongoClient(uri, {
    serverSelectionTimeoutMS: 10000,
    tls: true,
    tlsAllowInvalidCertificates: true,
    tlsAllowInvalidHostnames: true,
  })
  
  try {
    console.log('Attempting connection...\n')
    await client.connect()
    console.log('✅ SUCCESS! Connected to MongoDB Atlas!\n')
    
    // Test database access
    const db = client.db('security_dashboard')
    await db.command({ ping: 1 })
    console.log('✅ Database is accessible!\n')
    
    // List collections
    const collections = await db.listCollections().toArray()
    console.log(`Found ${collections.length} collections:`)
    collections.forEach(col => console.log(`  - ${col.name}`))
    
    // Check users
    const usersCount = await db.collection('users').countDocuments()
    console.log(`\n👥 Users in database: ${usersCount}`)
    
    if (usersCount === 0) {
      console.log('\n⚠️  No users found! Run: node scripts/create-admin-user.js')
    } else {
      console.log('✅ You can login with your registered users')
    }
    
  } catch (error) {
    console.log('❌ CONNECTION FAILED!\n')
    console.log('Error:', error.message)
    console.log('\n📋 Common Solutions:\n')
    console.log('1️⃣  MongoDB Atlas → Network Access → Allow 0.0.0.0/0')
    console.log('   (Wait 2-3 minutes after adding)')
    console.log('\n2️⃣  MongoDB Atlas → Database Access → Check password')
    console.log('   Current password in .env.local: Sentinel_V03')
    console.log('\n3️⃣  MongoDB Atlas → Clusters → Verify cluster is RUNNING')
    console.log('\n4️⃣  Check your internet connection')
    
  } finally {
    await client.close()
  }
}

testConnection()
