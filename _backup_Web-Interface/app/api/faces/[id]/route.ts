import { NextRequest, NextResponse } from 'next/server'
import { getCollection } from '@/lib/mongo'
import { ObjectId } from 'mongodb'

interface AuthorizedFace {
  _id?: any
  name: string
  email?: string
  faceDescriptor: number[]
  imageBase64?: string
  createdAt?: Date
  createdBy?: string
}

// DELETE - Remove authorized face
export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const { id } = params

    if (!id || !ObjectId.isValid(id)) {
      return NextResponse.json(
        { message: 'Invalid face ID' },
        { status: 400 }
      )
    }

    const facesCollection = await getCollection<AuthorizedFace>('authorized_faces')
    const result = await facesCollection.deleteOne({
      _id: new ObjectId(id),
    })

    if (result.deletedCount === 0) {
      return NextResponse.json(
        { message: 'Face not found' },
        { status: 404 }
      )
    }

    return NextResponse.json({ message: 'Face deleted successfully' })
  } catch (error) {
    console.error('Error deleting face:', error)
    return NextResponse.json(
      { message: 'Failed to delete face' },
      { status: 500 }
    )
  }
}
