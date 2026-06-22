import { useEffect, useState } from 'react'
import { X, Download, CheckCircle2, AlertCircle } from 'lucide-react'
import { api } from '../lib/api'
import { RequirePermission } from './RequireRole'

interface InstallModalProps {
  open: boolean
  onClose: () => void
  skillName: string
  versions: string[]
  latest: string
}

export default function InstallModal({ open, onClose, skillName, versions, latest }: InstallModalProps) {
  const [selectedVersion, setSelectedVersion] = useState(latest)
  const [targetPath, setTargetPath] = useState(`installed/${skillName}`)
  const [verify, setVerify] = useState(true)
  const [status, setStatus] = useState<'idle' | 'installing' | 'done' | 'error'>('idle')
  const [message, setMessage] = useState('')
  const [resultPath, setResultPath] = useState('')

  // Reset form state every time the modal opens — latest/versions load lazily,
  // so an always-mounted modal would otherwise keep stale defaults.
  useEffect(() => {
    if (open) {
      setSelectedVersion(latest)
      setTargetPath(`installed/${skillName}`)
      setVerify(true)
      setStatus('idle')
      setMessage('')
      setResultPath('')
    }
  }, [open, latest, skillName])

  if (!open) return null

  const handleInstall = async () => {
    setStatus('installing')
    setMessage('')
    try {
      const res = await api.skills.install(skillName, {
        version: selectedVersion,
        target: targetPath.trim() || undefined,
        verify,
      })
      setResultPath(res.path)
      setStatus('done')
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Installation failed')
      setStatus('error')
    }
  }

  const handleClose = () => {
    setStatus('idle')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm" onClick={handleClose}>
      <div className="w-full max-w-lg rounded-2xl border border-line bg-surface p-6 shadow-lift" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-ink">Install Skill</h3>
          <button onClick={handleClose} className="btn-ghost p-1" aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <RequirePermission
          actions={['skill:install']}
          fallback={
            <div className="flex items-center gap-2 rounded-lg border border-line bg-canvas p-3 text-sm text-ink-2">
              <AlertCircle size={16} className="text-warn" />
              You do not have permission to install skills
            </div>
          }
        >
          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm text-ink-2">Version</label>
              <select
                value={selectedVersion}
                onChange={(e) => setSelectedVersion(e.target.value)}
                aria-label="Version to install"
                className="input"
              >
                {versions.map((v) => (
                  <option key={v} value={v}>
                    {v} {v === latest ? '(latest)' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-sm text-ink-2">Target Path</label>
              <input
                type="text"
                value={targetPath}
                onChange={(e) => setTargetPath(e.target.value)}
                aria-label="Target install path"
                className="input font-mono text-sm"
              />
              <p className="mt-1 text-xs text-ink-3">Relative to the server workspace root.</p>
            </div>

            <label className="flex items-center gap-3 rounded-lg border border-line p-3 cursor-pointer hover:bg-canvas">
              <input
                type="checkbox"
                checked={verify}
                onChange={(e) => setVerify(e.target.checked)}
                className="h-4 w-4 rounded border-line bg-surface text-accent-500"
              />
              <div>
                <p className="text-sm font-medium text-ink">Verify content integrity</p>
                <p className="text-xs text-ink-2">Confirm hash matches the stored ID</p>
              </div>
            </label>

            {status === 'done' && (
              <div className="rounded-lg border border-line bg-canvas p-3 text-sm text-ink-2">
                <div className="flex items-center gap-2 text-ink">
                  <CheckCircle2 size={16} className="text-ok" />
                  Installed {skillName}@{selectedVersion}
                </div>
                {resultPath && <p className="mt-1 font-mono text-xs text-ink-3 break-all">{resultPath}</p>}
              </div>
            )}

            {status === 'error' && (
              <div className="flex items-start gap-2 rounded-lg border border-line bg-canvas p-3 text-sm text-bad">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <span className="break-words">{message || 'Installation failed'}</span>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button onClick={handleClose} className="btn-ghost">{status === 'done' ? 'Close' : 'Cancel'}</button>
              <button
                onClick={handleInstall}
                disabled={status === 'installing' || status === 'done'}
                className="btn-primary"
              >
                {status === 'installing' ? (
                  <>Installing...</>
                ) : status === 'done' ? (
                  <>Installed</>
                ) : (
                  <><Download size={16} /> Install</>
                )}
              </button>
            </div>
          </div>
        </RequirePermission>
      </div>
    </div>
  )
}
