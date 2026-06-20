export function shortHash(id: string): string {
  const parts = id.split('/')
  const hash = parts[3]
  if (!hash) return id
  return hash.slice(0, 12)
}

export function formatDate(ts: string | number): string {
  const d = new Date(ts)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function pluralize(n: number, singular: string, plural?: string): string {
  return n === 1 ? `${n} ${singular}` : `${n} ${plural ?? singular + 's'}`
}

export function classNames(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}
