import request from './request'
import type { ErrorRecord } from '@/types'

export const getErrorList = (params: {
  page: number
  page_size: number
  mastered?: boolean
  knowledge_id?: string
}) => {
  return request.get<{
    items: ErrorRecord[]
    total: number
    page: number
    page_size: number
  }>('/errors/list', { params })
}

export const markMastered = (questionId: string) => {
  return request.post(`/errors/mark-mastered/${questionId}`)
}

export const unmarkMastered = (questionId: string) => {
  return request.post(`/errors/unmark-mastered/${questionId}`)
}

export const removeError = (questionId: string) => {
  return request.delete(`/errors/${questionId}`)
}

export const startErrorPractice = (data: {
  knowledge_id?: string
  question_count: number
}) => {
  return request.post('/errors/start-practice', data)
}

export const getErrorStats = () => {
  return request.get<{
    total_errors: number
    mastered_count: number
    knowledge_stats: { _id: string; count: number }[]
  }>('/errors/stats')
}
