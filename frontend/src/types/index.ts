export interface User {
  id: string
  username: string
  email?: string
  role: string
  created_at: string
  avatar?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Subject {
  id: string
  name: string
  icon?: string
  description?: string
  color: string
  question_count: number
  chapter_count: number
}

export interface KnowledgeNode {
  id: string
  name: string
  level: number
  parent_id?: string
  subject_id: string
  order: number
  description?: string
  question_count: number
  children: KnowledgeNode[]
}

export interface QuestionOption {
  key: string
  content: string
}

export interface Question {
  id: string
  type: 'single_choice' | 'multiple_choice' | 'true_false' | 'fill_blank'
  content: string
  options?: QuestionOption[]
  correct_answer?: any
  explanation?: string
  subject_id: string
  knowledge_ids: string[]
  difficulty: 'easy' | 'medium' | 'hard'
  tags: string[]
}

export interface PracticeSession {
  id: string
  mode: string
  subject_id: string
  knowledge_ids?: string[]
  question_ids: string[]
  current_index: number
  answers: Record<string, any>
  total: number
  correct_count: number
}

export interface PracticeResult {
  question_id: string
  is_correct: boolean
  correct_answer: any
  explanation?: string
  progress: {
    current: number
    total: number
    correct: number
    accuracy: number
  }
  is_finished: boolean
}

export interface ExamSession {
  session_id: string
  name: string
  total_questions: number
  duration_minutes: number
  start_time: string
  end_time: string
  remaining_seconds: number
  is_submitted: boolean
  answers: Record<string, any>
  questions: Question[]
}

export interface ExamResult {
  id: string
  name: string
  subject_id: string
  score: number
  total_questions: number
  correct_count: number
  accuracy: number
  duration_used: number
  submitted_at: string
  details?: ExamQuestionDetail[]
}

export interface ExamQuestionDetail {
  question_id: string
  type: string
  content: string
  options?: QuestionOption[]
  user_answer: any
  correct_answer: any
  is_correct: boolean
  explanation?: string
}

export interface ErrorRecord {
  id: string
  question_id: string
  question: Question
  wrong_count: number
  created_at: string
  last_wrong_at: string
  mastered: boolean
}

export interface LearningOverview {
  total_practiced: number
  total_correct: number
  accuracy: number
  total_exams: number
  avg_exam_score: number
  weak_knowledge: {
    knowledge_id: string
    knowledge_name: string
    error_count: number
  }[]
}

export interface AccuracyTrend {
  date: string
  accuracy: number
  total: number
  correct: number
}

export interface KnowledgeMastery {
  knowledge_id: string
  knowledge_name: string
  total_answered: number
  correct_count: number
  mastery_rate: number
}
