import mqtt from 'mqtt'

/**
 * Publishes a command to the MQTT broker
 * @param topic - The MQTT topic to publish to
 * @param payload - The payload object to send (will be JSON stringified)
 * @returns Promise that resolves when the message is published
 */
export async function publishCommand(
  topic: string,
  payload: object
): Promise<void> {
  return new Promise((resolve, reject) => {
    const brokerUrl = process.env.MQTT_BROKER_URL || 'mqtt://localhost:1883'
    
    try {
      // Connect to MQTT broker
      const client = mqtt.connect(brokerUrl, {
        connectTimeout: 5000,
        reconnectPeriod: 0, // Disable auto-reconnect for stateless operation
      })

      // Handle connection errors
      client.on('error', (error) => {
        console.error('MQTT connection error:', error)
        client.end(true) // Force close
        reject(new Error(`MQTT connection failed: ${error.message}`))
      })

      // Handle successful connection
      client.on('connect', () => {
        console.log(`Connected to MQTT broker at ${brokerUrl}`)
        
        // Publish the message
        const message = JSON.stringify(payload)
        client.publish(topic, message, { qos: 1 }, (error) => {
          if (error) {
            console.error('MQTT publish error:', error)
            client.end(true)
            reject(new Error(`Failed to publish message: ${error.message}`))
          } else {
            console.log(`Published to ${topic}:`, message)
            // Disconnect after successful publish
            client.end(false, () => {
              resolve()
            })
          }
        })
      })

      // Handle timeout - if not connected within 6 seconds, reject
      setTimeout(() => {
        if (!client.connected) {
          client.end(true)
          reject(new Error('MQTT connection timeout'))
        }
      }, 6000)
    } catch (error) {
      reject(new Error(`MQTT setup failed: ${error}`))
    }
  })
}
