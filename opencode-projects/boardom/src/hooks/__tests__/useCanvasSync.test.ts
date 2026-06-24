import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'

// Mock tldraw entirely to avoid browser environment requirements (CSS.supports, etc.)
vi.mock('tldraw', () => ({
  InstancePresenceRecordType: {
    create: vi.fn((data: Record<string, unknown>) => data),
    createId: vi.fn((id: string) => `presence:${id}`),
  },
}))

import { useCanvasSync } from '@/hooks/useCanvasSync'

const mockMergeRemoteChanges = vi.fn((fn: () => void) => fn())
const mockPut = vi.fn()
const mockRemove = vi.fn()
const mockListen = vi.fn().mockReturnValue(() => {})

const mockEditor = {
  store: {
    listen: mockListen,
    mergeRemoteChanges: mockMergeRemoteChanges,
    put: mockPut,
    remove: mockRemove,
  },
  inputs: { currentPagePoint: { x: 10, y: 20 } },
  getCurrentPageId: vi.fn().mockReturnValue('page:1'),
  user: { getId: vi.fn().mockReturnValue('local-user') },
}

describe('useCanvasSync', () => {
  beforeEach(() => vi.clearAllMocks())

  it('calls store.listen when editor is provided', () => {
    renderHook(() =>
      useCanvasSync({ editor: mockEditor as any, sendData: vi.fn(), remoteUserId: 'remote' })
    )
    expect(mockListen).toHaveBeenCalled()
  })

  it('does not call store.listen when editor is null', () => {
    renderHook(() =>
      useCanvasSync({ editor: null, sendData: vi.fn(), remoteUserId: 'remote' })
    )
    expect(mockListen).not.toHaveBeenCalled()
  })

  it('applyRemoteData calls mergeRemoteChanges for store-change messages', () => {
    const { result } = renderHook(() =>
      useCanvasSync({ editor: mockEditor as any, sendData: vi.fn(), remoteUserId: 'remote' })
    )

    const msg = JSON.stringify({
      type: 'store-change',
      added: [{ id: 'shape:1', typeName: 'shape' }],
      updated: [],
      removed: [],
    })

    act(() => result.current.applyRemoteData(msg))
    expect(mockMergeRemoteChanges).toHaveBeenCalled()
    expect(mockPut).toHaveBeenCalledWith([{ id: 'shape:1', typeName: 'shape' }])
  })

  it('applyRemoteData calls store.remove for removed records', () => {
    const { result } = renderHook(() =>
      useCanvasSync({ editor: mockEditor as any, sendData: vi.fn(), remoteUserId: 'remote' })
    )

    const msg = JSON.stringify({
      type: 'store-change',
      added: [],
      updated: [],
      removed: ['shape:1'],
    })

    act(() => result.current.applyRemoteData(msg))
    expect(mockRemove).toHaveBeenCalledWith(['shape:1'])
  })
})
