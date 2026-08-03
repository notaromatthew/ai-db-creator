import ReactFlow, { Controls, Background, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import { NormalizedSchema } from '@/types'

interface Props {
  schema: NormalizedSchema
}

interface TableNodeProps {
  data: {
    label: string
    columns: { name: string; type: string; pk: boolean }[]
  }
}

const TableNode = ({ data }: TableNodeProps) => {
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg p-3 shadow-lg min-w-[150px]">
      <div className="font-bold text-center mb-2 text-blue-600 dark:text-blue-400">{data.label}</div>
      <table className="w-full text-xs">
        <tbody>
          {data.columns.map((col) => (
            <tr key={col.name}>
              <td className="pr-2">
                <Handle
                  type="source"
                  position={Position.Right}
                  id={col.name}
                  style={{ display: 'none' }}
                />
                {col.pk && <span className="text-yellow-500">🔑 </span>}
                {col.name}
              </td>
              <td className="text-gray-500 dark:text-gray-400">{col.type}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const nodeTypes = {
  tableNode: TableNode,
}

export default function SchemaDiagram({ schema }: Props) {
  if (!schema.tables.length) {
    return <p className="text-gray-500 text-center py-8">No tables to display</p>
  }

  const nodes = schema.tables.map((table, i) => ({
    id: table.name,
    type: 'tableNode',
    position: { x: (i % 4) * 280, y: Math.floor(i / 4) * 220 },
    data: {
      label: table.name,
      columns: table.columns.map((c) => ({
        name: c.name,
        type: c.data_type,
        pk: c.is_primary_key,
      })),
    },
  }))

  const edges = schema.relationships.flatMap((rel) => {
    const fromTable = schema.tables.find((t) => t.name === rel.from_table)
    const toTable = schema.tables.find((t) => t.name === rel.to_table)
    if (!fromTable || !toTable) return []

    return [{
      id: `${rel.from_table}-${rel.to_table}-${rel.from_column}`,
      source: rel.from_table,
      target: rel.to_table,
      sourceHandle: rel.from_column,
      targetHandle: rel.to_column,
      label: rel.type === 'one_to_many' ? 'N' : rel.type === 'many_to_many' ? 'M:N' : '1:1',
      type: 'smoothstep',
      animated: true,
      style: { stroke: '#6366f1', strokeWidth: 2 },
      labelStyle: { fill: '#6366f1', fontSize: 12, fontWeight: 'bold' },
    }]
  })

  return (
    <div className="h-[500px] w-full border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-900">
      {edges.length === 0 && (
        <div className="absolute top-2 left-2 bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 text-xs px-2 py-1 rounded z-10">
          No relationships defined between tables
        </div>
      )}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        attributionPosition="bottom-left"
      >
        <Controls />
        <Background />
      </ReactFlow>
    </div>
  )
}