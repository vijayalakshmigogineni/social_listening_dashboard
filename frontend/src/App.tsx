import { NavLink, Route, Routes } from 'react-router-dom'
import { DataCollection } from './pages/DataCollection'
import { Explorer } from './pages/Explorer'
import { Overview } from './pages/Overview'
import { PipelineDebug } from './pages/PipelineDebug'
import { PostDetail } from './pages/PostDetail'

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">ProbePS Social Listening Dashboard</div>
        <nav className="app-nav">
          <NavLink to="/" end>
            Overview
          </NavLink>
          <NavLink to="/explorer">All Signals</NavLink>
          <NavLink to="/collect">Data Collection</NavLink>
          <NavLink to="/debug">Pipeline / Debug</NavLink>
        </nav>
      </header>

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
        full Step 1–7 input/output trace for that record.
      </p>
    </div>
  )
}
