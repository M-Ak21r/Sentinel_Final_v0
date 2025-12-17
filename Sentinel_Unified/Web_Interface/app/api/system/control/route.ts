import { NextRequest, NextResponse } from 'next/server'
import { publishCommand } from '@/lib/mqtt-publisher'

interface ControlRequest {
  target: 'door' | 'interior' | 'all'
  action: 'UNLOCK' | 'SILENCE'
}

export async function POST(request: NextRequest) {
  try {
    // Parse request body
    const body: ControlRequest = await request.json()
    const { target, action } = body

    // Validate request
    if (!target || !action) {
      return NextResponse.json(
        { error: 'Missing required fields: target and action' },
        { status: 400 }
      )
    }

    if (!['door', 'interior', 'all'].includes(target)) {
      return NextResponse.json(
        { error: 'Invalid target. Must be "door", "interior", or "all"' },
        { status: 400 }
      )
    }

    if (!['UNLOCK', 'SILENCE'].includes(action)) {
      return NextResponse.json(
        { error: 'Invalid action. Must be "UNLOCK" or "SILENCE"' },
        { status: 400 }
      )
    }

    // Prepare MQTT payload based on action
    let mqttPayload: { target: string; action: string }

    if (action === 'UNLOCK') {
      // UNLOCK action - target specific door
      mqttPayload = {
        target: 'door',
        action: 'UNLOCK',
      }
    } else if (action === 'SILENCE') {
      // SILENCE action - stop all alarms
      mqttPayload = {
        target: 'all',
        action: 'STOP_ALARM',
      }
    } else {
      return NextResponse.json(
        { error: 'Unsupported action' },
        { status: 400 }
      )
    }

    // Publish command to MQTT
    const topic = 'sentinel/commands'
    await publishCommand(topic, mqttPayload)

    // Return success response
    return NextResponse.json(
      {
        success: true,
        message: `Command ${action} sent successfully`,
        payload: mqttPayload,
      },
      { status: 200 }
    )
  } catch (error) {
    console.error('Error processing control command:', error)
    
    // Return error response
    return NextResponse.json(
      {
        error: 'Failed to send command',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}
