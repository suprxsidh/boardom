import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('tldraw', () => ({ DefaultColorStyle: {}, DefaultSizeStyle: {} }))

import DrawingToolbar from '@/components/canvas/DrawingToolbar'

function makeEditor() {
  return {
    setCurrentTool: vi.fn(),
    setStyleForNextShapes: vi.fn(),
  }
}

describe('DrawingToolbar', () => {
  it('renders null when editor is null', () => {
    const { container } = render(<DrawingToolbar editor={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('calls setCurrentTool("draw") when Draw clicked', () => {
    const editor = makeEditor()
    render(<DrawingToolbar editor={editor as any} />)
    fireEvent.click(screen.getByTitle('Draw'))
    expect(editor.setCurrentTool).toHaveBeenCalledWith('draw')
  })

  it('calls setCurrentTool("eraser") when Eraser clicked', () => {
    const editor = makeEditor()
    render(<DrawingToolbar editor={editor as any} />)
    fireEvent.click(screen.getByTitle('Eraser'))
    expect(editor.setCurrentTool).toHaveBeenCalledWith('eraser')
  })

  it('calls setCurrentTool("text") when Text clicked', () => {
    const editor = makeEditor()
    render(<DrawingToolbar editor={editor as any} />)
    fireEvent.click(screen.getByTitle('Text'))
    expect(editor.setCurrentTool).toHaveBeenCalledWith('text')
  })

  it('calls setCurrentTool("geo") when Shape clicked', () => {
    const editor = makeEditor()
    render(<DrawingToolbar editor={editor as any} />)
    fireEvent.click(screen.getByTitle('Shape'))
    expect(editor.setCurrentTool).toHaveBeenCalledWith('geo')
  })

  it('calls setStyleForNextShapes with color token when color swatch clicked', () => {
    const editor = makeEditor()
    render(<DrawingToolbar editor={editor as any} />)
    fireEvent.click(screen.getByTitle('red'))
    expect(editor.setStyleForNextShapes).toHaveBeenCalledWith({}, 'red')
  })

  it('calls setStyleForNextShapes with size token when size button clicked', () => {
    const editor = makeEditor()
    render(<DrawingToolbar editor={editor as any} />)
    fireEvent.click(screen.getByTitle('m'))
    expect(editor.setStyleForNextShapes).toHaveBeenCalledWith({}, 'm')
  })
})
