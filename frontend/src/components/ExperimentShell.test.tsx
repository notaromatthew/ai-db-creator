import { render, screen, waitFor } from '@testing-library/react'
import { vi, describe, it, expect } from 'vitest'
import ExperimentShell, { useExperiment } from './ExperimentShell'
import { api } from '../api/client'

function Probe() {
  const { can } = useExperiment()
  return <div>{['ai_generate','chat','edit','import_sql'].filter(can).join(',')}</div>
}

describe.each([
  ['manual', ['project_view','edit','import_sql'], 'edit,import_sql'],
  ['ai_only', ['project_view','ai_generate','populate'], 'ai_generate'],
  ['ai_interface', ['project_view','ai_generate','populate','chat','edit','import_sql'], 'ai_generate,chat,edit,import_sql'],
])('ExperimentShell %s', (_arm, capabilities, expected) => {
  it('exposes only server capabilities with neutral condition copy', async () => {
    vi.spyOn(api, 'get').mockResolvedValueOnce({session_id:`s-${_arm}`,project_id:'p1', status:'active', condition:_arm, deadline_at:new Date(Date.now()+60000).toISOString(), capabilities}).mockResolvedValue({session_id:`s-${_arm}`,next_sequence:1})
    vi.spyOn(api, 'post').mockResolvedValue({status:'logged'})
    render(<ExperimentShell projectId="p1"><Probe /></ExperimentShell>)
    await waitFor(() => expect(screen.getByText(expected)).toBeInTheDocument())
    expect(screen.getByText(/Percorso assegnato/)).toBeInTheDocument()
    expect(screen.queryByText(_arm)).not.toBeInTheDocument()
    vi.restoreAllMocks()
  })
})
