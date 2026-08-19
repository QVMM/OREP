import SockJS from 'sockjs-client/dist/sockjs.min.js'
import { Client } from '@stomp/stompjs'
import { getUserToken } from './authStorage'

const websocketEndpoint = import.meta.env.VITE_WEBSOCKET_ENDPOINT
  || (import.meta.env.DEV ? '/ws' : '/ws-stomp')

// WebSocket 客户端工具类
export class WebSocketClient {
  constructor() {
    this.client = null
    this.connected = false
    this.subscriptions = new Map()
    this.connectedListeners = new Set()
    this.errorListeners = new Set()
    this.nextSubscriberId = 1
  }

  // 连接 WebSocket
  connect(onConnected, onError) {
    if (onConnected) this.connectedListeners.add(onConnected)
    if (onError) this.errorListeners.add(onError)

    const removeListeners = () => {
      if (onConnected) this.connectedListeners.delete(onConnected)
      if (onError) this.errorListeners.delete(onError)
    }

    if (this.connected) {
      onConnected?.()
      return removeListeners
    }

    if (this.client?.active) return removeListeners

    const token = getUserToken()

    this.client = new Client({
      // 使用 SockJS 作为 WebSocket 传输层
      webSocketFactory: () => {
        return new SockJS(websocketEndpoint)
      },
      // 连接头信息，携带 token
      connectHeaders: {
        Authorization: `Bearer ${token}`
      },
      // 心跳间隔（毫秒）
      heartbeatIncoming: 4000,
      heartbeatOutgoing: 4000,
      // 重连延迟（毫秒）
      reconnectDelay: 5000,
      // 连接成功回调
      onConnect: () => {
        this.connected = true
        this.subscriptions.forEach((entry, destination) => {
          this.activateSubscription(destination, entry)
        })
        this.connectedListeners.forEach(listener => listener())
      },
      // 连接错误回调
      onStompError: (frame) => {
        console.error('WebSocket 错误:', frame)
        this.errorListeners.forEach(listener => listener(frame))
      },
      // 断开连接回调
      onDisconnect: () => {
        this.connected = false
        this.clearActiveSubscriptions()
      },
      onWebSocketClose: () => {
        this.connected = false
        this.clearActiveSubscriptions()
      }
    })

    this.client.activate()
    return removeListeners
  }

  // 订阅消息
  subscribe(destination, callback) {
    if (typeof callback !== 'function') throw new TypeError('订阅回调必须是函数')
    const subscriberId = `ws-${this.nextSubscriberId++}`
    const token = { destination, subscriberId }
    let entry = this.subscriptions.get(destination)
    if (!entry) {
      entry = {
        callbacks: new Map(),
        activeSubscription: null
      }
      this.subscriptions.set(destination, entry)
    }
    entry.callbacks.set(subscriberId, callback)

    if (this.connected) this.activateSubscription(destination, entry)
    return token
  }

  activateSubscription(destination, entry) {
    if (!this.client || !this.connected || entry.activeSubscription) return
    entry.activeSubscription = this.client.subscribe(destination, (message) => {
      let data
      try {
        data = JSON.parse(message.body)
      } catch (e) {
        data = message.body
      }
      entry.callbacks.forEach((callback) => callback(data))
    })
  }

  // 发送消息
  send(destination, body) {
    if (!this.client || !this.connected) {
      console.warn('WebSocket 未连接，无法发送消息')
      return
    }

    this.client.publish({
      destination,
      body: typeof body === 'string' ? body : JSON.stringify(body)
    })
  }

  // 取消订阅
  unsubscribe(token) {
    if (!token) return
    const destination = typeof token === 'string' ? token : token.destination
    const subscriberId = typeof token === 'string' ? null : token.subscriberId
    const entry = this.subscriptions.get(destination)
    if (!entry) return

    if (subscriberId) entry.callbacks.delete(subscriberId)
    else entry.callbacks.clear()

    if (entry.callbacks.size === 0) {
      entry.activeSubscription?.unsubscribe()
      this.subscriptions.delete(destination)
    }
  }

  clearActiveSubscriptions() {
    this.subscriptions.forEach((entry) => {
      entry.activeSubscription = null
    })
  }

  // 断开连接
  disconnect() {
    if (this.client) {
      // 取消所有订阅
      this.subscriptions.forEach((entry) => entry.activeSubscription?.unsubscribe())
      this.subscriptions.clear()
      // 断开连接
      this.client.deactivate()
      this.client = null
      this.connected = false
    }
  }

  // 检查连接状态
  isConnected() {
    return this.connected
  }
}

// 导出单例
export default new WebSocketClient()
