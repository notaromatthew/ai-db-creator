import { useNavigate } from 'react-router-dom'
import { OnboardingSteps, markOnboardingSeen } from '@/components/Onboarding'
import { useAuth } from '@/context/KeycloakContext'

/** Presentazione in tre schermate, rivedibile in qualsiasi momento da /app/benvenuto. */
export default function OnboardingPage() {
  const navigate = useNavigate()
  const { username } = useAuth()
  const done = () => { markOnboardingSeen(username); navigate('/app') }
  return (
    <div className="glass mx-auto max-w-xl p-6 sm:p-8">
      <h1 className="mb-4 text-3xl font-bold tracking-tight">Come funziona</h1>
      <OnboardingSteps onFinish={done} finishLabel="Vai ai progetti" />
    </div>
  )
}
