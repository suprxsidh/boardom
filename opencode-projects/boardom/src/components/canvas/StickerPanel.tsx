'use client'

import { useState } from 'react'
import { Editor, createShapeId } from 'tldraw'

const EMOJI_LIST = [
  '😂', '❤️', '🔥', '👍', '👎', '😮', '😢', '🎉',
  '✨', '💡', '❓', '⭐', '🚀', '🎨', '🌈', '💀',
]

interface Props {
  editor: Editor | null
}

type Tab = 'notes' | 'emoji'

export default function StickerPanel({ editor }: Props) {
  const [tab, setTab] = useState<Tab>('notes')

  if (!editor) return null

  function placeNote() {
    const id = createShapeId()
    const { x, y } = editor!.getViewportPageBounds().center
    editor!.createShape({
      id,
      type: 'note',
      x: x - 100,
      y: y - 100,
    })
    editor!.select(id)
  }

  function placeEmoji(emoji: string) {
    const id = createShapeId()
    const { x, y } = editor!.getViewportPageBounds().center
    editor!.createShape({
      id,
      type: 'text',
      x,
      y,
      props: { text: emoji, size: 'xl', font: 'sans' },
    })
    editor!.select(id)
  }

  return (
    <aside className="flex flex-col w-16 bg-white border-l border-neutral-200 py-4 shrink-0">
      {/* Tabs */}
      <div className="flex border-b border-neutral-200 mb-3">
        <TabButton active={tab === 'notes'} onClick={() => setTab('notes')} title="Notes">
          📝
        </TabButton>
        <TabButton active={tab === 'emoji'} onClick={() => setTab('emoji')} title="Emoji">
          😊
        </TabButton>
      </div>

      {tab === 'notes' && (
        <div className="flex flex-col items-center gap-2 px-1">
          <button
            onClick={placeNote}
            className="w-12 h-12 bg-yellow-200 rounded-md text-xs text-neutral-600 hover:bg-yellow-300 transition-colors flex items-center justify-center"
            title="Add sticky note"
          >
            +
          </button>
        </div>
      )}

      {tab === 'emoji' && (
        <div className="flex flex-col items-center gap-1 px-1 overflow-y-auto">
          {EMOJI_LIST.map((emoji) => (
            <button
              key={emoji}
              onClick={() => placeEmoji(emoji)}
              className="w-9 h-9 text-xl hover:bg-neutral-100 rounded-md transition-colors"
              title={emoji}
            >
              {emoji}
            </button>
          ))}
        </div>
      )}
    </aside>
  )
}

function TabButton({ active, onClick, title, children }: {
  active: boolean
  onClick: () => void
  title: string
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`flex-1 py-1 text-base transition-colors ${
        active ? 'border-b-2 border-neutral-800' : 'text-neutral-400 hover:text-neutral-600'
      }`}
    >
      {children}
    </button>
  )
}
