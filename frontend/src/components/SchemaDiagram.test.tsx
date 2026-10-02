import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import SchemaDiagram from './SchemaDiagram'
import { NormalizedSchema } from '@/types'

// Mock reactflow so jsdom doesn't choke on DOM measurements
vi.mock('reactflow', async () => {
  const actual: any = await vi.importActual('reactflow')
  return {
    ...actual,
    default: ({ nodes, edges }: any) => (
      <div data-testid="mock-reactflow">
        <div data-testid="nodes-count">{nodes.length}</div>
        <div data-testid="edges-count">{edges.length}</div>
        {nodes.map((n: any) => (
          <div key={n.id} data-testid={`node-${n.id}`}>
            {n.data.label}
          </div>
        ))}
      </div>
    ),
    Controls: () => <div data-testid="mock-controls" />,
    Background: () => <div data-testid="mock-background" />,
    MiniMap: () => <div data-testid="mock-minimap" />,
    Panel: ({ children }: any) => <div data-testid="mock-panel">{children}</div>,
  }
})

describe('SchemaDiagram', () => {
  it('renders tables and discovers relationships even when columns are omitted in rel def', () => {
    const testSchema: NormalizedSchema = {
      tables: [
        {
          name: 'clienti',
          columns: [
            { name: 'cli_id', data_type: 'INTEGER', is_primary_key: true },
            { name: 'nome', data_type: 'TEXT' },
          ],
        },
        {
          name: 'ordini',
          columns: [
            { name: 'id', data_type: 'INTEGER', is_primary_key: true },
            {
              name: 'cli_id',
              data_type: 'INTEGER',
              is_foreign_key: true,
              foreign_key_table: 'clienti',
              foreign_key_column: 'cli_id',
            },
          ],
        },
      ],
      relationships: [
        {
          from_table: 'ordini',
          from_column: '',
          to_table: 'clienti',
          to_column: '',
          type: 'one_to_many',
        },
      ],
    }

    render(<SchemaDiagram schema={testSchema} />)

    expect(screen.getByTestId('nodes-count')).toHaveTextContent('2')
    expect(screen.getByTestId('edges-count')).toHaveTextContent('1')
    expect(screen.getByTestId('node-clienti')).toHaveTextContent('clienti')
    expect(screen.getByTestId('node-ordini')).toHaveTextContent('ordini')
  })

  it('renders fallback when no tables are present', () => {
    const emptySchema: NormalizedSchema = {
      tables: [],
      relationships: [],
    }
    render(<SchemaDiagram schema={emptySchema} />)
    expect(screen.getByText('Nessuna tabella da mostrare')).toBeInTheDocument()
  })
})
