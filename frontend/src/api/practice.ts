import request from './request'
import type { Question, PracticeResult } from '@/types'

export const startPractice = (data: {
  mode: string
  subject_id: string
  knowledge_ids?: string[]
  question_count: number
  difficulty?: string
}) => {
  return request.post<{
    session_id: string
    current_question: Question
    progress: { current: number; total: number; correct: number; accuracy: number }
  }>('/practice/start', data)
}

export const submitAnswer = (sessionId: string, questionId: string, userAnswer: any) => {
  return request.post<PracticeResult>('/practice/submit', {
    session_id: sessionId,
    question_id: questionId,
    user_answer: userAnswer
  })
}

export const navigateQuestion = (sessionId: string, direction: 'prev' | 'next') => {
  return request.get<Question>(`/practice/navigate/${sessionId}/${direction}`)
}

export const getSessionProgress = (sessionId: string) => {
  return request.get<{
    current: number
    total: number
    correct: number
    accuracy: number
    answers: Record<string, any>
  }>(`/practice/progress/${sessionId}`)
}
