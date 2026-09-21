import request from './request'
import type { Subject, KnowledgeNode } from '@/types'

export const getSubjects = () => {
  return request.get<Subject[]>('/knowledge/subjects')
}

export const getKnowledgeTree = (subjectId: string) => {
  return request.get<KnowledgeNode[]>(`/knowledge/tree/${subjectId}`)
}

export const searchKnowledge = (subjectId: string, keyword: string) => {
  return request.get<KnowledgeNode[]>(`/knowledge/search/${subjectId}`, {
    params: { keyword }
  })
}
