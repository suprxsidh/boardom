'use client'

import { Editor, DefaultColorStyle, DefaultSizeStyle } from 'tldraw'

type TldrawColor = 'black' | 'white' | 'red' | 'orange' | 'yellow' | 'green' | 'blue' | 'violet'
type TldrawSize = 's' | 'm' | 'l'

const COLORS: { token: TldrawColor; hex: string }[] = [
  { token: 'black', hex: '#1d1d1d' },
  { token: 'white', hex: '#f8f9fa' },
  { token: 'red', hex: '#e03131' },
  { token: 'orange', hex: '#f76707' },
  { token: 'yellow', hex: '#f59f00' },
  { token: 'green', hex: '#2f9e44' },
  { token: 'blue', hex: '#1971c2' },
  { token: 'violet', hex: '#7048e8' },
]

const SIZES: { token: TldrawSize; px: number }[] = [
  { token: 's', px: 4 },
  { token: 'm', px: 8 },
  { token: 'l', px: 12 },
]

interface Props {
  editor: Editor | null
}

export default function DrawingToolbar({ editor }: Props) {
  if (!editor) return null

  return (
    <aside className="flex flex-col items-center gap-3 w-14 bg-neutral-900 py-3 rounded-xl shadow-lg">
      {/* Tools */}
      <button onClick={() => editor.setCurrentTool('select')} title="Select" className="p-2 hover:bg-neutral-700 rounded-lg text-white text-xl">↖</button>
      <button onClick={() => editor.setCurrentTool('draw')} title="Draw" className="p-2 hover:bg-neutral-700 rounded-lg text-white text-xl">✏️</button>
      <button onClick={() => editor.setCurrentTool('eraser')} title="Eraser" className="p-2 hover:bg-neutral-700 rounded-lg text-white text-xl">🧹</button>
      <button onClick={() => editor.setCurrentTool('text')} title="Text" className="p-2 hover:bg-neutral-700 rounded-lg text-white text-xl">T</button>
      <button onClick={() => editor.setCurrentTool('geo')} title="Shape" className="p-2 hover:bg-neutral-700 rounded-lg text-white text-xl">□</button>

      <div className="w-8 h-px bg-neutral-700" />

      {/* Colors */}
      {COLORS.map(({ token, hex }) => (
        <button
          key={token}
          title={token}
          onClick={() => editor.setStyleForNextShapes(DefaultColorStyle, token)}
          className="w-7 h-7 rounded-full border-2 border-neutral-600 hover:border-white transition-colors"
          style={{ backgroundColor: hex }}
        />
      ))}

      <div className="w-8 h-px bg-neutral-700" />

      {/* Sizes */}
      {SIZES.map(({ token, px }) => (
        <button
          key={token}
          title={token}
          onClick={() => editor.setStyleForNextShapes(DefaultSizeStyle, token)}
          className="flex items-center justify-center w-8 h-8 hover:bg-neutral-700 rounded-lg"
        >
          <div className="bg-white rounded-full" style={{ width: px, height: px }} />
        </button>
      ))}
    </aside>
  )
}
