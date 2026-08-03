import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ProjectPage from './pages/ProjectPage'
import LLMStatus from './components/LLMStatus'
import ThemeToggle from './components/ThemeToggle'
import ProgressBar from './components/ProgressBar'

function App() {
  const location = useLocation()
  const projectId = location.pathname.split('/')[2]

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <nav className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90" aria-label="Navigazione principale">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <Link to="/" className="flex items-center gap-3 rounded-lg" aria-label="AI DB Creator, torna ai progetti">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-sm font-black text-white shadow-sm">DB</span>
            <span>
              <span className="block text-base font-bold leading-tight text-slate-900 dark:text-white">AI DB Creator</span>
              <span className="hidden text-xs text-slate-500 sm:block dark:text-slate-400">Dal documento al database, passo dopo passo</span>
            </span>
          </Link>
          <ThemeToggle />
        </div>
      </nav>
      <main className="mx-auto w-full max-w-7xl p-4 sm:p-6 lg:p-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects/:id" element={<ProjectPage />} />
        </Routes>
      </main>
      {projectId && <ProgressBar projectId={projectId} />}
      <LLMStatus />
    </div>
  )
}

export default App
