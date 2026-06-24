'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import SimplePeer from 'simple-peer'

interface UsePeerConnectionOptions {
  isInitiator: boolean
  onSignal: (signal: SimplePeer.SignalData) => void
  onConnect: () => void
  onData: (data: string) => void
  onClose: () => void
  onError?: (err: Error) => void
}

export function usePeerConnection({
  isInitiator,
  onSignal,
  onConnect,
  onData,
  onClose,
  onError,
}: UsePeerConnectionOptions) {
  const peerRef = useRef<SimplePeer.Instance | null>(null)
  const [connected, setConnected] = useState(false)

  const onSignalRef = useRef(onSignal)
  const onConnectRef = useRef(onConnect)
  const onDataRef = useRef(onData)
  const onCloseRef = useRef(onClose)
  const onErrorRef = useRef(onError)

  useEffect(() => { onSignalRef.current = onSignal }, [onSignal])
  useEffect(() => { onConnectRef.current = onConnect }, [onConnect])
  useEffect(() => { onDataRef.current = onData }, [onData])
  useEffect(() => { onCloseRef.current = onClose }, [onClose])
  useEffect(() => { onErrorRef.current = onError }, [onError])

  useEffect(() => {
    const peer = new SimplePeer({ initiator: isInitiator, trickle: true })

    peer.on('signal', (signal) => onSignalRef.current(signal))
    peer.on('connect', () => {
      setConnected(true)
      onConnectRef.current()
    })
    peer.on('data', (buf) => onDataRef.current(buf.toString()))
    peer.on('close', () => {
      setConnected(false)
      onCloseRef.current()
    })
    peer.on('error', (err) => onErrorRef.current?.(err))

    peerRef.current = peer

    return () => {
      peer.destroy()
      peerRef.current = null
    }
  }, [isInitiator]) // eslint-disable-line react-hooks/exhaustive-deps

  const receiveSignal = useCallback((signal: SimplePeer.SignalData) => {
    peerRef.current?.signal(signal)
  }, [])

  const sendData = useCallback((data: string) => {
    if (peerRef.current?.connected) {
      peerRef.current.send(data)
    }
  }, [])

  const destroy = useCallback(() => {
    peerRef.current?.destroy()
  }, [])

  return { receiveSignal, sendData, connected, destroy }
}
