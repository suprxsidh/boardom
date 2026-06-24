import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('tldraw', () => ({
  createShapeId: vi.fn(() => 'shape:test-id'),
  Editor: class {},
}))

import StickerPanel from '@/components/canvas/StickerPanel'

function makeEditor() {
  return {
    getViewportPageBounds: vi.fn(() => ({ center: { x: 100, y: 200 } })),
    createShape: vi.fn(),
    select: vi.fn(),
  }
}

describe('StickerPanel', () => {
  it('renders null when editor is null', () => {
    const { container } = render(<StickerPanel editor={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows Notes tab by default', () => {
    const editor = makeEditor()
    render(<StickerPanel editor={editor as any} />)
    expect(screen.getByTitle('Add sticky note')).toBeInTheDocument()
  })

  it('switches to Emoji tab on click', () => {
    const editor = makeEditor()
    render(<StickerPanel editor={editor as any} />)
    fireEvent.click(screen.getByTitle('Emoji'))
    expect(screen.getByTitle('🔥')).toBeInTheDocument()
  })

  it('places a note shape when + button clicked', () => {
    const editor = makeEditor()
    render(<StickerPanel editor={editor as any} />)
    fireEvent.click(screen.getByTitle('Add sticky note'))
    expect(editor.createShape).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'note', x: 0, y: 100 })
    )
    expect(editor.select).toHaveBeenCalledWith('shape:test-id')
  })

  it('places an emoji text shape when emoji clicked', () => {
    const editor = makeEditor()
    render(<StickerPanel editor={editor as any} />)
    fireEvent.click(screen.getByTitle('Emoji'))
    fireEvent.click(screen.getByTitle('🔥'))
    expect(editor.createShape).toHaveBeenCalledWith(
      expect.objectContaining({
        type: 'text',
        x: 100,
        y: 200,
        props: { text: '🔥', size: 'xl', font: 'sans' },
      })
    )
    expect(editor.select).toHaveBeenCalledWith('shape:test-id')
  })
})
