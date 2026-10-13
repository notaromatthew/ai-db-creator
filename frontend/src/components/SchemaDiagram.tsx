import ReactFlow, { Controls, Background, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import { NormalizedSchema } from '@/types'

interface Props {
  schema: NormalizedSchema
}

interface TableNodeProps {
  data: {
    label: string
    columns: { name: string; type: string; pk: boolean; fk: boolean }[]
  }
}

const TableNode = ({ data }: TableNodeProps) => {
  return (
    <div className="min-w-[200px] overflow-hidden rounded-xl border border-tecnia-line bg-white text-xs shadow-glass dark:border-slate-600 dark:bg-slate-900">
      <div className="bg-slate-100 px-3 py-2 text-center font-headline text-sm font-bold text-tecnia-primary dark:bg-slate-800 dark:text-orange-300">{data.label}</div>
      <ul>
        {data.columns.map((col) => (
          <li key={col.name} className="relative flex items-center gap-2 px-3 py-1.5">
            <Handle type="target" position={Position.Left} id={col.name} style={{ opacity: 0 }} />
            <Handle type="source" position={Position.Right} id={col.name} style={{ opacity: 0 }} />
            <span className="w-5 font-bold text-fuchsia-700 dark:text-fuchsia-300">{col.pk ? 'PK' : col.fk ? 'FK' : ''}</span>
            <span className="flex-1">{col.name}</span>
            <span className="text-tecnia-muted dark:text-slate-400">{col.type.toLowerCase()}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

const nodeTypes = {
  tableNode: TableNode,
}

export default function SchemaDiagram({ schema }: Props) {
  if (!schema.tables.length) {
    return <p className="py-8 text-center text-slate-500">Nessuna tabella da mostrare.</p>
  }

  const nodes = schema.tables.map((table, i) => ({
    id: table.name,
    type: 'tableNode',
    position: { x: (i % 3) * 330, y: Math.floor(i / 3) * 280 },
    data: {
      label: table.name,
      columns: table.columns.map((c) => ({
        name: c.name,
        type: c.data_type,
        pk: !!c.is_primary_key,
        fk: !!c.is_foreign_key,
      })),
    },
  }))

  const edges = schema.relationships.flatMap((rel) => {
    const fromTable = schema.tables.find((t) => t.name === rel.from_table)
    const toTable = schema.tables.find((t) => t.name === rel.to_table)
    if (!fromTable || !toTable) return []
    const hasHandle = (t: typeof fromTable, col: string) => t.columns.some((c) => c.name === col)

    return [{
      id: `${rel.from_table}-${rel.to_table}-${rel.from_column}`,
      source: rel.from_table,
      target: rel.to_table,
      sourceHandle: hasHandle(fromTable, rel.from_column) ? rel.from_column : undefined,
      targetHandle: hasHandle(toTable, rel.to_column) ? rel.to_column : undefined,
      label: rel.type === 'one_to_many' ? '1 : N' : rel.type === 'many_to_many' ? 'N : M' : '1 : 1',
      type: 'smoothstep',
      style: { stroke: '#b20088', strokeWidth: 2 },
      labelStyle: { fill: '#b20088', fontSize: 12, fontWeight: 700 },
    }]
  })

  return (
    <div className="relative h-[min(560px,65vh)] w-full overflow-hidden rounded-2xl border border-tecnia-line bg-slate-50 dark:border-slate-700 dark:bg-slate-900" role="img" aria-label="Diagramma UML dello schema con tabelle e relazioni">
      {edges.length === 0 && (
        <div className="absolute left-2 top-2 z-10 rounded bg-amber-100 px-2 py-1 text-xs text-amber-800 dark:bg-amber-900 dark:text-amber-200">
          Nessuna relazione definita tra le tabelle
        </div>
      )}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        nodesConnectable={false}
        attributionPosition="bottom-left"
      >
        <Controls showInteractive={false} />
        <Background gap={20} size={1} color="#e2bfb0" />
      </ReactFlow>
    </div>
  )
}
