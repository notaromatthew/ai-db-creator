import { Routes, Route, Link, NavLink, Navigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import ProjectPage from './pages/ProjectPage'
import HelpPage from './pages/HelpPage'
import SettingsPage from './pages/SettingsPage'
import BenchmarkPage from './pages/BenchmarkPage'
import AdminPage from './pages/AdminPage'
import SharedProjectPage from './pages/SharedProjectPage'
import StudyPage from './pages/StudyPage'
import Landing from './site/Landing'
import LLMStatus from './components/LLMStatus'
import ThemeToggle from './components/ThemeToggle'
import ProgressBar from './components/ProgressBar'
import { KeycloakProvider, useAuth } from './context/KeycloakContext'
import { ConfigProvider, useConfig } from './config/AppConfig'
import { Logo } from './brand/Logo'
import SiteFooter from './brand/SiteFooter'
import { api } from './api/client'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { authenticated, login, register } = useAuth()
  const { config } = useConfig()

  if (!authenticated) {
    return (
      <div className="glass mx-auto my-12 max-w-md p-8 text-center">
        <Logo size={44} showName={false} />
        <h2 className="mt-4 text-xl font-bold">Accedi per continuare</h2>
        <p className="mt-2 text-sm text-tecnia-muted">I tuoi progetti sono privati: li vedi solo tu e chi decidi di far entrare.</p>
        <div className="mt-6 flex flex-col gap-3">
          <button onClick={login} className="primary-button w-full">Accedi</button>
          {config.registration_open && <button onClick={register} className="secondary-button w-full">Crea un account</button>}
        </div>
      </div>
    )
  }
  return <>{children}</>
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useAuth()
  return isAdmin ? <>{children}</> : <Navigate to="/app" replace />
}

const navCls = ({ isActive }: { isActive: boolean }) =>
  `rounded-full px-3.5 py-1.5 font-headline text-sm font-semibold transition ${isActive ? 'bg-orange-50 text-tecnia-primary' : 'text-tecnia-muted hover:bg-white/70'}`

function AppShell() {
  const location = useLocation()
  const projectId = location.pathname.match(/^\/app\/projects\/([^/]+)/)?.[1]
  const { authenticated, username, login, register, logout, token, isAdmin } = useAuth()
  const { config } = useConfig()

  useEffect(() => {
    api.setToken(token)
  }, [token])

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-tecnia-bg text-tecnia-ink dark:bg-slate-950 dark:text-slate-100">
      <div className="orb -left-32 -top-40 h-[500px] w-[500px] bg-[radial-gradient(circle,#ff6b00,transparent_70%)]" />
      {config.maintenance_message && (
        <div role="status" className="relative z-10 bg-orange-50 px-4 py-2 text-center text-sm text-tecnia-primary">{config.maintenance_message}</div>
      )}
      <nav className="sticky top-0 z-40 border-b border-tecnia-line/60 bg-white/80 backdrop-blur" aria-label="Navigazione principale">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-5">
            <Link to="/app" aria-label="AI-DB-Creator, torna ai progetti"><Logo size={34} /></Link>
            {authenticated && (
              <div className="hidden items-center gap-1 sm:flex">
                <NavLink to="/app" end className={navCls}>Progetti</NavLink>
                {config.research_mode && <NavLink to="/app/benchmark" className={navCls}>Benchmark</NavLink>}
                {config.research_mode && <NavLink to="/app/studio" className={navCls}>Studio</NavLink>}
                {isAdmin && <NavLink to="/app/admin" className={navCls}>Admin</NavLink>}
                {isAdmin && <NavLink to="/app/settings" className={navCls}>Modelli</NavLink>}
                <NavLink to="/app/help" className={navCls}>Aiuto</NavLink>
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            {authenticated ? (
              <>
                <span className="hidden text-sm font-semibold md:block">{username}</span>
                <button onClick={logout} className="secondary-button !min-h-9 !px-4">Esci</button>
              </>
            ) : (
              <>
                <button onClick={login} className="secondary-button !min-h-9 !px-4">Accedi</button>
                {config.registration_open && <button onClick={register} className="primary-button !min-h-9 !px-4">Registrati</button>}
              </>
            )}
            <ThemeToggle />
          </div>
        </div>
      </nav>

      <main className="relative z-10 mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6 lg:p-8">
        <Routes>
          <Route index element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="projects/:id" element={<RequireAuth><ProjectPage /></RequireAuth>} />
          <Route path="shared/:token" element={<SharedProjectPage />} />
          <Route path="help" element={<HelpPage />} />
          <Route path="settings" element={<RequireAuth><RequireAdmin><SettingsPage /></RequireAdmin></RequireAuth>} />
          <Route path="admin" element={<RequireAuth><RequireAdmin><AdminPage /></RequireAdmin></RequireAuth>} />
          {config.research_mode && <Route path="benchmark" element={<RequireAuth><BenchmarkPage /></RequireAuth>} />}
          {config.research_mode && <Route path="studio" element={<RequireAuth><StudyPage /></RequireAuth>} />}
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </main>
      {projectId && <ProgressBar projectId={projectId} />}
      <LLMStatus />
      <SiteFooter />
    </div>
  )
}

export default function App() {
  return (
    <ConfigProvider>
      <Routes>
        <Route path="/" element={<Landing lang="it" />} />
        <Route path="/en/*" element={<Landing lang="en" />} />
        <Route path="/app/*" element={<KeycloakProvider><AppShell /></KeycloakProvider>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ConfigProvider>
  )
}
