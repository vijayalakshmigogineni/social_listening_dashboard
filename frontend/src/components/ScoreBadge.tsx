interface Props {
  score: number | null
}

function scoreClass(score: number): string {
  if (score >= 20) return 'score-badge score-high'
  if (score >= 10) return 'score-badge score-mid'
  return 'score-badge score-low'
}

export function ScoreBadge({ score }: Props) {
  if (score === null) {
    return <span className="score-badge score-unanalyzed">—</span>
  }
  return <span className={scoreClass(score)}>{score.toFixed(1)}</span>
}
