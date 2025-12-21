import { NextResponse } from 'next/server'
import { getCollection } from '@/lib/mongo'

interface SecurityEvent {
  _id?: unknown
  topic: string
  level?: string
  event?: string
  snapshotUrl?: string
  createdAt: Date
  status?: string
  confidence?: number
  cameraId?: string
}

// GET - Fetch recent security events
export async function GET() {
  try {
    const eventsCollection = await getCollection<SecurityEvent>('events')
    
    // Query events collection: sort by createdAt descending, limit to 50
    const events = await eventsCollection
      .find({})
      .sort({ createdAt: -1 })
      .limit(50)
      .toArray()
    
    return NextResponse.json({
      events: events.map(event => ({
        id: event._id?.toString(),
        topic: event.topic,
        level: event.level,
        event: event.event,
        snapshotUrl: event.snapshotUrl,
        createdAt: event.createdAt,
        status: event.status,
        confidence: event.confidence,
        cameraId: event.cameraId,
      })),
    })
  } catch (error) {
    console.error('Error fetching events:', error)
    return NextResponse.json(
      { message: 'Failed to fetch events' },
      { status: 500 }
    )
  }
}
