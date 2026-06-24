'use client'

import { useCallback, useEffect, useRef } from 'react'
import SimplePeer from 'simple-peer'

interface UsePeerConnectionOptions {
  isInitiator: boolean
  onSignal: (signal: SimplePeer.SignalData) => void
  onConnect: () => void
  onData: (data: string) => void
  onClose: () => void
}

export function usePeerConnection({
  isInitiator,
  onSignal,
  onConnect,
  onData,
  onClose,
}: UsePeerConnectionOptions) {
  const peerRef = useRef<SimplePeer.Instance | null>(null)

  useEffect(() => {
    const peer = new SimplePeer({ initiator: isInitiator, trickle: true })

    peer.on('signal', onSignal)
    peer.on('connect', onConnect)
    peer.on('data', (buf) => onData(buf.toString()))
    peer.on('close', onClose)
    peer.on('error', onClose)

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

  return { receiveSignal, sendData }
}
