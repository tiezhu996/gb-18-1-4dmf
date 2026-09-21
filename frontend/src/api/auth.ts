import request from './request'
import type { User, TokenResponse } from '@/types'

export const login = (username: string, password: string) => {
  return request.post<TokenResponse>('/auth/login', { username, password })
}

export const register = (username: string, password: string, email?: string) => {
  return request.post<TokenResponse>('/auth/register', { username, password, email })
}

export const getCurrentUser = () => {
  return request.get<User>('/auth/me')
}
