'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Tldraw, Editor } from 'tldraw'
import 'tldraw/tldraw.css'
import { getSession, clearSession } from '@/lib/session'
import { useCanvasSync } from '@/hooks/useCanvasSync'
import DrawingToolbar from './DrawingToolbar'
import StickerPanel from './StickerPanel'

export default function CanvasPage() {
  const router = useRouter()
  const [editor, setEditor] = useState<Editor | null>(null)
  const [partnerLeft, setPartnerLeft] = useState(false)

  const peer = getSession()?.peer ?? null

  const sendData = useCallback((data: string) => {
    if (peer?.connected) peer.send(data)
  }, [peer])

  const { applyRemoteData } = useCanvasSync({
    editor,
    sendData,
    remoteUserId: 'remote-peer',
  })

  const applyRemoteDataRef = useRef(applyRemoteData)
  applyRemoteDataRef.current = applyRemoteData

  useEffect(() => {
    if (!peer) {
      router.push('/')
      return
    }

    const onData = (buf: Buffer) => applyRemoteDataRef.current(buf.toString())
    const onClose = () => setPartnerLeft(true)

    peer.on('data', onData)
    peer.on('close', onClose)
    peer.on('error', onClose)

    return () => {
      peer.removeListener('data', onData)
      peer.removeListener('close', onClose)
      peer.removeListener('error', onClose)
    }
  }, [peer, router])

  if (partnerLeft) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-neutral-950 text-white">
        <p className="text-neutral-300">Your partner left.</p>
        <button
          onClick={() => { clearSession(); router.push('/') }}
          className="px-6 py-2 bg-white text-black rounded-full text-sm font-medium"
        >
          Start again
        </button>
      </main>
    )
  }

  return (
    <div className="flex h-screen w-screen bg-neutral-100 overflow-hidden">
      <DrawingToolbar editor={editor} />
      <div className="flex-1 relative">
        <Tldraw onMount={setEditor} hideUi />
        <button
          onClick={() => { clearSession(); router.push('/') }}
          className="absolute top-3 right-3 z-10 text-xs text-neutral-400 hover:text-neutral-700 transition-colors px-2 py-1"
        >
          Leave
        </button>
      </div>
      <StickerPanel editor={editor} />
    </div>
  )
}
