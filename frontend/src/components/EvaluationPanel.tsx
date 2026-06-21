import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Play,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ThumbsUp,
  ThumbsDown,
  Loader2,
  ClipboardCheck,
} from 'lucide-react'
import { api, ApiError } from '../lib/api'
import { RequirePermission } from './RequireRole'
import type { EvalCase, ContentCriticFinding } from '../lib/types'

interface EvaluationPanelProps {
  skillName: string
  version: string
}

function judgeStatusBadge(status: 'ok' | 'skipped' | 'error', reason: string | null) {
  if (status === 'ok') return <span className="badge bg-emerald-600/10 text-emerald-400">judge: ok</span>
  if (status === 'error') {
    return (
      <span className="badge bg-red-600/10 text-red-400" title={reason ?? undefined}>
        judge: error
      </span>
    )
  }
  return (
    <span className="badge bg-gray-800 text-gray-400" title={reason ?? undefined}>
      judge: skipped
    </span>
  )
}

function severityBadge(severity: string) {
  if (severity === 'error') return <span className="badge bg-red-600/10 text-red-400">error</span>
  if (severity === 'warning') return <span className="badge bg-amber-600/10 text-amber-400">warning</span>
  return <span className="badge bg-gray-800 text-gray-400">info</span>
}

function resultStatusBadge(status: string) {
  if (status === 'passed') return <span className="badge bg-emerald-600/10 text-emerald-400">passed</span>
  if (status === 'failed') return <span className="badge bg-red-600/10 text-red-400">failed</span>
  if (status === 'error') return <span className="badge bg-red-600/10 text-red-400">error</span>
  return <span className="badge bg-gray-800 text-gray-400">{status}</span>
}

export default function EvaluationPanel({ skillName, version }: EvaluationPanelProps) {
  const queryClient = useQueryClient()
  const [judgeSpec, setJudgeSpec] = useState('')
  const [noJudge, setNoJudge] = useState(false)
  const [casesError, setCasesError] = useState<string | null>(null)

  const [newId, setNewId] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [newInputType, setNewInputType] = useState<'command' | 'event'>('command')
  const [newInputName, setNewInputName] = useState('')
  const [newPayload, setNewPayload] = useState('')
  const [newMode, setNewMode] = useState<'exact_match' | 'contains' | 'llm_judged'>('exact_match')
  const [newValue, setNewValue] = useState('')
  const [newRubric, setNewRubric] = useState('')
  const [addError, setAddError] = useState<string | null>(null)

  const casesQuery = useQuery({
    queryKey: ['eval-cases', skillName],
    queryFn: () => api.skills.evaluation.cases(skillName),
  })

  const latestQuery = useQuery({
    queryKey: ['eval-latest', skillName, version],
    queryFn: () => api.skills.evaluation.latest(skillName, version),
    retry: false,
  })

  const feedbackQuery = useQuery({
    queryKey: ['eval-feedback', skillName],
    queryFn: () => api.skills.evaluation.feedback(skillName),
  })

  const cases = casesQuery.data?.cases ?? []
  const report = latestQuery.error instanceof ApiError && latestQuery.error.status === 404 ? null : latestQuery.data
  const feedbackBySignature = new Map(
    (feedbackQuery.data?.entries ?? []).map((e) => [e.finding_signature, e.verdict]),
  )

  const saveCasesMutation = useMutation({
    mutationFn: (next: EvalCase[]) => api.skills.evaluation.updateCases(skillName, next),
    onSuccess: () => {
      setCasesError(null)
      queryClient.invalidateQueries({ queryKey: ['eval-cases', skillName] })
    },
    onError: (e) => setCasesError(e instanceof Error ? e.message : 'Failed to save cases'),
  })

  const runMutation = useMutation({
    mutationFn: () => api.skills.evaluation.run(skillName, noJudge ? 'none' : judgeSpec.trim() || undefined),
    onSuccess: (data) => {
      queryClient.setQueryData(['eval-latest', skillName, version], data)
      queryClient.invalidateQueries({ queryKey: ['audit'] })
      queryClient.invalidateQueries({ queryKey: ['compliance'] })
    },
  })

  const feedbackMutation = useMutation({
    mutationFn: (vars: { finding: ContentCriticFinding; verdict: 'accepted' | 'dismissed' }) =>
      api.skills.evaluation.submitFeedback(skillName, {
        finding_id: vars.finding.id,
        finding_signature: vars.finding.signature,
        finding_text: vars.finding.message,
        verdict: vars.verdict,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['eval-feedback', skillName] }),
  })

  const addCase = () => {
    setAddError(null)
    const id = newId.trim()
    const inputName = newInputName.trim()
    if (!id || !inputName) {
      setAddError('Case id and input name are required')
      return
    }
    if (cases.some((c) => c.id === id)) {
      setAddError(`A case with id "${id}" already exists`)
      return
    }

    let payload: Record<string, unknown> | undefined
    if (newPayload.trim()) {
      try {
        payload = JSON.parse(newPayload)
      } catch {
        setAddError('Payload must be valid JSON')
        return
      }
    }

    let value: Record<string, unknown> | undefined
    if (newMode !== 'llm_judged' && newValue.trim()) {
      try {
        value = JSON.parse(newValue)
      } catch {
        setAddError('Expected value must be valid JSON')
        return
      }
    }

    if (newMode === 'llm_judged' && !newRubric.trim()) {
      setAddError('llm_judged cases require a rubric')
      return
    }

    const next: EvalCase = {
      id,
      description: newDescription.trim() || undefined,
      input: { type: newInputType, name: inputName, ...(payload ? { payload } : {}) },
      expect:
        newMode === 'llm_judged'
          ? { mode: 'llm_judged', rubric: newRubric.trim() }
          : { mode: newMode, value: value ?? {} },
    }

    saveCasesMutation.mutate([...cases, next])
    setNewId('')
    setNewDescription('')
    setNewInputName('')
    setNewPayload('')
    setNewValue('')
    setNewRubric('')
  }

  const removeCase = (id: string) => {
    saveCasesMutation.mutate(cases.filter((c) => c.id !== id))
  }

  return (
    <div className="space-y-6">
      <div className="card">
        <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
          <ClipboardCheck size={14} /> Evaluation Cases
        </h3>

        {casesQuery.isLoading ? (
          <p className="text-sm text-gray-500">Loading cases...</p>
        ) : cases.length === 0 ? (
          <p className="mb-4 text-sm text-gray-500">No evaluation cases defined yet.</p>
        ) : (
          <div className="mb-4 space-y-2">
            {cases.map((c) => (
              <div key={c.id} className="flex items-start justify-between rounded-lg border border-gray-800 p-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-gray-200">{c.id}</span>
                    <span className="tag bg-gray-800 text-gray-400">{c.input.type}</span>
                    <span className="tag bg-gray-800 text-gray-400">{c.input.name}</span>
                    <span className="tag bg-brand-600/10 text-brand-400">{c.expect.mode}</span>
                  </div>
                  {c.description && <p className="mt-1 text-xs text-gray-500">{c.description}</p>}
                </div>
                <RequirePermission actions={['skill:evaluate']}>
                  <button
                    onClick={() => removeCase(c.id)}
                    className="btn-ghost p-1 shrink-0"
                    aria-label={`Remove case ${c.id}`}
                  >
                    <Trash2 size={14} />
                  </button>
                </RequirePermission>
              </div>
            ))}
          </div>
        )}

        {casesError && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-600/10 p-3 text-sm text-red-400">
            <AlertTriangle size={14} /> {casesError}
          </div>
        )}

        <RequirePermission
          actions={['skill:evaluate']}
          fallback={<p className="text-xs text-gray-600">You do not have permission to edit evaluation cases.</p>}
        >
          <div className="space-y-3 rounded-lg border border-gray-800 p-3">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Add Case</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                type="text"
                placeholder="case id"
                value={newId}
                onChange={(e) => setNewId(e.target.value)}
                className="input font-mono text-sm"
              />
              <input
                type="text"
                placeholder="description (optional)"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className="input text-sm"
              />
              <select
                value={newInputType}
                onChange={(e) => setNewInputType(e.target.value as 'command' | 'event')}
                className="input text-sm"
              >
                <option value="command">command</option>
                <option value="event">event</option>
              </select>
              <input
                type="text"
                placeholder={newInputType === 'command' ? '/validate' : 'data.source.updated'}
                value={newInputName}
                onChange={(e) => setNewInputName(e.target.value)}
                className="input font-mono text-sm"
              />
              <textarea
                placeholder='payload (JSON, optional) e.g. {"sources": []}'
                value={newPayload}
                onChange={(e) => setNewPayload(e.target.value)}
                className="input font-mono text-xs sm:col-span-2"
                rows={2}
              />
              <select
                value={newMode}
                onChange={(e) => setNewMode(e.target.value as typeof newMode)}
                className="input text-sm"
              >
                <option value="exact_match">exact_match</option>
                <option value="contains">contains</option>
                <option value="llm_judged">llm_judged</option>
              </select>
              {newMode === 'llm_judged' ? (
                <input
                  type="text"
                  placeholder="rubric"
                  value={newRubric}
                  onChange={(e) => setNewRubric(e.target.value)}
                  className="input text-sm"
                />
              ) : (
                <input
                  type="text"
                  placeholder='expected value (JSON) e.g. {"status": "success"}'
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  className="input font-mono text-sm"
                />
              )}
            </div>
            {addError && <p className="text-xs text-red-400">{addError}</p>}
            <button onClick={addCase} disabled={saveCasesMutation.isPending} className="btn-secondary">
              <Plus size={14} /> Add Case
            </button>
          </div>
        </RequirePermission>
      </div>

      <div className="card">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            <Play size={14} /> Run Evaluation
          </h3>
          <RequirePermission
            actions={['skill:evaluate']}
            fallback={<p className="text-xs text-gray-600">You do not have permission to run evaluations.</p>}
          >
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                placeholder="judge model, e.g. anthropic:claude-haiku-4-5 (optional)"
                value={judgeSpec}
                onChange={(e) => setJudgeSpec(e.target.value)}
                disabled={noJudge}
                className="input w-64 text-sm disabled:opacity-40"
              />
              <label className="flex items-center gap-1.5 text-xs text-gray-400">
                <input
                  type="checkbox"
                  checked={noJudge}
                  onChange={(e) => setNoJudge(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-gray-600 bg-gray-800 text-brand-600"
                />
                deterministic only
              </label>
              <button onClick={() => runMutation.mutate()} disabled={runMutation.isPending} className="btn-primary">
                {runMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                Run Evaluation
              </button>
            </div>
          </RequirePermission>
        </div>

        {runMutation.isError && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-600/10 p-3 text-sm text-red-400">
            <AlertTriangle size={14} />
            {runMutation.error instanceof Error ? runMutation.error.message : 'Evaluation run failed'}
          </div>
        )}

        {latestQuery.isLoading ? (
          <p className="text-sm text-gray-500">Loading latest report...</p>
        ) : !report ? (
          <p className="text-sm text-gray-500">No evaluation has been run for v{version} yet.</p>
        ) : (
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              {judgeStatusBadge(report.judge_status, report.judge_skip_reason)}
              {report.overall_score != null && (
                <span className="badge bg-brand-600/10 text-brand-400">score: {report.overall_score}</span>
              )}
              <span className="text-xs text-gray-600">{new Date(report.run_at).toLocaleString()}</span>
            </div>

            <p className="text-sm text-gray-400">{report.summary}</p>

            {report.judge_status !== 'ok' && report.judge_skip_reason && (
              <div>
                <p className={`mb-1 text-xs font-medium uppercase tracking-wider ${
                  report.judge_status === 'error' ? 'text-red-400' : 'text-gray-500'
                }`}>
                  {report.judge_status === 'error' ? 'Judge Error' : 'Judge Skipped'}
                </p>
                <p className={`whitespace-pre-wrap break-words text-sm ${
                  report.judge_status === 'error' ? 'text-red-400' : 'text-gray-500'
                }`}>
                  {report.judge_skip_reason}
                </p>
              </div>
            )}

            {report.structural_errors.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-medium uppercase tracking-wider text-red-400">Structural Errors</p>
                <ul className="list-inside list-disc space-y-1 text-sm text-red-400">
                  {report.structural_errors.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              </div>
            )}

            {report.structural_warnings.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-medium uppercase tracking-wider text-amber-400">Structural Warnings</p>
                <ul className="list-inside list-disc space-y-1 text-sm text-amber-400">
                  {report.structural_warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}

            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-400">
                Content Critic Findings {report.content_critic.model ? `(${report.content_critic.model})` : ''}
              </p>
              {report.content_critic.findings.length === 0 ? (
                <p className="text-sm text-gray-500">No findings.</p>
              ) : (
                <div className="space-y-2">
                  {report.content_critic.findings.map((f) => {
                    const verdict = feedbackBySignature.get(f.signature)
                    return (
                      <div key={f.id} className="rounded-lg border border-gray-800 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              {severityBadge(f.severity)}
                              <span className="text-xs font-mono text-gray-500">{f.field}</span>
                              {verdict && (
                                <span className={`badge ${verdict === 'accepted' ? 'bg-emerald-600/10 text-emerald-400' : 'bg-gray-800 text-gray-500'}`}>
                                  {verdict}
                                </span>
                              )}
                            </div>
                            <p className="mt-1 text-sm text-gray-300">{f.message}</p>
                            {f.suggestion && <p className="mt-1 text-xs text-gray-500">Suggestion: {f.suggestion}</p>}
                          </div>
                          <RequirePermission actions={['skill:evaluate']}>
                            <div className="flex shrink-0 gap-1">
                              <button
                                onClick={() => feedbackMutation.mutate({ finding: f, verdict: 'accepted' })}
                                disabled={feedbackMutation.isPending}
                                className="btn-ghost p-1"
                                aria-label="Accept finding"
                                title="Accept"
                              >
                                <ThumbsUp size={14} />
                              </button>
                              <button
                                onClick={() => feedbackMutation.mutate({ finding: f, verdict: 'dismissed' })}
                                disabled={feedbackMutation.isPending}
                                className="btn-ghost p-1"
                                aria-label="Dismiss finding"
                                title="Dismiss"
                              >
                                <ThumbsDown size={14} />
                              </button>
                            </div>
                          </RequirePermission>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-gray-400">
                Test Cases ({report.test_executor.passed}/{report.test_executor.total} passed)
              </p>
              {report.test_executor.results.length === 0 ? (
                <p className="text-sm text-gray-500">No test cases defined.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase">
                        <th className="pb-2 pr-4 font-medium">Case</th>
                        <th className="pb-2 pr-4 font-medium">Mode</th>
                        <th className="pb-2 pr-4 font-medium">Status</th>
                        <th className="pb-2 font-medium">Detail</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.test_executor.results.map((r) => (
                        <tr key={r.case_id} className="border-b border-gray-800/50">
                          <td className="py-2 pr-4 font-mono text-xs text-gray-300">{r.case_id}</td>
                          <td className="py-2 pr-4 text-gray-400">{r.mode}</td>
                          <td className="py-2 pr-4">{resultStatusBadge(r.status)}</td>
                          <td className="py-2 text-xs text-gray-500">
                            {r.detail ?? r.rationale ?? (r.score != null ? `score: ${r.score}` : '')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {report === null && latestQuery.error && !(latestQuery.error instanceof ApiError && latestQuery.error.status === 404) && (
          <div className="flex items-center gap-2 rounded-lg bg-red-600/10 p-3 text-sm text-red-400">
            <XCircle size={14} />
            {latestQuery.error instanceof Error ? latestQuery.error.message : 'Failed to load latest evaluation'}
          </div>
        )}
      </div>

      {!feedbackQuery.isLoading && (feedbackQuery.data?.entries.length ?? 0) > 0 && (
        <div className="card">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-300 uppercase tracking-wider">
            <CheckCircle2 size={14} /> Feedback History
          </h3>
          <div className="space-y-1">
            {feedbackQuery.data!.entries.map((e, i) => (
              <div key={`${e.finding_id}-${i}`} className="flex items-center justify-between text-xs">
                <span className="truncate text-gray-400">{e.finding_text}</span>
                <span className={`badge shrink-0 ${e.verdict === 'accepted' ? 'bg-emerald-600/10 text-emerald-400' : 'bg-gray-800 text-gray-500'}`}>
                  {e.verdict}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
