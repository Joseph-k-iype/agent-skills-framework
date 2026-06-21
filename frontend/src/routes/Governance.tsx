import { Fragment, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Shield, CheckCircle2, XCircle, Package, FileKey, Lock, GitBranch } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'

export default function Governance() {
  const { can } = useAuth()
  const canAudit = can('skill:audit')

  // Single backend call returns per-skill compliance — no more N+1 waterfall of
  // validate+manifest requests from the browser.
  const { data, isLoading } = useQuery({
    queryKey: ['compliance'],
    queryFn: api.skills.compliance,
  })

  const [impactTarget, setImpactTarget] = useState<string | null>(null)
  const { data: impact, isLoading: impactLoading } = useQuery({
    queryKey: ['impact', impactTarget],
    queryFn: () => api.skills.impact(impactTarget!),
    enabled: !!impactTarget,
  })

  const rows = data?.skills ?? []
  const validCount = rows.filter((r) => r.valid === true).length
  const failCount = rows.filter((r) => r.valid === false).length
  const totalPermissions = rows.reduce((s, r) => s + r.permissions, 0)
  const totalCapabilities = rows.reduce((s, r) => s + r.capabilities, 0)

  const stats = [
    { label: 'Skills', value: rows.length, icon: Package },
    { label: 'Passing', value: validCount, icon: CheckCircle2 },
    { label: 'Failing', value: failCount, icon: XCircle },
    { label: 'Capabilities', value: totalCapabilities, icon: FileKey },
  ]

  const policies = [
    {
      name: 'Valid Manifest',
      pass: validCount,
      total: rows.length,
      status: rows.length === 0 ? 'unknown' : failCount === 0 ? 'pass' : 'warn',
    },
    {
      name: 'Content Hash Integrity',
      pass: validCount,
      total: rows.length,
      status: rows.length === 0 ? 'unknown' : failCount === 0 ? 'pass' : 'warn',
    },
    {
      name: 'Permission Declarations',
      pass: rows.filter((r) => r.permissions > 0).length,
      total: rows.length,
      status: rows.length > 0 && totalPermissions === 0 ? 'warn' : 'pass',
    },
  ] as const

  const byResource = new Map<string, { skill: string; actions: string[] }[]>()
  rows.forEach((r) => {
    (r.permission_details ?? []).forEach((p) => {
      const list = byResource.get(p.resource) ?? []
      list.push({ skill: r.name, actions: p.actions })
      byResource.set(p.resource, list)
    })
  })

  return (
    <div className="space-y-10">
      <div>
        <p className="eyebrow">Governance</p>
        <h2 className="mt-2 text-3xl font-semibold tracking-tightish text-ink">Governance</h2>
        <p className="mt-2 text-sm text-ink-2">Compliance, permissions, and policy overview</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(({ label, value, icon: Icon }) => (
          <div key={label} className="card">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-canvas text-ink-2">
                <Icon size={20} />
              </div>
              <div>
                <p className="eyebrow">{label}</p>
                <p className="mt-1 text-2xl font-light tabular-nums tracking-tightish text-ink">{isLoading ? '...' : value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h3 className="eyebrow mb-4 flex items-center gap-2">
            <Shield size={14} /> Policy Compliance
          </h3>
          <div className="space-y-3">
            {policies.map((policy) => (
              <div key={policy.name} className="flex items-center justify-between rounded-lg border border-line p-3">
                <div className="flex items-center gap-3">
                  <span className={`h-1.5 w-1.5 rounded-full ${
                    policy.status === 'pass' ? 'bg-ok' :
                    policy.status === 'warn' ? 'bg-warn' :
                    'bg-ink-3'
                  }`} />
                  <div>
                    <p className="text-sm font-medium text-ink">{policy.name}</p>
                    <p className="text-xs text-ink-3">{policy.pass}/{policy.total} passing</p>
                  </div>
                </div>
                <span className="badge bg-canvas border border-line text-ink-2">
                  {policy.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 className="eyebrow mb-4 flex items-center gap-2">
            <Lock size={14} /> Permissions &amp; Capabilities
          </h3>
          {rows.length === 0 ? (
            <div className="py-8 text-center">
              <Lock size={32} className="mx-auto text-ink-3" />
              <p className="mt-2 text-sm text-ink-2">No skills in registry</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {rows.map((r) => (
                <div key={r.name} className="flex items-center justify-between rounded-lg border border-line p-2">
                  <span className="text-sm text-ink">{r.name}</span>
                  <div className="flex gap-2">
                    <span className="badge bg-canvas border border-line text-ink-2 text-[10px]">{r.permissions} perms</span>
                    <span className="badge bg-canvas border border-line text-ink-2 text-[10px]">{r.capabilities} caps</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h3 className="eyebrow mb-4 flex items-center gap-2">
          <FileKey size={14} /> Permissions by Resource
        </h3>
        {byResource.size === 0 ? (
          <div className="py-8 text-center">
            <FileKey size={32} className="mx-auto text-ink-3" />
            <p className="mt-2 text-sm text-ink-2">No skill declares any permissions</p>
          </div>
        ) : (
          <div className="space-y-3">
            {[...byResource.entries()].map(([resource, entries]) => (
              <div key={resource} className="rounded-lg border border-line p-3">
                <p className="text-sm font-medium text-ink">{resource}</p>
                <div className="mt-2 space-y-1">
                  {entries.map((e, i) => (
                    <div key={`${e.skill}-${i}`} className="flex items-center justify-between text-xs">
                      <span className="text-ink-2">{e.skill}</span>
                      <span className="text-ink-3">{e.actions.join(', ')}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="eyebrow mb-4">Skill Compliance</h3>
        {rows.length === 0 ? (
          <div className="py-8 text-center">
            <Package size={32} className="mx-auto text-ink-3" />
            <p className="mt-2 text-sm text-ink-2">No skills in registry</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left eyebrow">
                  <th className="pb-2 pr-4 font-medium">Skill</th>
                  <th className="pb-2 pr-4 font-medium">Runtime</th>
                  <th className="pb-2 pr-4 font-medium">Permissions</th>
                  <th className="pb-2 pr-4 font-medium">Capabilities</th>
                  <th className="pb-2 pr-4 font-medium">Compliance</th>
                  <th className="pb-2 pr-4 font-medium">Eval Score</th>
                  {canAudit && <th className="pb-2 font-medium">Impact</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((r) => (
                  <Fragment key={r.name}>
                    <tr>
                      <td className="py-3 pr-4">
                        <p className="font-medium text-ink">{r.name}</p>
                        <p className="font-mono text-xs text-ink-3">v{r.latest}</p>
                      </td>
                      <td className="py-3 pr-4">
                        {r.runtime && <span className="tag">{r.runtime}</span>}
                      </td>
                      <td className="py-3 pr-4 text-ink-2">{r.permissions}</td>
                      <td className="py-3 pr-4 text-ink-2">{r.capabilities}</td>
                      <td className="py-3 pr-4">
                        {r.valid === null ? (
                          <span className="text-ink-3">—</span>
                        ) : r.valid ? (
                          <span className="badge bg-canvas border border-line text-ink-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-ok" />
                            Valid
                          </span>
                        ) : (
                          <span className="badge bg-canvas border border-line text-ink-2" title={r.errors.join('; ')}>
                            <span className="h-1.5 w-1.5 rounded-full bg-bad" />
                            Invalid
                          </span>
                        )}
                      </td>
                      <td className="py-3 pr-4">
                        {r.last_evaluation_score == null ? (
                          <span className="text-ink-3">—</span>
                        ) : (
                          <span className="badge bg-canvas border border-line text-ink-2">
                            <span className={`h-1.5 w-1.5 rounded-full ${
                              r.last_evaluation_score >= 80 ? 'bg-ok' :
                              r.last_evaluation_score >= 50 ? 'bg-warn' :
                              'bg-bad'
                            }`} />
                            {r.last_evaluation_score.toFixed(0)}
                          </span>
                        )}
                      </td>
                      {canAudit && (
                        <td className="py-3">
                          <button
                            onClick={() => setImpactTarget(impactTarget === r.name ? null : r.name)}
                            className="btn-ghost text-xs"
                          >
                            <GitBranch size={12} /> {impactTarget === r.name ? 'Hide' : 'Show Impact'}
                          </button>
                        </td>
                      )}
                    </tr>
                    {canAudit && impactTarget === r.name && (
                      <tr className="bg-canvas">
                        <td colSpan={7} className="py-3 px-4 text-xs">
                          {impactLoading ? (
                            <span className="text-ink-3">Loading downstream impact...</span>
                          ) : !impact || impact.count === 0 ? (
                            <span className="text-ink-3">No other skills depend on {r.name}.</span>
                          ) : (
                            <div>
                              <p className="mb-1 text-ink-2">
                                {impact.count} skill{impact.count !== 1 ? 's' : ''} would be affected if {r.name} changes:
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {impact.downstream.map((d) => (
                                  <span key={d} className="tag">{d}</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
