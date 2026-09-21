import request from './request'
import type { Question, ExamResult } from '@/types'

export interface ExamState {
  session_id: string
  name: string
  total_questions: number
  duration_minutes: number
  is_submitted: boolean
  remaining_seconds: number
  start_time?: string
  saved_answers?: Record<string, any>
  questions?: Question[]
}

export const startExam = (data: {
  name: string
  subject_id: string
  question_count: number
  duration_minutes: number
}) => {
  return request.post<{
    session_id: string
    name: string
    total_questions: number
    duration_minutes: number
    start_time: string
    questions: Question[]
  }>('/exam/start', data)
}

export const getExamState = (sessionId: string) => {
  return request.get<ExamState>(`/exam/${sessionId}`)
}

export const saveExamAnswers = (
  sessionId: string,
  answers: Record<string, any>,
  silent: boolean = false
) => {
  return request.post<{ is_submitted: boolean; remaining_seconds: number }>(
    '/exam/save',
    { session_id: sessionId, answers },
    { _silent: silent } as any
  )
}

export const submitExam = (sessionId: string, answers: Record<string, any>) => {
  return request.post<ExamResult>('/exam/submit', {
    session_id: sessionId,
    answers
  })
}

export const getExamResult = (sessionId: string) => {
  return request.get<ExamResult>(`/exam/result/${sessionId}`)
}

export const getExamHistory = (limit: number = 20) => {
  return request.get<ExamResult[]>(`/exam/history/list?limit=${limit}`)
}
