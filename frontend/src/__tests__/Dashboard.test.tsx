import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from '../routes/Dashboard'

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Dashboard', () => {
  it('renders the heading', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })

  it('renders stats placeholder while loading', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getByText('Total Skills')).toBeInTheDocument()
    expect(screen.getByText('Versions')).toBeInTheDocument()
    expect(screen.getByText('Sources')).toBeInTheDocument()
    expect(screen.getByText('Registry')).toBeInTheDocument()
  })
})
