import { useState } from 'react'

interface Props {
  onGenerate: (prompt: string) => void
  loading: boolean
  error?: string
}

export default function PromptInput({ onGenerate, loading, error }: Props) {
  const [prompt, setPrompt] = useState('')

  const handleSubmit = () => {
    if (!prompt.trim()) return
    onGenerate(prompt)
    setPrompt('')
  }

  return (
    <div className="bg-white dark:bg-gray-800 p-4 rounded shadow mb-6">
      <h3 className="font-semibold mb-2">Generate Schema</h3>
      <textarea
        placeholder="Describe your database requirements..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        className="w-full p-2 border rounded h-24 dark:bg-gray-700 dark:text-white dark:border-gray-600"
        disabled={loading}
      />
      <button
        onClick={handleSubmit}
        disabled={!prompt.trim() || loading}
        className="bg-blue-600 text-white px-4 py-2 rounded mt-2 disabled:opacity-50"
      >
        {loading ? 'Generating...' : 'Generate'}
      </button>
      {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
    </div>
  )
}
