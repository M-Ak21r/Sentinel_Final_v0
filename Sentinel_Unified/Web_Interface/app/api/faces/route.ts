import { NextRequest, NextResponse } from 'next/server'
import { getCollection } from '@/lib/mongo'
import { ObjectId } from 'mongodb'

interface AuthorizedFace {
  _id?: any
  name: string
  email?: string
  faceDescriptor: number[] // Array of 128 values from face-api
  imageBase64?: string // Base64 encoded face image for preview
  createdAt?: Date
  createdBy?: string // User ID who added this face
}

// GET - Fetch all authorized faces
export async function GET(request: NextRequest) {
  try {
    const facesCollection = await getCollection<AuthorizedFace>('authorized_faces')
    const faces = await facesCollection.find({}).toArray()
    
    return NextResponse.json({
      faces: faces.map(face => ({
        id: face._id?.toString(),
        name: face.name,
        email: face.email,
        createdAt: face.createdAt,
        imagePreview: face.imageBase64 ? `data:image/png;base64,${face.imageBase64}` : null,
      })),
    })
  } catch (error) {
    console.error('Error fetching faces:', error)
    return NextResponse.json(
      { message: 'Failed to fetch faces' },
      { status: 500 }
    )
  }
}

// POST - Add new authorized face
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { name, email, faceDescriptor, imageBase64 } = body

    if (!name || !faceDescriptor || !Array.isArray(faceDescriptor)) {
      return NextResponse.json(
        { message: 'Missing or invalid required fields: name, faceDescriptor' },
        { status: 400 }
      )
    }

    if (faceDescriptor.length !== 128) {
      return NextResponse.json(
        { message: 'Face descriptor must have exactly 128 values' },
        { status: 400 }
      )
    }

    const facesCollection = await getCollection<AuthorizedFace>('authorized_faces')

    const newFace: AuthorizedFace = {
      name,
      email: email || '',
      faceDescriptor,
      imageBase64: imageBase64?.substring(0, 50000), // Store first 50KB of image
      createdAt: new Date(),
      createdBy: 'system', // In production, get from auth context
    }

    const result = await facesCollection.insertOne(newFace)

    return NextResponse.json(
      {
        id: result.insertedId.toString(),
        name,
        email,
        message: 'Face registered successfully',
      },
      { status: 201 }
    )
  } catch (error) {
    const err = error as any
    console.error('Error registering face:', err?.name || 'Unknown', err?.message || err)
    return NextResponse.json(
      { message: `Failed to register face: ${err?.message || 'Unknown error'}` },
      { status: 500 }
    )
  }
}
