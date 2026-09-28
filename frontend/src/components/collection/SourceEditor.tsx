import { useState } from 'react'
import { api } from '../../api/client'
import type { CollectionSource, SourceUnit } from '../../api/types'
import { plural } from './format'

interface Props {
  source: CollectionSource
  onSaved: (source: CollectionSource) => void
  onClose: () => void
}

/** Edit the units (subreddits, forums, groups, query families, accounts) one
 *  source collects. The backend validates and stores them; the next
 *  collection job uses them. */
export function SourceEditor({ source, onSaved, onClose }: Props) {
  const rule = source.unit_rule
  const [rows, setRows] = useState<SourceUnit[]>(() => source.unit_values.map((u) => ({ ...u })))
  const [saving, setSaving] = useState<'save' | 'reset' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const update = (i: number, patch: Partial<SourceUnit>) =>
    setRows((cur) => cur.map((r, j) => (j === i ? { ...r, ...patch } : r)))
  const remove = (i: number) => setRows((cur) => cur.filter((_, j) => j !== i))
  const add = () => setRows((cur) => [...cur, { name: '', value: '' }])

  const save = () => {
    setSaving('save')
    setError(null)
    api
      .saveSourceUnits(source.key, rows)
      .then(onSaved)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setSaving(null))
  }

  const reset = () => {
    setSaving('reset')
    setError(null)
    api
      .resetSourceUnits(source.key)
      .then(onSaved)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setSaving(null))
  }

  const unitWord = source.unit_label
  return (
    <section className="dc-card dc-editor" aria-label={`Edit ${source.label} ${plural(unitWord)}`}>
      <div className="dc-card-head">
        <h3>
          Edit {source.label} {plural(unitWord)}
        </h3>
        <span className="dc-subtle">
          {rows.length} / {rule.max_units} · used from the next fetch
        </span>
      </div>
      <p className="dc-subtle dc-editor-hint">
        {rule.value_label}: {rule.value_hint}
        {rule.named && ' · Name: short id, lowercase letters, digits or _'}
      </p>

      <div className="dc-editor-rows">
        {rows.map((row, i) => (
          <div key={i} className={`dc-editor-row${rule.named ? ' dc-editor-row-named' : ''}`}>
            {rule.named && (
              <input
                aria-label={`Name ${i + 1}`}
                placeholder="name"
                value={row.name}
                onChange={(e) => update(i, { name: e.target.value })}
              />
            )}
            <input
              aria-label={`${rule.value_label} ${i + 1}`}
              placeholder={rule.value_label}
              value={row.value}
              onChange={(e) => update(i, { value: e.target.value })}
            />
            <button className="dc-icon-btn" onClick={() => remove(i)} aria-label={`Remove row ${i + 1}`}>
              ×
            </button>
          </div>
        ))}
      </div>

      <button className="dc-link-btn" onClick={add} disabled={rows.length >= rule.max_units}>
        + Add {unitWord}
      </button>

      {error && <div className="dc-errors">{error}</div>}

      <div className="dc-editor-actions">
        <button className="dc-btn" onClick={save} disabled={saving !== null || rows.length === 0}>
          {saving === 'save' ? 'Saving…' : 'Save'}
        </button>
        <button className="dc-btn dc-btn-secondary" onClick={onClose} disabled={saving !== null}>
          Cancel
        </button>
        {source.customized && (
          <button className="dc-link-btn dc-editor-reset" onClick={reset} disabled={saving !== null}>
            {saving === 'reset' ? 'Resetting…' : 'Reset to defaults'}
          </button>
        )}
      </div>
    </section>
  )
}
