import mqtt, { MqttClient } from 'mqtt'
import { saveEvent } from './events-repo'
import { emitEvent } from './event-bus'

let client: MqttClient | null = null
let started = false

const TOPICS = [
  'security/level1/haarcascade/events',
  'security/level1/haarcascade/frames',
  'security/level2/yolo/events',
  'security/level2/yolo/frames',
  'security/level3/sensors',
  'security/level3/alerts',
]

function deriveLevel(topic: string): 'level1' | 'level2' | 'level3' | undefined {
  if (topic.includes('level1')) return 'level1'
  if (topic.includes('level2')) return 'level2'
  if (topic.includes('level3')) return 'level3'
  return undefined
}

export async function ensureMqtt() {
  if (started) return client
  const url = process.env.MQTT_URL || ''
  if (!url) {
    console.warn('[mqtt] MQTT_URL not set; ingestion disabled')
    return null
  }

  client = mqtt.connect(url, {
    username: process.env.MQTT_USERNAME,
    password: process.env.MQTT_PASSWORD,
  })

  client.on('connect', () => {
    client?.subscribe(TOPICS, { qos: 1 }, (err: any) => {
      if (err) console.error('[mqtt] subscribe error', err)
    })
    console.log('[mqtt] connected and subscribed')
  })

  client.on('error', (err: any) => {
    console.error('[mqtt] error', err)
  })

  client.on('message', async (topic: string, payload: Buffer) => {
    try {
      const parsed = JSON.parse(payload.toString())
      const doc = {
        topic,
        level: deriveLevel(topic),
        cameraId: parsed.cameraId,
        model: parsed.model,
        event: parsed.event || parsed.type,
        confidence: parsed.confidence,
        snapshotUrl: parsed.frameUrl || parsed.snapshotUrl,
        status: parsed.status,
        raw: parsed,
        createdAt: parsed.timestamp ? new Date(parsed.timestamp) : new Date(),
      }
      await saveEvent(doc)
      emitEvent(doc)
    } catch (err) {
      console.error('[mqtt] message handling error', err)
    }
  })

  started = true
  return client
}
