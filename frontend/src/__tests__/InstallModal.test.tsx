import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import InstallModal from '../components/InstallModal'
import { AuthProvider } from '../lib/auth'

function renderModal(open: boolean) {
  return render(
    <AuthProvider>
      <InstallModal
        open={open}
        onClose={vi.fn()}
        skillName="data-quality"
        versions={['1.0.0']}
        latest="1.0.0"
      />
    </AuthProvider>,
  )
}

describe('InstallModal', () => {
  it('renders nothing when closed', () => {
    const { container } = renderModal(false)
    expect(container).toBeEmptyDOMElement()
  })

  it('gates installation behind the skill:install permission', () => {
    // The default role is "developer", which cannot install (consumer/admin can).
    renderModal(true)
    expect(screen.getByText('Install Skill')).toBeInTheDocument()
    expect(screen.getByText(/do not have permission to install/i)).toBeInTheDocument()
  })
})
