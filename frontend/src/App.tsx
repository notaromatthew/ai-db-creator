import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import ProjectPage from './pages/ProjectPage'
import HelpPage from './pages/HelpPage'
import SettingsPage from './pages/SettingsPage'
import BenchmarkPage from './pages/BenchmarkPage'
import LLMStatus from './components/LLMStatus'
import ThemeToggle from './components/ThemeToggle'
import ProgressBar from './components/ProgressBar'
import { KeycloakProvider, useAuth } from './context/KeycloakContext'
import { api } from './api/client'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { authenticated, login } = useAuth()

  if (!authenticated) {
    return (
      <div className="mx-auto my-12 max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-xl dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-blue-50 text-3xl dark:bg-blue-950/50">
          🔒
        </div>
        <h2 className="mt-4 text-xl font-bold text-slate-900 dark:text-white">Autenticazione Richiesta</h2>
        <p className="mt-2 text-xs text-slate-500">
          Per accedere a questa sezione e gestire i tuoi progetti su AI DB Creator è necessario autenticarsi tramite Keycloak.
        </p>
        <button
          onClick={login}
          className="mt-6 w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3 text-sm font-bold text-white shadow-md hover:from-blue-700 hover:to-indigo-700"
        >
          🔑 Accedi con Keycloak
        </button>
      </div>
    )
  }

  return <>{children}</>
}

function MainContent() {
  const location = useLocation()
  const projectId = location.pathname.split('/')[2]
  const { authenticated, username, login, logout, token } = useAuth()

  useEffect(() => {
    api.setToken(token)
  }, [token])

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <nav className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90" aria-label="Navigazione principale">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-3 rounded-lg" aria-label="AI DB Creator, torna ai progetti">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 text-sm font-black text-white shadow-sm">DB</span>
              <span>
                <span className="block text-base font-bold leading-tight text-slate-900 dark:text-white">AI DB Creator</span>
                <span className="hidden text-xs text-slate-500 sm:block dark:text-slate-400">Dal documento al database, passo dopo passo</span>
              </span>
            </Link>

            <div className="hidden items-center gap-1 sm:flex">
              {authenticated && (
                <>
                  <Link to="/" className="rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                    Dashboard
                  </Link>
                  <Link to="/benchmark" className="rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                    📊 Benchmark
                  </Link>
                  <Link to="/settings" className="rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                    ⚙️ Configurazione
                  </Link>
                </>
              )}
              <Link to="/help" className="rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
                📚 Aiuto
              </Link>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* User Auth Status */}
            <div className="flex items-center gap-2.5 border-r border-slate-200 pr-3 dark:border-slate-800">
              {authenticated ? (
                <>
                  <div className="relative flex items-center gap-2">
                    <span className="grid h-7 w-7 place-items-center rounded-full bg-blue-600 text-xs font-bold text-white shadow-sm">
                      {username.charAt(0).toUpperCase()}
                    </span>
                    <span className="hidden text-xs font-bold text-slate-800 md:block dark:text-slate-200">
                      {username}
                    </span>
                    <span className="h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-emerald-500/20"></span>
                  </div>
                  <button
                    onClick={logout}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600 hover:bg-slate-100 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
                  >
                    Esci
                  </button>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-1.5">
                    <span className="grid h-7 w-7 place-items-center rounded-full bg-slate-200 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                      👤
                    </span>
                    <span className="hidden text-xs font-semibold text-amber-600 md:block dark:text-amber-400">
                      Ospite (Non autenticato)
                    </span>
                  </div>
                  <button
                    onClick={login}
                    className="rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 px-3 py-1 text-[11px] font-bold text-white shadow-sm hover:from-blue-700 hover:to-indigo-700"
                  >
                    🔑 Accedi con Keycloak
                  </button>
                </>
              )}
            </div>

            <ThemeToggle />
          </div>
        </div>
      </nav>

      <main className="mx-auto w-full max-w-7xl p-4 sm:p-6 lg:p-8">
        <Routes>
          <Route path="/" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="/projects/:id" element={<RequireAuth><ProjectPage /></RequireAuth>} />
          <Route path="/help" element={<HelpPage />} />
          <Route path="/settings" element={<RequireAuth><SettingsPage /></RequireAuth>} />
          <Route path="/benchmark" element={<RequireAuth><BenchmarkPage /></RequireAuth>} />
        </Routes>
      </main>
      {projectId && <ProgressBar projectId={projectId} />}
      <LLMStatus />
    </div>
  )
}

function App() {
  return (
    <KeycloakProvider>
      <MainContent />
    </KeycloakProvider>
  )
}

export default App
