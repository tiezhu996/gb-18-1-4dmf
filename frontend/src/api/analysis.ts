import request from './request'
import type { LearningOverview, AccuracyTrend, KnowledgeMastery } from '@/types'

export const getLearningOverview = () => {
  return request.get<LearningOverview>('/analysis/overview')
}

export const getAccuracyTrend = (days: number = 7) => {
  return request.get<AccuracyTrend[]>(`/analysis/accuracy-trend?days=${days}`)
}

export const getKnowledgeMastery = (subjectId?: string) => {
  return request.get<KnowledgeMastery[]>(
    subjectId ? `/analysis/knowledge-mastery/${subjectId}` : '/analysis/knowledge-mastery'
  )
}

export const getRecommendations = () => {
  return request.get<{
    weak_knowledge: { knowledge_id: string; knowledge_name: string; error_count: number }[]
    recommended_questions: any[]
  }>('/analysis/recommendations')
}
