import { NextRequest, NextResponse } from 'next/server'
import { stats24h } from '@/lib/events-repo'
import { ensureMqtt } from '@/lib/mqtt-ingester'

export async function GET(request: NextRequest) {
  try {
    const auth = request.headers.get('authorization')
    if (!auth) {
      return NextResponse.json({ message: 'Unauthorized' }, { status: 401 })
    }

    await ensureMqtt()
    const stats = await stats24h()

    return NextResponse.json(stats)
  } catch (error) {
    console.error('[stats] error', error)
    return NextResponse.json({ message: 'Server error' }, { status: 500 })
  }
}
