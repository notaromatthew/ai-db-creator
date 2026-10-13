import { api } from './client'
import type { Job, JobRequest, SchemaVersionList, QueryHistoryItem, NormalizedSchema } from '@/types'

/** Funzioni per i lavori in coda, le versioni dello schema, la cronologia delle query e il dialetto. */

export const createJob = (projectId: string, body: JobRequest): Promise<Job> => api.post(`/projects/${projectId}/jobs`, body)

export const listJobs = async (projectId: string, status?: string): Promise<Job[]> => {
  const res = await api.get(`/projects/${projectId}/jobs${status ? `?status=${encodeURIComponent(status)}` : ''}`)
  return res?.jobs ?? []
}

export const getJob = (projectId: string, jobId: string): Promise<Job> => api.get(`/projects/${projectId}/jobs/${jobId}`)

export const cancelJob = (projectId: string, jobId: string): Promise<Job> => api.post(`/projects/${projectId}/jobs/${jobId}/cancel`, {})

export const listSchemaVersions = (projectId: string): Promise<SchemaVersionList> => api.get(`/projects/${projectId}/schema/versions`)

export const restoreSchemaVersion = (projectId: string, version: number): Promise<{ schema: NormalizedSchema; schema_version: number; restored_from: number }> =>
  api.post(`/projects/${projectId}/schema/versions/${version}/restore`, {})

export const listQueries = async (projectId: string): Promise<QueryHistoryItem[]> => {
  const res = await api.get(`/projects/${projectId}/queries`)
  return res?.queries ?? []
}

export const setProjectDialect = (projectId: string, dialect: string): Promise<{ target_dialect: string }> =>
  api.put(`/projects/${projectId}/dialect`, { dialect })
