import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import NotFound from '../routes/NotFound'

describe('NotFound', () => {
  it('renders a not-found message and a way home', () => {
    render(
      <MemoryRouter>
        <NotFound />
      </MemoryRouter>,
    )
    expect(screen.getByText('Page not found')).toBeInTheDocument()
    expect(screen.getByText(/Back to Dashboard/i)).toBeInTheDocument()
  })
})
