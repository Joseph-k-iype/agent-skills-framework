import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { computeSkillId, canonicalJson, type SkillManifest } from '../src/index'

const here = dirname(fileURLToPath(import.meta.url))
const fixture = JSON.parse(
  readFileSync(join(here, 'parity.fixture.json'), 'utf-8'),
) as { manifest: SkillManifest; files: Record<string, string>; expectedId: string }

describe('computeSkillId cross-language parity', () => {
  it('matches the id computed by the Python SDK for the same skill', async () => {
    const id = await computeSkillId(fixture.manifest, fixture.files)
    expect(id).toBe(fixture.expectedId)
  })

  it('ignores the id field when present (idempotent stamping)', async () => {
    const withId = { ...fixture.manifest, id: 'skill://sha256/deadbeef/x@1.0.0' }
    const a = await computeSkillId(withId, fixture.files)
    const b = await computeSkillId(fixture.manifest, fixture.files)
    expect(a).toBe(b)
  })

  it('changes when a source file changes', async () => {
    const a = await computeSkillId(fixture.manifest, fixture.files)
    const b = await computeSkillId(fixture.manifest, {
      ...fixture.files,
      'src/index.ts': 'export const x = 2\n',
    })
    expect(a).not.toBe(b)
  })
})

describe('canonicalJson', () => {
  it('sorts keys recursively with compact separators', () => {
    const out = canonicalJson({ b: 1, a: { d: 2, c: 3 } })
    expect(out).toBe('{"a":{"c":3,"d":2},"b":1}')
  })

  it('preserves array order', () => {
    expect(canonicalJson([3, 1, 2])).toBe('[3,1,2]')
  })
})
