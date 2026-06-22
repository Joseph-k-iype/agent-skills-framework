import { AlertTriangle } from 'lucide-react'
import { ApiError } from '../lib/api'

interface ErrorStateProps {
  error: unknown
  /** Optional retry handler (usually react-query's `refetch`). */
  onRetry?: () => void
  /** Short context, e.g. "Couldn't load skills". */
  title?: string
}

/**
 * Inline error state for failed data fetches. Distinct from the empty state:
 * a failed request must never masquerade as "no data". Surfaces the API
 * message and offers a retry so the user is never left at a dead end.
 */
export default function ErrorState({ error, onRetry, title = 'Something went wrong' }: ErrorStateProps) {
  const message =
    error instanceof ApiError
      ? error.message || `Request failed (${error.status})`
      : error instanceof Error
        ? error.message
        : 'The request failed. Check that the API server is running.'

  return (
    <div className="card py-12 text-center">
      <AlertTriangle size={36} className="mx-auto text-bad" />
      <p className="mt-3 text-base font-medium text-ink">{title}</p>
      <p className="mx-auto mt-1 max-w-md break-words text-sm text-ink-3">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary mt-4">
          Retry
        </button>
      )}
    </div>
  )
}
