import { Link } from 'react-router-dom'

export type StepState = 'done' | 'active' | 'todo'

export interface StepperState {
  choose: StepState
  fetch: StepState
  analyze: StepState
  dashboard: StepState
}

const STEPS: { key: keyof StepperState; title: string; help: string }[] = [
  { key: 'choose', title: 'Choose', help: 'Mode & sources' },
  { key: 'fetch', title: 'Fetch', help: 'Collect new posts' },
  { key: 'analyze', title: 'Analyze', help: 'Score for ProbePS' },
  { key: 'dashboard', title: 'Dashboard', help: 'See opportunities' },
]

/** Where the collect → analyze flow currently is, derived from live job
 *  state (the page advances it; nothing here is clickable except the end). */
export function CollectionStepper({ state }: { state: StepperState }) {
  return (
    <ol className="dc-stepper" aria-label="Collection progress">
      {STEPS.map((step, i) => {
        const s = state[step.key]
        const body = (
          <>
            <span className="dc-step-dot" aria-hidden="true">
              {s === 'done' ? '✓' : i + 1}
            </span>
            <span className="dc-step-text">
              <span className="dc-step-title">{step.title}</span>
              <span className="dc-step-help">{step.help}</span>
            </span>
          </>
        )
        return (
          <li key={step.key} className={`dc-step dc-step-${s}`} aria-current={s === 'active' ? 'step' : undefined}>
            {step.key === 'dashboard' && s !== 'todo' ? (
              <Link to="/" className="dc-step-link">
                {body}
              </Link>
            ) : (
              body
            )}
          </li>
        )
      })}
    </ol>
  )
}
