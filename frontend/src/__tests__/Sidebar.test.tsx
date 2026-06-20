import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Sidebar from '../components/layout/Sidebar'
import { AuthProvider } from '../lib/auth'

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <AuthProvider>
      <MemoryRouter>{ui}</MemoryRouter>
    </AuthProvider>,
  )
}

describe('Sidebar', () => {
  it('renders brand name', () => {
    renderWithProviders(<Sidebar />)
    expect(screen.getByText('Agent Skills')).toBeInTheDocument()
    expect(screen.getByText('Framework')).toBeInTheDocument()
  })

  it('renders main navigation items', () => {
    renderWithProviders(<Sidebar />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByText('Registry')).toBeInTheDocument()
  })

  it('renders version number', () => {
    renderWithProviders(<Sidebar />)
    expect(screen.getByText('v0.1.0')).toBeInTheDocument()
  })
})
