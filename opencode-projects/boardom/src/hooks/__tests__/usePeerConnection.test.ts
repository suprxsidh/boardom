import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePeerConnection } from '@/hooks/usePeerConnection'
import SimplePeer from 'simple-peer'

vi.mock('simple-peer')

const mockOn = vi.fn()
const mockSignal = vi.fn()
const mockSend = vi.fn()
const mockDestroy = vi.fn()

const mockPeerInstance = {
  on: mockOn,
  signal: mockSignal,
  send: mockSend,
  destroy: mockDestroy,
  connected: true,
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(SimplePeer).mockImplementation(function () {
    return mockPeerInstance as unknown as SimplePeer.Instance
  })
  mockOn.mockReturnValue(mockPeerInstance)
})

describe('usePeerConnection', () => {
  it('creates SimplePeer with correct initiator flag', () => {
    renderHook(() =>
      usePeerConnection({
        isInitiator: true,
        onSignal: vi.fn(),
        onConnect: vi.fn(),
        onData: vi.fn(),
        onClose: vi.fn(),
      })
    )
    expect(SimplePeer).toHaveBeenCalledWith({ initiator: true, trickle: true })
  })

  it('fires onSignal when peer emits signal', () => {
    const onSignal = vi.fn()
    renderHook(() =>
      usePeerConnection({ isInitiator: false, onSignal, onConnect: vi.fn(), onData: vi.fn(), onClose: vi.fn() })
    )

    const signalHandler = mockOn.mock.calls.find(([e]) => e === 'signal')?.[1]
    act(() => signalHandler?.({ type: 'offer' }))
    expect(onSignal).toHaveBeenCalledWith({ type: 'offer' })
  })

  it('receiveSignal feeds signal into peer', () => {
    const { result } = renderHook(() =>
      usePeerConnection({ isInitiator: false, onSignal: vi.fn(), onConnect: vi.fn(), onData: vi.fn(), onClose: vi.fn() })
    )
    act(() => result.current.receiveSignal({ type: 'answer' } as SimplePeer.SignalData))
    expect(mockSignal).toHaveBeenCalledWith({ type: 'answer' })
  })

  it('sendData calls peer.send when connected', () => {
    const { result } = renderHook(() =>
      usePeerConnection({ isInitiator: false, onSignal: vi.fn(), onConnect: vi.fn(), onData: vi.fn(), onClose: vi.fn() })
    )
    act(() => result.current.sendData('hello'))
    expect(mockSend).toHaveBeenCalledWith('hello')
  })
})
