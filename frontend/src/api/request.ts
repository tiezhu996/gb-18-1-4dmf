import axios from 'axios'
import type { AxiosRequestConfig } from 'axios'
import { showToast } from 'vant'
import { useUserStore } from '@/stores/user'
import router from '@/router'

declare module 'axios' {
  interface AxiosRequestConfig {
    /** 静默请求：业务错误不弹全局 Toast（如自动保存） */
    _silent?: boolean
  }
}

interface DataClient {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
}

const request = axios.create({
  baseURL: '/api',
  timeout: 30000
}) as DataClient & ReturnType<typeof axios.create>

request.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    const token = userStore.token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.detail || error.message || '请求失败'
    const silent = error.config?._silent

    if (status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
      if (!silent) showToast('登录已过期，请重新登录')
    } else if (status === 403) {
      if (!silent) showToast('没有权限')
    } else if (!silent) {
      showToast(message)
    }

    return Promise.reject(error)
  }
)

export default request
