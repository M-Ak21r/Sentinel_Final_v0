/**
 * MongoDB Connection Test Script
 * Run with: node scripts/test-mongodb-connection.js
 * 
 * This script will:
 * 1. Test connection to MongoDB Atlas
 * 2. List all databases
 * 3. Check if security_dashboard database exists
 * 4. List all collections in the database
 * 5. Count documents in users collection
 */

require('dotenv').config({ path: '.env.local' })
const { MongoClient } = require('mongodb')

async function testConnection() {
  console.log('🔍 MongoDB Connection Test')
  console.log('=' .repeat(60))
  
  // Check environment variables
  console.log('\n1️⃣  Checking Environment Variables...')
  const uri = process.env.MONGODB_URI
  const dbName = process.env.MONGODB_DB || 'security_dashboard'
  
  if (!uri) {
    console.error('❌ MONGODB_URI not found in .env.local')
    console.log('Please make sure .env.local exists and contains MONGODB_URI')
    return
  }
  
  console.log('✅ MONGODB_URI found')
  console.log('   URI:', uri.substring(0, 30) + '...' + uri.substring(uri.length - 20))
  console.log('✅ Database name:', dbName)
  
  const client = new MongoClient(uri, {
    serverSelectionTimeoutMS: 5000,
  })
  
  try {
    console.log('\n2️⃣  Connecting to MongoDB Atlas...')
    await client.connect()
    console.log('✅ Successfully connected to MongoDB!')
    
    // Test ping
    console.log('\n3️⃣  Testing connection with ping...')
    await client.db('admin').command({ ping: 1 })
    console.log('✅ Ping successful!')
    
    // List databases
    console.log('\n4️⃣  Listing all databases...')
    const adminDb = client.db().admin()
    const databasesList = await adminDb.listDatabases()
    console.log('   Databases found:', databasesList.databases.length)
    databasesList.databases.forEach(db => {
      const marker = db.name === dbName ? '👉' : '  '
      console.log(`   ${marker} ${db.name} (${(db.sizeOnDisk / 1024).toFixed(2)} KB)`)
    })
    
    // Check target database
    console.log(`\n5️⃣  Checking database "${dbName}"...`)
    const db = client.db(dbName)
    const collections = await db.listCollections().toArray()
    
    if (collections.length === 0) {
      console.log('⚠️  Database exists but has no collections yet')
      console.log('   This is normal for a new database')
    } else {
      console.log(`✅ Found ${collections.length} collection(s):`)
      for (const collection of collections) {
        console.log(`   - ${collection.name}`)
        
        // Count documents
        const count = await db.collection(collection.name).countDocuments()
        console.log(`     Documents: ${count}`)
      }
    }
    
    // Check users collection specifically
    console.log('\n6️⃣  Checking "users" collection...')
    const usersCollection = db.collection('users')
    const userCount = await usersCollection.countDocuments()
    
    if (userCount === 0) {
      console.log('⚠️  Users collection is empty')
      console.log('   You need to create your first user!')
      console.log('   Run: node scripts/create-admin-user.js')
    } else {
      console.log(`✅ Found ${userCount} user(s) in database`)
      
      // List users (without passwords)
      const users = await usersCollection.find({}, { 
        projection: { password: 0 } 
      }).toArray()
      
      console.log('\n   Registered users:')
      users.forEach((user, index) => {
        console.log(`   ${index + 1}. ${user.name} (${user.email})`)
        console.log(`      ID: ${user._id}`)
        console.log(`      Created: ${user.createdAt}`)
      })
    }
    
    console.log('\n' + '=' .repeat(60))
    console.log('✅ MongoDB is properly configured!')
    
    if (userCount === 0) {
      console.log('\n⚠️  NEXT STEP: Create your first user')
      console.log('   Run: node scripts/create-admin-user.js')
    } else {
      console.log('\n✅ You can now login with your registered users')
    }
    
  } catch (error) {
    console.log('\n' + '=' .repeat(60))
    console.error('❌ Connection failed!')
    console.error('\nError details:')
    console.error('Type:', error.name)
    console.error('Message:', error.message)
    
    if (error.message.includes('ENOTFOUND')) {
      console.log('\n💡 Troubleshooting:')
      console.log('   - Check your internet connection')
      console.log('   - Verify the MongoDB Atlas cluster is running')
      console.log('   - Check if the hostname in MONGODB_URI is correct')
    } else if (error.message.includes('authentication')) {
      console.log('\n💡 Troubleshooting:')
      console.log('   - Check your MongoDB username and password')
      console.log('   - Verify the user has correct permissions')
      console.log('   - Make sure the password doesn\'t have special characters that need encoding')
    } else if (error.message.includes('timeout')) {
      console.log('\n💡 Troubleshooting:')
      console.log('   - Check your firewall settings')
      console.log('   - Verify MongoDB Atlas IP whitelist (0.0.0.0/0 allows all)')
      console.log('   - Try increasing the timeout')
    }
    
  } finally {
    await client.close()
    console.log('\n👋 Connection closed')
  }
}

testConnection()
