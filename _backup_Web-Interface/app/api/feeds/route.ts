import { NextRequest, NextResponse } from 'next/server'
import { latestByCamera } from '@/lib/events-repo'
import { ensureMqtt } from '@/lib/mqtt-ingester'

export async function GET(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization')
    if (!auth) {
      return NextResponse.json({ message: 'Unauthorized' }, { status: 401 })
    }

    await ensureMqtt()
    const docs = await latestByCamera()

    const feeds = docs.map((d: any) => {
      const minutesAgo = Math.round((Date.now() - d.createdAt.getTime()) / 60000)
      return {
        id: d.cameraId || d._id || 'unknown',
        name: d.cameraId || 'Camera',
        status: minutesAgo <= 5 ? 'online' : 'offline',
        lastUpdate: minutesAgo === 0 ? 'now' : `${minutesAgo}m ago`,
        snapshotUrl: d.snapshotUrl,
        event: d.event,
        model: d.model,
      }
    })

    return NextResponse.json(feeds)
  } catch (error) {
    console.error('[feeds] error', error)
    return NextResponse.json({ message: 'Server error' }, { status: 500 })
  }
}
