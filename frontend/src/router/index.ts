import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useUserStore } from '@/stores/user'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/subjects',
    name: 'Subjects',
    component: () => import('@/views/Subjects.vue'),
    meta: {requiresAuth: true }
  },
  {
    path: '/knowledge/:subjectId',
    name: 'KnowledgeTree',
    component: () => import('@/views/KnowledgeTree.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/practice/:mode',
    name: 'Practice',
    component: () => import('@/views/Practice.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exam/:sessionId',
    name: 'Exam',
    component: () => import('@/views/Exam.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/exam-result/:sessionId',
    name: 'ExamResult',
    component: () => import('@/views/ExamResult.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/errors',
    name: 'ErrorBook',
    component: () => import('@/views/ErrorBook.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: () => import('@/views/Analysis.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('@/views/Profile.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, _from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
  } else if (to.path === '/login' && userStore.isLoggedIn) {
    next('/')
  } else {
    if (userStore.token && !userStore.userInfo) {
      await userStore.fetchUserInfo()
    }
    next()
  }
})

export default router
