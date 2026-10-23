import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ExpertReviewPage from './ExpertReviewPage'
import { expertApi } from '../api/expertClient'

vi.mock('../api/expertClient', () => ({
  expertApi: {
    listSchemas: vi.fn(),
    submitEvaluation: vi.fn(),
  },
}))

vi.mock('../context/KeycloakContext', () => ({
  useAuth: () => ({
    username: 'TestEvaluator',
    authenticated: true,
  }),
}))

const mockSchemas = [
  {
    code: 'S01',
    title: 'Schema S01',
    description: 'Gestione studenti e corsi universitari.',
    tables: [
      {
        name: 'students',
        columns: [
          {
            name: 'id',
            data_type: 'INTEGER',
            flags: ['PK', 'NN'],
            is_primary_key: true,
            is_unique: false,
            is_not_null: true,
            is_foreign_key: false,
          },
          {
            name: 'name',
            data_type: 'TEXT',
            flags: ['NN'],
            is_primary_key: false,
            is_unique: false,
            is_not_null: true,
            is_foreign_key: false,
          },
        ],
      },
    ],
    relationships: [],
    table_count: 1,
    column_count: 2,
    relationship_count: 0,
    raw_markdown: '# Schema S01\n\nTABLE students\n  - id (INTEGER) [PK, NN]\n  - name (TEXT) [NN]',
    has_evaluated: false,
  },
]

describe('ExpertReviewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('aidb_evaluator_name', 'TestEvaluator')
    vi.mocked(expertApi.listSchemas).mockResolvedValue(mockSchemas)
    vi.mocked(expertApi.submitEvaluation).mockResolvedValue({ status: 'saved' })
  })

  it('renders schema and submits evaluation with scores', async () => {
    render(<ExpertReviewPage />)

    expect(await screen.findByText('Schema S01')).toBeInTheDocument()
    expect(screen.getByText('TABLE')).toBeInTheDocument()
    expect(screen.getByText('students')).toBeInTheDocument()

    // Rate all 5 dimensions
    const scoreButtons = screen.getAllByRole('button', { name: '5' })
    for (const btn of scoreButtons) {
      await userEvent.click(btn)
    }

    // Click Salva
    const saveButton = screen.getByRole('button', { name: 'Salva' })
    expect(saveButton).not.toBeDisabled()
    await userEvent.click(saveButton)

    expect(expertApi.submitEvaluation).toHaveBeenCalledWith({
      evaluator_name: 'TestEvaluator',
      schema_code: 'S01',
      d1_3nf: 5,
      d2_naming: 5,
      d3_constraints: 5,
      d4_relationships: 5,
      d5_domain: 5,
      comment: undefined,
    })
  })
})
