import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { User } from '@/types'
import { login, register, getCurrentUser } from '@/api/auth'

export const useUserStore = defineStore(
  'user',
  () => {
    const token = ref<string>('')
    const userInfo = ref<User | null>(null)
    const isLoggedIn = ref(false)

    const handleLogin = async (username: string, password: string) => {
      const result = await login(username, password)
      token.value = result.access_token
      userInfo.value = result.user
      isLoggedIn.value = true
      return result
    }

    const handleRegister = async (username: string, password: string, email?: string) => {
      const result = await register(username, password, email)
      token.value = result.access_token
      userInfo.value = result.user
      isLoggedIn.value = true
      return result
    }

    const fetchUserInfo = async () => {
      if (token.value) {
        try {
          const user = await getCurrentUser()
          userInfo.value = user
          isLoggedIn.value = true
        } catch (error) {
          logout()
        }
      }
    }

    const logout = () => {
      token.value = ''
      userInfo.value = null
      isLoggedIn.value = false
    }

    return {
      token,
      userInfo,
      isLoggedIn,
      handleLogin,
      handleRegister,
      fetchUserInfo,
      logout
    }
  },
  {
    persist: {
      key: 'user-store',
      paths: ['token', 'userInfo', 'isLoggedIn']
    }
  }
)
