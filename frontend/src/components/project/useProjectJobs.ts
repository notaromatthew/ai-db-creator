import { useQuery } from '@tanstack/react-query'
import { listJobs } from '@/api/projects'
import type { Job, JobKind } from '@/types'

export const isActive = (job?: Job | null) => !!job && (job.status === 'queued' || job.status === 'running')

/**
 * Lavori del progetto. Finché ce n'è uno attivo l'elenco si aggiorna da solo: così l'avanzamento
 * si riprende anche dopo aver chiuso o ricaricato la pagina.
 */
export function useProjectJobs(projectId: string, enabled = true) {
  const query = useQuery<Job[]>({
    queryKey: ['jobs', projectId],
    queryFn: () => listJobs(projectId),
    enabled: enabled && !!projectId,
    refetchInterval: (q) => ((q.state.data ?? []).some(isActive) ? 2000 : false),
    retry: false,
  })
  const jobs = query.data ?? []
  const latest = (kind: JobKind) => jobs.find((j) => j.kind === kind)
  return {
    jobs,
    activeJob: (kind: JobKind) => jobs.find((j) => j.kind === kind && isActive(j)),
    latest,
    refetch: query.refetch,
  }
}
