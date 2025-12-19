import { NextRequest } from 'next/server'
import { onEvent } from '@/lib/event-bus'
import { ensureMqtt } from '@/lib/mqtt-ingester'

export const runtime = 'nodejs'

export async function GET(_req: NextRequest) {
  await ensureMqtt()

  const stream = new ReadableStream({
    start(controller) {
      const send = (data: any) => {
        controller.enqueue(`data: ${JSON.stringify(data)}\n\n`)
      }

      const off = onEvent(send)

      controller.enqueue(': connected\n\n')

      const keepAlive = setInterval(() => {
        controller.enqueue(': keep-alive\n\n')
      }, 15000)

      controller.close = controller.close.bind(controller)

      return () => {
        clearInterval(keepAlive)
        off()
      }
    },
    cancel(reason) {
      console.log('[sse] stream cancelled', reason)
    },
  })

  return new Response(stream, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'Access-Control-Allow-Origin': '*',
    },
  })
}
