export interface StudyContext {
  participant_id: string
  arm: 'manual' | 'ai_only' | 'ai_interface'
}

const KEY = 'aidb.study.context.v1'

export const readStudyContext = (): StudyContext | null => {
  try {
    const value = JSON.parse(window.localStorage.getItem(KEY) || 'null')
    if (!value || !value.participant_id || !['manual', 'ai_only', 'ai_interface'].includes(value.arm)) return null
    return value
  } catch {
    return null
  }
}

export const writeStudyContext = (value: StudyContext | null) => {
  try {
    if (value) window.localStorage.setItem(KEY, JSON.stringify(value))
    else window.localStorage.removeItem(KEY)
  } catch {
    /* Lo studio resta utilizzabile, ma il collegamento tra schede non è disponibile. */
  }
}

export const studyRunContext = (): Record<string, string> => {
  const value = typeof window === 'undefined' ? null : readStudyContext()
  return value ? { condition: value.arm, session_id: value.participant_id, participant_id: value.participant_id } : {}
}
