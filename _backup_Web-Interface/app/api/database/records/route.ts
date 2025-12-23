import { NextRequest, NextResponse } from 'next/server'
import { latestEvents, SecurityEvent } from '@/lib/events-repo'
import { ensureMqtt } from '@/lib/mqtt-ingester'

const severityFromEvent = (event?: string) => {
  if (!event) return 'low'
  if (/(gas|fire|smoke|alert|heat)/i.test(event)) return 'high'
  if (/(intrusion|person|motion)/i.test(event)) return 'medium'
  return 'low'
}

export async function GET(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization')
    if (!auth) {
      return NextResponse.json({ message: 'Unauthorized' }, { status: 401 })
    }

    await ensureMqtt()
    const events = await latestEvents(100)

    const records = events.map((e: SecurityEvent) => ({
      id: e._id,
      timestamp: e.createdAt,
      event: e.event || e.raw?.event || 'event',
      location: e.cameraId || e.level || 'unknown',
      severity: severityFromEvent(e.event),
      snapshotUrl: e.snapshotUrl,
    }))

    return NextResponse.json(records)
  } catch (error) {
    console.error('[records] error', error)
    return NextResponse.json({ message: 'Server error' }, { status: 500 })
  }
}
