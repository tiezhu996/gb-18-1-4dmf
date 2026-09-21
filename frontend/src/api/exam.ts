import request from './request'
import type { Question, ExamResult, ExamSession } from '@/types'

export const startExam = (data: {
  name: string
  subject_id: string
  question_count: number
  duration_minutes: number
}) => {
  return request.post<ExamSession>('/exam/start', data)
}

export const getExam = (sessionId: string) => {
  return request.get<ExamSession>(`/exam/${sessionId}`)
}

export const saveExamAnswers = (sessionId: string, answers: Record<string, any>) => {
  return request.put<{
    saved: boolean
    is_submitted: boolean
    remaining_seconds: number
  }>(`/exam/${sessionId}/answers`, { answers })
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
