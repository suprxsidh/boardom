'use client'

import { useCallback, useEffect, useRef } from 'react'
import {
  Editor,
  TLRecord,
  TLStoreEventInfo,
  InstancePresenceRecordType,
  TLInstancePresence,
} from 'tldraw'

type CanvasMessage =
  | { type: 'store-change'; added: TLRecord[]; updated: TLRecord[]; removed: string[] }
  | { type: 'cursor'; x: number; y: number }

interface UseCanvasSyncOptions {
  editor: Editor | null
  sendData: (data: string) => void
  remoteUserId: string
}

export function useCanvasSync({ editor, sendData, remoteUserId }: UseCanvasSyncOptions) {
  const editorRef = useRef(editor)
  editorRef.current = editor

  // Broadcast document changes
  useEffect(() => {
    if (!editor) return

    return editor.store.listen(
      ({ changes }: TLStoreEventInfo) => {
        const { added, updated, removed } = changes
        const msg: CanvasMessage = {
          type: 'store-change',
          added: Object.values(added) as TLRecord[],
          updated: Object.values(updated).map(([, next]) => next) as TLRecord[],
          removed: Object.keys(removed),
        }

        if (msg.added.length || msg.updated.length || msg.removed.length) {
          sendData(JSON.stringify(msg))
        }
      },
      { source: 'user', scope: 'document' }
    )
  }, [editor, sendData])

  // Broadcast cursor position
  useEffect(() => {
    if (!editor) return

    const onMove = () => {
      const { x, y } = editor.inputs.currentPagePoint
      sendData(JSON.stringify({ type: 'cursor', x, y } satisfies CanvasMessage))
    }

    window.addEventListener('pointermove', onMove)
    return () => window.removeEventListener('pointermove', onMove)
  }, [editor, sendData])

  const applyRemoteData = useCallback((data: string) => {
    const editor = editorRef.current
    if (!editor) return

    const msg: CanvasMessage = JSON.parse(data)

    if (msg.type === 'store-change') {
      editor.store.mergeRemoteChanges(() => {
        if (msg.added.length) editor.store.put(msg.added)
        if (msg.updated.length) editor.store.put(msg.updated)
        if (msg.removed.length) editor.store.remove(msg.removed)
      })
    } else if (msg.type === 'cursor') {
      const presence: TLInstancePresence = InstancePresenceRecordType.create({
        id: InstancePresenceRecordType.createId(remoteUserId),
        currentPageId: editor.getCurrentPageId(),
        userId: remoteUserId,
        userName: '',
        cursor: { x: msg.x, y: msg.y, type: 'default', rotation: 0 },
        color: '#ff4444',
        chatMessage: '',
        lastActivityTimestamp: Date.now(),
        followingUserId: null,
        screenBounds: { x: 0, y: 0, w: 0, h: 0 },
        selectedShapeIds: [],
        trackingNumber: 0,
      })

      editor.store.mergeRemoteChanges(() => {
        editor.store.put([presence])
      })
    }
  }, [remoteUserId])

  return { applyRemoteData }
}
