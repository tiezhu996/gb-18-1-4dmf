import request from './request'
import type { Question, ExamResult } from '@/types'

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
