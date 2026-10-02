import React, { useMemo } from 'react'
import ReactFlow, {
  Controls,
  Background,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  EdgeLabelRenderer,
  getSmoothStepPath,
  EdgeProps,
  Panel,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { NormalizedSchema, ColumnDef, TableDef } from '@/types'

interface Props {
  schema: NormalizedSchema
}

interface TableNodeData {
  label: string
  description?: string
  columns: ColumnDef[]
}

interface TableNodeProps {
  data: TableNodeData
}

// Custom UML Table Node according to standard Relational UML specifications
const UMLTableNode = ({ data }: TableNodeProps) => {
  return (
    <div className="bg-white dark:bg-slate-900 border-2 border-slate-300 dark:border-slate-700 rounded-lg shadow-md min-w-[240px] max-w-[340px] font-sans text-xs overflow-hidden transition-all hover:shadow-xl hover:border-indigo-400 dark:hover:border-indigo-500">
      {/* Node-level connection handles for fallback attachment */}
      <Handle
        type="target"
        position={Position.Left}
        id="__node_left"
        className="!w-2 !h-2 !bg-indigo-500 !border !border-white dark:!border-slate-900"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="__node_right"
        className="!w-2 !h-2 !bg-indigo-500 !border !border-white dark:!border-slate-900"
      />
      <Handle
        type="target"
        position={Position.Top}
        id="__node_top"
        className="!w-2 !h-2 !bg-indigo-500 !border !border-white dark:!border-slate-900"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="__node_bottom"
        className="!w-2 !h-2 !bg-indigo-500 !border !border-white dark:!border-slate-900"
      />

      {/* UML Class Header */}
      <div className="bg-gradient-to-r from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-850 px-3 py-2 border-b-2 border-slate-300 dark:border-slate-700 text-center">
        <div className="text-[10px] font-mono tracking-widest text-slate-500 dark:text-slate-400 uppercase select-none">
          «entity»
        </div>
        <div className="font-bold text-sm text-slate-900 dark:text-white flex items-center justify-center gap-1.5">
          <span>🗄️</span>
          <span className="font-mono tracking-tight">{data.label}</span>
        </div>
        {data.description && (
          <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate mt-0.5" title={data.description}>
            {data.description}
          </div>
        )}
      </div>

      {/* UML Attributes Compartment */}
      <div className="p-1.5 space-y-0.5 divide-y divide-slate-100 dark:divide-slate-800/60">
        {data.columns.map((col) => {
          const isPk = Boolean(col.is_primary_key)
          const isFk = Boolean(col.is_foreign_key || col.foreign_key_table)

          return (
            <div
              key={col.name}
              className={`relative px-2 py-1 flex items-center justify-between gap-2 group transition-colors rounded ${
                isPk
                  ? 'bg-amber-50/70 dark:bg-amber-950/20 font-semibold'
                  : isFk
                  ? 'bg-indigo-50/50 dark:bg-indigo-950/20'
                  : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
              }`}
            >
              {/* Target handle on left for FK incoming references */}
              <Handle
                type="target"
                position={Position.Left}
                id={`${col.name}-target`}
                className="!w-1.5 !h-1.5 !bg-indigo-400 !border-0 opacity-40 group-hover:opacity-100 -left-1"
              />

              {/* Source handle on right for outgoing FK references */}
              <Handle
                type="source"
                position={Position.Right}
                id={`${col.name}-source`}
                className="!w-1.5 !h-1.5 !bg-indigo-600 !border-0 opacity-40 group-hover:opacity-100 -right-1"
              />

              <div className="flex items-center gap-1.5 min-w-0">
                {/* UML Modifier / Stereotype Badges */}
                {isPk ? (
                  <span
                    className="px-1 py-0.2 bg-amber-500/20 text-amber-700 dark:text-amber-300 rounded text-[9px] font-mono font-bold"
                    title="Primary Key"
                  >
                    🔑 PK
                  </span>
                ) : isFk ? (
                  <span
                    className="px-1 py-0.2 bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 rounded text-[9px] font-mono font-bold"
                    title={`Foreign Key -> ${col.foreign_key_table || ''}`}
                  >
                    🔗 FK
                  </span>
                ) : (
                  <span className="text-slate-400 font-mono text-[10px] w-4 text-center">+</span>
                )}

                {/* Column Name */}
                <span
                  className={`font-mono truncate ${
                    isPk
                      ? 'text-amber-900 dark:text-amber-200 underline decoration-amber-500/40'
                      : isFk
                      ? 'text-indigo-900 dark:text-indigo-200 italic'
                      : 'text-slate-800 dark:text-slate-200'
                  }`}
                  title={col.name}
                >
                  {col.name}
                </span>
              </div>

              {/* Column Type and Constraints */}
              <div className="flex items-center gap-1 shrink-0 font-mono text-[10px] text-slate-500 dark:text-slate-400">
                <span className="text-indigo-600 dark:text-indigo-400 font-medium">{col.data_type}</span>
                {col.is_not_null && <span className="text-rose-500 dark:text-rose-400 text-[9px]" title="NOT NULL">*</span>}
                {col.is_unique && !isPk && (
                  <span className="text-[9px] px-0.5 bg-slate-200 dark:bg-slate-700 rounded text-slate-600 dark:text-slate-300">
                    UQ
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Custom UML Edge Component with Multiplicities (e.g. 1 ──────► 0..*)
const UMLEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetPosition,
    targetX,
    targetY,
    borderRadius: 8,
  })

  // UML Multiplicities:
  // Source (Child with FK) has multiplicity 0..* (or 1..* if NOT NULL, or 1 if 1:1)
  // Target (Parent with PK) has multiplicity 1
  const sourceMultiplicity = data?.sourceMultiplicity || '0..*'
  const targetMultiplicity = data?.targetMultiplicity || '1'
  const relationshipLabel = data?.relationshipLabel || ''

  // Positions for multiplicity labels close to endpoints
  const isTargetRight = targetX > sourceX
  const sourceLabelOffset = isTargetRight ? 24 : -24
  const targetLabelOffset = isTargetRight ? -24 : 24

  return (
    <>
      <path
        id={id}
        style={{ ...style, strokeWidth: 2, stroke: '#6366f1' }}
        className="react-flow__edge-path"
        d={edgePath}
        markerEnd={markerEnd}
      />
      <EdgeLabelRenderer>
        {/* Source Multiplicity (near Child / FK table) */}
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${sourceX + sourceLabelOffset}px, ${sourceY - 14}px)`,
            pointerEvents: 'none',
          }}
          className="bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-200 font-mono text-[10px] font-bold px-1.5 py-0.5 rounded shadow-xs border border-indigo-300 dark:border-indigo-800 z-10"
        >
          {sourceMultiplicity}
        </div>

        {/* Target Multiplicity (near Parent / PK table) */}
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${targetX + targetLabelOffset}px, ${targetY - 14}px)`,
            pointerEvents: 'none',
          }}
          className="bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-mono text-[10px] font-bold px-1.5 py-0.5 rounded shadow-xs border border-slate-300 dark:border-slate-700 z-10"
        >
          {targetMultiplicity}
        </div>

        {/* Center FK Link Pill */}
        {relationshipLabel && (
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="bg-white/95 dark:bg-slate-900/95 text-slate-700 dark:text-slate-300 font-mono text-[9px] px-2 py-0.5 rounded-full shadow border border-indigo-200 dark:border-indigo-900/80 cursor-default hover:border-indigo-500 transition-colors"
            title={relationshipLabel}
          >
            {relationshipLabel}
          </div>
        )}
      </EdgeLabelRenderer>
    </>
  )
}

const nodeTypes = {
  tableNode: UMLTableNode,
}

const edgeTypes = {
  umlEdge: UMLEdge,
}

export default function SchemaDiagram({ schema }: Props) {
  if (!schema.tables || !schema.tables.length) {
    return <p className="text-gray-500 text-center py-8">Nessuna tabella da mostrare</p>
  }

  // 1. Build Nodes with intelligent grid layout
  const nodes = useMemo(() => {
    const colsCount = Math.min(3, Math.max(1, Math.ceil(Math.sqrt(schema.tables.length))))
    const xGap = 340
    const yBaseGap = 50

    // Keep track of column vertical offsets to prevent overlapping cards with varying rows
    const colYOffsets = Array(colsCount).fill(30)

    return schema.tables.map((table, i) => {
      const colIndex = i % colsCount
      const posX = colIndex * xGap + 40
      const posY = colYOffsets[colIndex]

      // Approximate height: header ~60px + ~28px per column row
      const estimatedHeight = 70 + table.columns.length * 28
      colYOffsets[colIndex] += estimatedHeight + yBaseGap

      return {
        id: table.name,
        type: 'tableNode',
        position: { x: posX, y: posY },
        data: {
          label: table.name,
          description: table.description,
          columns: table.columns,
        },
      }
    })
  }, [schema.tables])

  // 2. Build Edges with UML relations
  const edges = useMemo(() => {
    const tableLookup = new Map<string, TableDef>()
    schema.tables.forEach((t) => tableLookup.set(t.name.toLowerCase(), t))

    interface ResolvedRel {
      fromTable: string
      fromCol: string
      toTable: string
      toCol: string
      type: string
    }

    const resolvedRels: ResolvedRel[] = []
    const seenRelKeys = new Set<string>()

    // A) Process explicitly declared relationships
    if (schema.relationships) {
      for (const rel of schema.relationships) {
        const fromT = tableLookup.get(rel.from_table.toLowerCase())
        const toT = tableLookup.get(rel.to_table.toLowerCase())
        if (!fromT || !toT) continue

        // Discover from_column if empty
        let fromColName = rel.from_column?.trim() || ''
        if (!fromColName) {
          const fkCol = fromT.columns.find(
            (c) =>
              c.foreign_key_table?.toLowerCase() === toT.name.toLowerCase() ||
              c.name.toLowerCase().includes(toT.name.toLowerCase()) ||
              c.name.toLowerCase().startsWith('id_') ||
              c.name.toLowerCase().endsWith('_id')
          )
          fromColName = fkCol ? fkCol.name : ''
        }

        // Discover to_column if empty
        let toColName = rel.to_column?.trim() || ''
        if (!toColName) {
          const pkCol = toT.columns.find((c) => c.is_primary_key)
          toColName = pkCol ? pkCol.name : (toT.columns[0]?.name || 'id')
        }

        const key = `${fromT.name}.${fromColName}->${toT.name}.${toColName}`
        if (!seenRelKeys.has(key)) {
          seenRelKeys.add(key)
          resolvedRels.push({
            fromTable: fromT.name,
            fromCol: fromColName,
            toTable: toT.name,
            toCol: toColName,
            type: rel.type || 'one_to_many',
          })
        }
      }
    }

    // B) Also supplement from column foreign_key_table attributes if not present
    for (const table of schema.tables) {
      for (const col of table.columns) {
        if (col.is_foreign_key && col.foreign_key_table) {
          const targetTable = tableLookup.get(col.foreign_key_table.toLowerCase())
          if (!targetTable) continue

          const targetPk = targetTable.columns.find((c) => c.is_primary_key)?.name || col.foreign_key_column || 'id'
          const key = `${table.name}.${col.name}->${targetTable.name}.${targetPk}`
          if (!seenRelKeys.has(key)) {
            seenRelKeys.add(key)
            resolvedRels.push({
              fromTable: table.name,
              fromCol: col.name,
              toTable: targetTable.name,
              toCol: targetPk,
              type: 'one_to_many',
            })
          }
        }
      }
    }

    // C) Convert resolved relationships into ReactFlow edges with UML semantics
    return resolvedRels.map((rel, index) => {
      // In UML: arrow points from Dependent/Child (fromTable with FK) to Parent (toTable with PK)
      // Multiplicity: Child side is 0..* (or *), Parent side is 1
      let sourceMultiplicity = '0..*'
      let targetMultiplicity = '1'

      if (rel.type === 'one_to_one') {
        sourceMultiplicity = '1'
        targetMultiplicity = '1'
      } else if (rel.type === 'many_to_many') {
        sourceMultiplicity = '*'
        targetMultiplicity = '*'
      } else {
        // one_to_many
        sourceMultiplicity = '0..*'
        targetMultiplicity = '1'
      }

      const sourceHandleId = rel.fromCol ? `${rel.fromCol}-source` : '__node_right'
      const targetHandleId = rel.toCol ? `${rel.toCol}-target` : '__node_left'

      const relationshipLabel = rel.fromCol && rel.toCol
        ? `${rel.fromTable}.${rel.fromCol} → ${rel.toTable}.${rel.toCol}`
        : `${rel.fromTable} → ${rel.toTable}`

      return {
        id: `uml-edge-${rel.fromTable}-${rel.toTable}-${index}`,
        source: rel.fromTable,
        target: rel.toTable,
        sourceHandle: sourceHandleId,
        targetHandle: targetHandleId,
        type: 'umlEdge',
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: '#6366f1',
        },
        data: {
          sourceMultiplicity,
          targetMultiplicity,
          relationshipLabel,
        },
      }
    })
  }, [schema])

  return (
    <div className="h-[600px] w-full border border-slate-200 dark:border-slate-800 rounded-xl bg-slate-50/70 dark:bg-slate-950 overflow-hidden relative shadow-inner">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={1.5}
        attributionPosition="bottom-left"
      >
        <Controls className="!bg-white dark:!bg-slate-900 !border !border-slate-200 dark:!border-slate-800 !rounded-lg !shadow-sm" />
        <Background variant={BackgroundVariant.Dots} gap={20} size={1.2} className="opacity-40" />
        <MiniMap
          nodeColor={(node) => {
            return node.type === 'tableNode' ? '#6366f1' : '#cbd5e1'
          }}
          className="!bg-white/90 dark:!bg-slate-900/90 !border !border-slate-200 dark:!border-slate-800 !rounded-lg !shadow-md"
        />

        {/* UML Legend Panel */}
        <Panel position="top-right" className="bg-white/90 dark:bg-slate-900/90 backdrop-blur-xs border border-slate-200 dark:border-slate-800 rounded-lg p-3 text-[11px] shadow-sm font-sans space-y-1.5 max-w-[220px]">
          <div className="font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1">
            <span>📐</span> Notazione UML Relazionale
          </div>
          <div className="text-slate-600 dark:text-slate-400 space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-amber-600 dark:text-amber-400 font-bold">🔑 PK</span>
              <span>Chiave Primaria</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">🔗 FK</span>
              <span>Chiave Esterna</span>
            </div>
            <div className="flex items-center gap-2 font-mono text-[10px] text-indigo-600 dark:text-indigo-400">
              <span className="font-bold">0..* ──► 1</span>
              <span className="text-slate-500 font-sans">Molteplicità (1:N)</span>
            </div>
          </div>
          <div className="pt-1 border-t border-slate-200 dark:border-slate-800 text-[10px] text-slate-400">
            Archi: <span className="font-bold text-slate-700 dark:text-slate-300">{edges.length}</span> relazioni
          </div>
        </Panel>
      </ReactFlow>
    </div>
  )
}