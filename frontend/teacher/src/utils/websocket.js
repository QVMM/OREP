import SockJS from 'sockjs-client/dist/sockjs.min.js'
import { Client } from '@stomp/stompjs'
import { getToken } from './auth'

const websocketEndpoint = import.meta.env.VITE_WEBSOCKET_ENDPOINT
  || (import.meta.env.DEV ? '/ws' : '/ws-stomp')

class TeacherWebSocketClient {
  constructor() {
    this.client = null
    this.connected = false
    this.subscriptions = new Map()
    this.listeners = new Set()
    this.nextId = 1
  }

  connect(onConnected) {
    if (onConnected) this.listeners.add(onConnected)
    const remove = () => onConnected && this.listeners.delete(onConnected)
    if (this.connected) {
      onConnected?.()
      return remove
    }
    if (this.client?.active) return remove
    this.client = new Client({
      webSocketFactory: () => new SockJS(websocketEndpoint),
      connectHeaders: { Authorization: `Bearer ${getToken()}` },
      heartbeatIncoming: 4000,
      heartbeatOutgoing: 4000,
      reconnectDelay: 5000,
      onConnect: () => {
        this.connected = true
        this.subscriptions.forEach((entry, destination) => this.activate(destination, entry))
        this.listeners.forEach(listener => listener())
      },
      onDisconnect: () => this.markDisconnected(),
      onWebSocketClose: () => this.markDisconnected(),
    })
    this.client.activate()
    return remove
  }

  subscribe(destination, callback) {
    const subscriberId = `teacher-ws-${this.nextId++}`
    let entry = this.subscriptions.get(destination)
    if (!entry) {
      entry = { callbacks: new Map(), activeSubscription: null }
      this.subscriptions.set(destination, entry)
    }
    entry.callbacks.set(subscriberId, callback)
    if (this.connected) this.activate(destination, entry)
    return { destination, subscriberId }
  }

  unsubscribe(token) {
    if (!token) return
    const entry = this.subscriptions.get(token.destination)
    if (!entry) return
    entry.callbacks.delete(token.subscriberId)
    if (entry.callbacks.size === 0) {
      entry.activeSubscription?.unsubscribe()
      this.subscriptions.delete(token.destination)
    }
  }

  activate(destination, entry) {
    if (!this.connected || entry.activeSubscription) return
    entry.activeSubscription = this.client.subscribe(destination, message => {
      let payload = message.body
      try {
        payload = JSON.parse(message.body)
      } catch {
        // 文本消息原样分发。
      }
      entry.callbacks.forEach(callback => callback(payload))
    })
  }

  markDisconnected() {
    this.connected = false
    this.subscriptions.forEach(entry => {
      entry.activeSubscription = null
    })
  }
}

export default new TeacherWebSocketClient()
