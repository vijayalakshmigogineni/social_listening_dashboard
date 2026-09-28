import { NavLink, Route, Routes } from 'react-router-dom'
import { DataCollection } from './pages/DataCollection'
import { Explorer } from './pages/Explorer'
import { Overview } from './pages/Overview'
import { PipelineDebug } from './pages/PipelineDebug'
import { PostDetail } from './pages/PostDetail'

/** 20px line icons, drawn in currentColor so they follow the link state. */
const ICONS: Record<string, string> = {
  overview: 'M3 3h7v7H3zM14 3h7v4h-7zM14 11h7v10h-7zM3 14h7v7H3z',
  signals: 'M4 6h16M4 12h16M4 18h10',
  collect: 'M12 3v12m0 0-4-4m4 4 4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2',
  debug: 'M4 7h4l2 10 4-14 2 4h4',
}

function NavIcon({ name }: { name: string }) {
  return (
    <svg className="nav-icon" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path d={ICONS[name]} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

const NAV = [
  { to: '/', label: 'Overview', icon: 'overview', end: true },
  { to: '/explorer', label: 'All Signals', icon: 'signals', end: false },
  { to: '/collect', label: 'Data Collection', icon: 'collect', end: false },
  { to: '/debug', label: 'Pipeline / Debug', icon: 'debug', end: false },
]

export default function App() {
  return (
    <div className="app">
      <aside className="app-sidebar">
        <div className="app-title">
          <span className="brand-mark" aria-hidden="true">P</span>
          <span className="app-title-text">
            ProbePS
            <span className="app-title-sub">Social Listening</span>
          </span>
        </div>
        <nav className="app-nav" aria-label="Main">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              <NavIcon name={item.icon} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="app-sidebar-foot">RCM opportunity intelligence</div>
      </aside>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/explorer" element={<Explorer />} />
          <Route path="/collect" element={<DataCollection />} />
          <Route path="/posts/:source/:sourceItemId" element={<PostDetail />} />
          <Route path="/pipeline/:source/:sourceItemId" element={<PipelineDebug />} />
          <Route path="/debug" element={<DebugLanding />} />
        </Routes>
      </main>
    </div>
  )
}

function DebugLanding() {
  return (
    <div className="debug-landing">
      <h2>Pipeline / Debug</h2>
      <p>
        Open any post from Overview or All Signals and click "View pipeline breakdown" to see the
        stored scoring breakdown for that record: RCM relevance, Step 3 payer/procedure, the LLM opportunity assessment and the 65/20/15 contributions to the final score.
      </p>
    </div>
  )
}
