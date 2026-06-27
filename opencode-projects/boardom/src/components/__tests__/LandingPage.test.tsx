import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import LandingPage from '@/components/LandingPage'

const mockPush = vi.fn()
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: mockPush }) }))

describe('LandingPage', () => {
  it('renders wordmark', () => {
    render(<LandingPage />)
    expect(screen.getByText('Boredroom')).toBeInTheDocument()
  })

  it('Start button disabled until 18+ checkbox checked', () => {
    render(<LandingPage />)
    const button = screen.getByRole('button', { name: /start/i })
    expect(button).toBeDisabled()
    fireEvent.click(screen.getByRole('checkbox'))
    expect(button).not.toBeDisabled()
  })

  it('Start navigates /waiting', () => {
    render(<LandingPage />)
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: /start/i }))
    expect(mockPush).toHaveBeenCalledWith('/waiting')
  })
})
