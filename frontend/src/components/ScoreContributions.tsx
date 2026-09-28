import type { ScoreBreakdown } from '../api/types'

const fmt = (n: number) => (Math.round(n * 10) / 10).toFixed(1)
const pct = (w: number) => `${Math.round(w * 100)}%`

interface Props {
  breakdown: ScoreBreakdown
  /** Show the raw points behind each component (Pipeline / Debug). */
  detailed?: boolean
}

/** Score x weight = contribution, for the three components, then caps and the
 *  final score -- read straight off the stored breakdown, nothing recomputed. */
export function ScoreContributions({ breakdown: b, detailed = false }: Props) {
  const rows = [
    {
      name: 'LLM opportunity assessment',
      score: b.llm_score,
      weight: b.weights.llm,
      contribution: b.llm_contribution,
      points: [
        ['problem evidence', b.llm_points.problem_evidence, 25],
        ['first person', b.llm_points.first_person, 10],
        ['seeking level', b.llm_points.seeking, 20],
        ['business impact', b.llm_points.business_impact, 15],
        ['recurring', b.llm_points.recurring, 5],
        ['ProbePS fit', b.llm_points.probeps_fit, 25],
      ] as const,
    },
    {
      name: 'RCM relevance',
      score: b.rcm_score,
      weight: b.weights.rcm,
      contribution: b.rcm_contribution,
      points: [
        ['relevance confidence', b.rcm_points.relevance, 50],
        [`category severity (${b.rcm_points.primary_problem_category ?? 'none'})`,
          b.rcm_points.category_severity, 50],
      ] as const,
    },
    {
      name: 'Step 3 payer / procedure',
      score: b.step3_score,
      weight: b.weights.step3,
      contribution: b.step3_contribution,
      points: [
        ['category', b.step3_points.category, 7],
        ['payer', b.step3_points.payer, 4],
        ['procedure', b.step3_points.procedure, 3],
        ['denial reason', b.step3_points.denial_reason, 3],
        ['code', b.step3_points.code, 2],
        ['specialty', b.step3_points.specialty, 1],
      ] as const,
    },
  ]

  return (
    <table className="score-table">
      <thead>
        <tr>
          <th>Component</th>
          <th className="num">Score</th>
          <th className="num">Weight</th>
          <th className="num">Contribution</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.name}>
            <td>
              {r.name}
              {detailed && (
                <div className="score-points">
                  {r.points.map(([label, value, max]) => (
                    <span key={label}>
                      {label} {fmt(value)}/{max}
                    </span>
                  ))}
                </div>
              )}
            </td>
            <td className="num">{fmt(r.score)}</td>
            <td className="num">{pct(r.weight)}</td>
            <td className="num">{fmt(r.contribution)}</td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        {(b.cap_applied || b.llm_cap_applied) && (
          <tr className="score-cap">
            <td colSpan={3}>{b.cap_reason}</td>
            <td className="num">{b.cap_applied ? `${fmt(b.pre_cap_score)} → ${fmt(b.final_score)}` : ''}</td>
          </tr>
        )}
        <tr>
          <td colSpan={3}>Final opportunity score</td>
          <td className="num">{fmt(b.final_score)}</td>
        </tr>
      </tfoot>
    </table>
  )
}
