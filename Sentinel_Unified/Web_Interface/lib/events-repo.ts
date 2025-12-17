import { getCollection } from './mongo'

export type SecurityEvent = {
  _id?: string
  topic: string
  level?: 'level1' | 'level2' | 'level3'
  cameraId?: string
  model?: string
  event?: string
  confidence?: number
  snapshotUrl?: string
  status?: string
  raw?: any
  createdAt: Date
}

const COLLECTION = 'events'

export async function saveEvent(evt: Omit<SecurityEvent, '_id'>) {
  const col = await getCollection<SecurityEvent>(COLLECTION)
  await col.insertOne(evt)
}

export async function latestEvents(limit = 50) {
  const col = await getCollection<SecurityEvent>(COLLECTION)
  return col.find({}).sort({ createdAt: -1 }).limit(limit).toArray()
}

export async function stats24h() {
  const col = await getCollection<SecurityEvent>(COLLECTION)
  const since = new Date(Date.now() - 24 * 60 * 60 * 1000)
  const events24h = await col.countDocuments({ createdAt: { $gte: since } })
  const recentWindow = new Date(Date.now() - 5 * 60 * 1000)
  const onlineCameras = await col.distinct('cameraId', { createdAt: { $gte: recentWindow } })
  const cameras = await col.distinct('cameraId', {})

  // crude critical count: anything with event containing alert/gas/heat/fire
  const criticalAlerts = await col.countDocuments({
    event: { $regex: /(alert|gas|heat|fire|smoke)/i },
    createdAt: { $gte: since },
  })

  return {
    totalCameras: cameras.filter(Boolean).length,
    onlineFeeds: onlineCameras.filter(Boolean).length,
    events24h,
    criticalAlerts,
  }
}

export async function latestByCamera() {
  const col = await getCollection<SecurityEvent>(COLLECTION)
  const pipeline = [
    { $sort: { createdAt: -1 } },
    {
      $group: {
        _id: '$cameraId',
        doc: { $first: '$$ROOT' },
      },
    },
    { $replaceRoot: { newRoot: '$doc' } },
  ]
  return col.aggregate<SecurityEvent>(pipeline).toArray()
}
