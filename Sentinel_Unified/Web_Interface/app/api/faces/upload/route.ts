import { NextRequest, NextResponse } from 'next/server'

/**
 * POST - Upload a new face image to MongoDB via Python Flask API
 * 
 * This endpoint proxies the upload request to the Door Sentry service which:
 * 1. Validates and processes the image
 * 2. Extracts face embeddings using InsightFace
 * 3. Stores the face data in MongoDB
 * 4. Broadcasts RELOAD_FACES command to all services via MQTT
 */
export async function POST(request: NextRequest) {
  try {
    // Parse the FormData from the incoming request
    const formData = await request.formData()
    const name = formData.get('name') as string
    const file = formData.get('file') as File

    // Validate inputs
    if (!name || !file) {
      return NextResponse.json(
        { success: false, message: 'Missing required fields: name and file' },
        { status: 400 }
      )
    }

    // Validate file type
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png']
    if (!validTypes.includes(file.type)) {
      return NextResponse.json(
        { success: false, message: 'Invalid file type. Only JPG and PNG images are allowed.' },
        { status: 400 }
      )
    }

    // Validate file size (max 10MB to match Python API limit)
    const maxSize = 10 * 1024 * 1024 // 10MB in bytes
    if (file.size > maxSize) {
      return NextResponse.json(
        { success: false, message: 'File too large. Maximum size is 10MB.' },
        { status: 400 }
      )
    }

    // Prepare FormData to forward to Python service
    // The Python API expects 'image' field name, not 'file'
    const pythonFormData = new FormData()
    pythonFormData.append('name', name)
    pythonFormData.append('image', file)

    // Forward the request to the Python Door Sentry service
    const pythonServiceUrl = process.env.DOOR_SENTRY_URL || 'http://127.0.0.1:5001'
    const pythonEndpoint = `${pythonServiceUrl}/api/faces/register`

    console.log(`[Face Upload] Forwarding request to Python service: ${pythonEndpoint}`)
    console.log(`[Face Upload] Name: ${name}, File size: ${file.size} bytes`)

    try {
      const response = await fetch(pythonEndpoint, {
        method: 'POST',
        body: pythonFormData,
      })

      const responseData = await response.json()

      if (response.ok) {
        console.log(`[Face Upload] Success: ${responseData.message}`)
        return NextResponse.json({
          success: true,
          message: 'Face registered in MongoDB',
          name: name
        })
      } else {
        console.error(`[Face Upload] Python service error: ${responseData.error}`)
        return NextResponse.json(
          { 
            success: false, 
            message: responseData.error || 'Failed to register face'
          },
          { status: response.status }
        )
      }
    } catch (fetchError) {
      console.error('[Face Upload] Failed to connect to Door Sentry service:', fetchError)
      return NextResponse.json(
        { 
          success: false, 
          message: 'Door Sentry service unreachable. Please ensure the service is running.' 
        },
        { status: 503 }
      )
    }

  } catch (error) {
    console.error('[Face Upload] Error:', error)
    const err = error as Error
    return NextResponse.json(
      { 
        success: false, 
        message: `Failed to upload face: ${err.message || 'Unknown error'}` 
      },
      { status: 500 }
    )
  }
}
