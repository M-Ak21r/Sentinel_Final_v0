import { EventEmitter } from 'events'

const bus = new EventEmitter()
bus.setMaxListeners(50)

export function emitEvent(event: any) {
  bus.emit('event', event)
}

export function onEvent(handler: (event: any) => void) {
  bus.on('event', handler)
  return () => bus.off('event', handler)
}
