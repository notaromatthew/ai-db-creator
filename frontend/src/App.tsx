import { Routes, Route, Link, NavLink, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import Dashboard from './pages/Dashboard'
import ProjectPage from './pages/ProjectPage'
import HelpPage from './pages/HelpPage'
import SettingsPage from './pages/SettingsPage'
import BenchmarkPage from './pages/BenchmarkPage'
import AdminPage from './pages/AdminPage'
import SharedProjectPage from './pages/SharedProjectPage'
import ExamplesPage from './pages/ExamplesPage'
import ExampleDetailPage from './pages/ExampleDetailPage'
import StudyPage from './pages/StudyPage'
import ResearchPage from './pages/research/ResearchPage'
import LegalPage from './pages/LegalPage'
import OnboardingPage from './pages/OnboardingPage'
import { OnboardingDialog, hasSeenOnboarding, markOnboardingSeen } from './components/Onboarding'
import SessionBanner from './components/SessionBanner'
import { markAutoLogin, sanitizeReturnPath, saveReturnTo, shouldAutoLogin } from './hooks/authReturn'
import Landing from './site/Landing'
import LLMStatus from './components/LLMStatus'
import ThemeToggle from './components/ThemeToggle'
import ProgressBar from './components/ProgressBar'
import { KeycloakProvider, useAuth } from './context/KeycloakContext'
import { ConfigProvider, useConfig } from './config/AppConfig'
import { Logo } from './brand/Logo'
import SiteFooter from './brand/SiteFooter'
import { api } from './api/client'

/** /app/login e /app/register: aprono subito Keycloak e, dopo l'accesso, riportano a ?next= (o alla home). */
function AuthEntry({ mode }: { mode: 'login' | 'register' }) {
  const { authenticated, login, register } = useAuth()
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const ran = useRef(false)
  useEffect(() => {
    if (ran.current) return
    ran.current = true
    const next = sanitizeReturnPath(params.get('next'))
    if (authenticated) { navigate(next ?? '/app', { replace: true }); return }
    saveReturnTo(next)
    markAutoLogin()
    if (mode === 'register') register()
    else login()
  }, [authenticated, login, register, mode, navigate, params])
  return (
    <div role="status" className="glass mx-auto my-12 max-w-md p-8 text-center">
      <p className="font-headline text-lg font-bold">{mode === 'register' ? 'Ti porto alla registrazione…' : 'Ti porto all\'accesso…'}</p>
      <p className="mt-2 text-sm text-tecnia-muted">Se non succede nulla, <button type="button" className="underline" onClick={mode === 'register' ? register : login}>premi qui</button>.</p>
    </div>
  )
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { authenticated, login, register } = useAuth()
  const { config } = useConfig()
  const [redirecting, setRedirecting] = useState(false)

  // Senza sessione si va subito al login (una volta sola, per non fare giri a vuoto se si annulla).
  useEffect(() => {
    if (!authenticated && shouldAutoLogin()) {
      markAutoLogin()
      setRedirecting(true)
      login()
    }
  }, [authenticated, login])

  if (!authenticated) {
    return (
      <div className="glass mx-auto my-12 max-w-md p-8 text-center">
        <Logo size={44} showName={false} />
        <h2 className="mt-4 text-xl font-bold">Accedi per continuare</h2>
        <p className="mt-2 text-sm text-tecnia-muted" role="status">
          {redirecting ? 'Ti porto alla pagina di accesso…' : 'I tuoi progetti sono privati: li vedi solo tu e chi decidi di far entrare.'}
        </p>
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
  `rounded-full px-3.5 py-1.5 font-headline text-sm font-semibold transition ${isActive ? 'bg-orange-50 text-tecnia-primary dark:bg-slate-800' : 'text-tecnia-muted hover:bg-white/70 dark:hover:bg-slate-800'}`

function AppShell() {
  const location = useLocation()
  const projectId = location.pathname.match(/^\/app\/projects\/([^/]+)/)?.[1]
  const { authenticated, username, login, register, logout, token, isAdmin } = useAuth()
  const { config } = useConfig()
  const { roles: authRoles } = useAuth()
  const canResearch = config.research_mode && (isAdmin || authRoles.includes('aidb-researcher'))

  useEffect(() => {
    api.setToken(token)
  }, [token])

  const [showOnboarding, setShowOnboarding] = useState(false)
  useEffect(() => {
    if (authenticated && username && username !== 'Ospite' && !hasSeenOnboarding(username) && !location.pathname.startsWith('/app/benvenuto')) setShowOnboarding(true)
  }, [authenticated, username, location.pathname])
  const closeOnboarding = () => { markOnboardingSeen(username); setShowOnboarding(false) }
  const aiOff = (config as { ai_enabled?: boolean }).ai_enabled === false

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-tecnia-bg text-tecnia-ink dark:bg-slate-950 dark:text-slate-100">
      <a href="#contenuto" className="skip-link">Vai al contenuto</a>
      <div className="orb -left-32 -top-40 h-[500px] w-[500px] bg-[radial-gradient(circle,#ff6b00,transparent_70%)]" aria-hidden="true" />
      {config.maintenance_message && (
        <div role="status" className="relative z-10 bg-orange-50 px-4 py-2 text-center text-sm text-tecnia-primary dark:bg-orange-950/40">{config.maintenance_message}</div>
      )}
      {aiOff && (
        <div role="status" className="relative z-10 flex items-center justify-center gap-2 bg-amber-100 px-4 py-2 text-center text-sm font-medium text-amber-900 dark:bg-amber-950 dark:text-amber-100">
          <span className="material-symbols-outlined text-[18px]" aria-hidden="true">pause_circle</span>
          Le funzioni AI sono in pausa per manutenzione: puoi consultare i tuoi progetti, ma generazione e chat tornano più tardi.
        </div>
      )}
      <SessionBanner />
      <nav className="sticky top-0 z-40 border-b border-tecnia-line/60 bg-white/80 backdrop-blur dark:bg-slate-900/80" aria-label="Navigazione principale">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-5">
            <Link to="/app" aria-label="AI-DB-Creator, torna ai progetti"><Logo size={34} /></Link>
            <div className="hidden items-center gap-1 sm:flex">
              {authenticated && <NavLink to="/app" end className={navCls}>Progetti</NavLink>}
              <NavLink to="/app/examples" className={navCls}>Esempi</NavLink>
              {authenticated && (<>
                {config.research_mode && <NavLink to="/app/benchmark" className={navCls}>Benchmark</NavLink>}
                {config.research_mode && <NavLink to="/app/studio" className={navCls}>Studio</NavLink>}
                {canResearch && <NavLink to="/app/ricerca" className={navCls}>Ricerca</NavLink>}
                {isAdmin && <NavLink to="/app/admin" className={navCls}>Admin</NavLink>}
                {isAdmin && <NavLink to="/app/settings" className={navCls}>Modelli</NavLink>}
              </>)}
              <NavLink to="/app/help" className={navCls}>Aiuto</NavLink>
            </div>
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

      <main id="contenuto" tabIndex={-1} className="relative z-10 mx-auto outline-none w-full max-w-7xl flex-1 p-4 sm:p-6 lg:p-8">
        <Routes>
          <Route index element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="projects/:id" element={<RequireAuth><ProjectPage /></RequireAuth>} />
          <Route path="shared/:token" element={<SharedProjectPage />} />
          <Route path="examples" element={<ExamplesPage />} />
          <Route path="examples/:name" element={<ExampleDetailPage />} />
          <Route path="login" element={<AuthEntry mode="login" />} />
          <Route path="register" element={<AuthEntry mode="register" />} />
          <Route path="benvenuto" element={<RequireAuth><OnboardingPage /></RequireAuth>} />
          <Route path="privacy" element={<LegalPage kind="privacy" />} />
          <Route path="cookie" element={<LegalPage kind="cookie" />} />
          <Route path="help" element={<HelpPage />} />
          <Route path="settings" element={<RequireAuth><RequireAdmin><SettingsPage /></RequireAdmin></RequireAuth>} />
          <Route path="admin" element={<RequireAuth><RequireAdmin><AdminPage /></RequireAdmin></RequireAuth>} />
          {config.research_mode && <Route path="benchmark" element={<RequireAuth><BenchmarkPage /></RequireAuth>} />}
          {config.research_mode && <Route path="studio" element={<RequireAuth><StudyPage /></RequireAuth>} />}
          {config.research_mode && <Route path="ricerca" element={<RequireAuth><ResearchPage /></RequireAuth>} />}
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </main>
      {projectId && <ProgressBar projectId={projectId} />}
      <LLMStatus />
      <OnboardingDialog open={showOnboarding} onClose={closeOnboarding} />
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
