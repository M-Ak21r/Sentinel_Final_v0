import { NextRequest, NextResponse } from 'next/server'
import { promises as fs } from 'fs'
import path from 'path'
import { publishCommand } from '@/lib/mqtt-publisher'

/**
 * POST - Upload a new face image to the authorized faces directory
 * 
 * This endpoint handles multipart/form-data uploads and:
 * 1. Saves the image to the file system
 * 2. Sends an MQTT command to reload faces in Python services
 */
export async function POST(request: NextRequest) {
  try {
    // Parse the FormData
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

    // Sanitize the name
    let sanitizedName = name.trim()
    // Replace spaces with underscores
    sanitizedName = sanitizedName.replace(/\s+/g, '_')
    // Remove any non-alphanumeric characters (keep underscores and hyphens)
    sanitizedName = sanitizedName.replace(/[^a-zA-Z0-9_-]/g, '')

    if (!sanitizedName) {
      return NextResponse.json(
        { success: false, message: 'Invalid name after sanitization' },
        { status: 400 }
      )
    }

    // Resolve the Shared Data path relative to process.cwd()
    // From Web_Interface root, go up two levels to Sentinel_Unified, then to Shared/data/authorized_faces
    const sharedDataPath = path.join(
      process.cwd(),
      '..',
      '..',
      'Shared',
      'data',
      'authorized_faces',
      sanitizedName
    )

    // Create the directory if it doesn't exist
    await fs.mkdir(sharedDataPath, { recursive: true })

    // Convert the Blob/File to a Buffer
    const arrayBuffer = await file.arrayBuffer()
    const buffer = Buffer.from(arrayBuffer)

    // Save the file as reference.jpg
    const filePath = path.join(sharedDataPath, 'reference.jpg')
    await fs.writeFile(filePath, buffer)

    console.log(`[Face Upload] Saved face image for ${sanitizedName} at ${filePath}`)

    // System Sync - Publish MQTT command to reload faces
    try {
      await publishCommand('sentinel/commands', {
        target: 'all',
        action: 'RELOAD_FACES'
      })
      console.log('[Face Upload] MQTT command published: RELOAD_FACES')
    } catch (mqttError) {
      console.error('[Face Upload] Failed to publish MQTT command:', mqttError)
      // Continue anyway - the file is saved, manual restart will work
    }

    return NextResponse.json({
      success: true,
      message: 'Face registered & System updated',
      name: sanitizedName
    })

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
