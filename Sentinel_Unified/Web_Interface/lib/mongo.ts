import { MongoClient, Db, Collection } from 'mongodb'

let client: MongoClient | null = null
let db: Db | null = null

const dbName = process.env.MONGODB_DB || 'security_dashboard'

export async function getDb(): Promise<Db> {
  if (db) return db
  const uri = process.env.MONGODB_URI
  if (!uri) {
    throw new Error('MONGODB_URI is not set')
  }
  try {
    client = new MongoClient(uri, {
      retryWrites: true,
      w: 'majority',
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000, // Fail faster for debugging
    })
    console.log('Attempting to connect to MongoDB...')
    await client.connect()
    console.log('MongoDB connected successfully!')
    db = client.db(dbName)
    return db
  } catch (error) {
    console.error('MongoDB connection failed:', error)
    throw new Error(`MongoDB connection error: ${error instanceof Error ? error.message : 'Unknown error'}`)
  }
}

export async function getCollection<T = any>(name: string): Promise<Collection<T>> {
  const database = await getDb()
  return database.collection<T>(name)
}

export async function closeDb() {
  if (client) {
    await client.close()
    client = null
    db = null
  }
}
