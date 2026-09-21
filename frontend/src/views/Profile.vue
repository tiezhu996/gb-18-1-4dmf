<template>
  <div class="profile-page">
    <van-nav-bar title="我的" />

    <div class="page-content">
      <div class="user-card">
        <div class="avatar">
          <span>👤</span>
        </div>
        <div class="user-info">
          <div class="username">{{ userStore.userInfo?.username || '未登录' }}</div>
          <div class="role-tag" :class="userStore.userInfo?.role">
            {{ userStore.userInfo?.role === 'admin' ? '管理员' : '学生' }}
          </div>
        </div>
      </div>

      <div class="stats-card">
        <div class="stats-item" @click="goToErrors">
          <div class="stats-value">{{ errorStats.total_errors }}</div>
          <div class="stats-label">错题</div>
        </div>
        <div class="stats-divider"></div>
        <div class="stats-item" @click="goToAnalysis">
          <div class="stats-value">{{ overview.total_practiced }}</div>
          <div class="stats-label">练习</div>
        </div>
        <div class="stats-divider"></div>
        <div class="stats-item" @click="goToExams">
          <div class="stats-value">{{ overview.total_exams }}</div>
          <div class="stats-label">考试</div>
        </div>
      </div>

      <div class="menu-list">
        <div class="menu-section">
          <div class="menu-item" @click="goToSubjects">
            <div class="menu-icon" style="background: #dbeafe">📚</div>
            <div class="menu-label">题库练习</div>
            <van-icon name="arrow" class="menu-arrow" />
          </div>
          <div class="menu-item" @click="startQuickExam">
            <div class="menu-icon" style="background: #fed7aa">📝</div>
            <div class="menu-label">模拟考试</div>
            <van-icon name="arrow" class="menu-arrow" />
          </div>
          <div class="menu-item" @click="goToErrors">
            <div class="menu-icon" style="background: #fee2e2">❌</div>
            <div class="menu-label">错题本</div>
            <van-icon name="arrow" class="menu-arrow" />
          </div>
          <div class="menu-item" @click="goToAnalysis">
            <div class="menu-icon" style="background: #dcfce7">📊</div>
            <div class="menu-label">学习分析</div>
            <van-icon name="arrow" class="menu-arrow" />
          </div>
        </div>

        <div class="menu-section">
          <div class="menu-item" @click="showAbout = true">
            <div class="menu-icon" style="background: #f3e8ff">ℹ️</div>
            <div class="menu-label">关于</div>
            <van-icon name="arrow" class="menu-arrow" />
          </div>
        </div>
      </div>

      <div class="logout-section">
        <van-button type="default" block round @click="handleLogout">
          退出登录
        </van-button>
      </div>
    </div>

    <van-dialog
      v-model:show="showAbout"
      title="关于在线题库"
      :show-confirm-button="false"
      :show-cancel-button="true"
      cancel-button-text="关闭"
    >
      <div class="about-content">
        <div class="about-version">版本 1.0.0</div>
        <div class="about-desc">
          在线题库与刷题平台，支持多种练习模式，帮助学生高效刷题，提升学习效率。
        </div>
        <div class="about-features">
          <div class="about-feature">✓ 顺序练习</div>
          <div class="about-feature">✓ 随机练习</div>
          <div class="about-feature">✓ 模拟考试</div>
          <div class="about-feature">✓ 错题本</div>
          <div class="about-feature">✓ 学习分析</div>
        </div>
      </div>
    </van-dialog>

    <van-tabbar v-model="activeTab" route>
      <van-tabbar-item replace to="/">
        <template #icon="{ active }">
          <span style="font-size: 22px">{{ active ? '🏠' : '🏡' }}</span>
        </template>
        首页
      </van-tabbar-item>
      <van-tabbar-item replace to="/subjects">
        <template #icon="{ active }">
          <span style="font-size: 22px">{{ active ? '📚' : '📖' }}</span>
        </template>
        题库
      </van-tabbar-item>
      <van-tabbar-item replace to="/errors">
        <template #icon="{ active }">
          <span style="font-size: 22px">{{ active ? '❌' : '📝' }}</span>
        </template>
        错题
      </van-tabbar-item>
      <van-tabbar-item replace to="/analysis">
        <template #icon="{ active }">
          <span style="font-size: 22px">{{ active ? '📊' : '📈' }}</span>
        </template>
        分析
      </van-tabbar-item>
      <van-tabbar-item replace to="/profile">
        <template #icon="{ active }">
          <span style="font-size: 22px">{{ active ? '👤' : '🧑' }}</span>
        </template>
        我的
      </van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showConfirmDialog, showLoadingToast, closeToast, showToast } from 'vant'
import { useUserStore } from '@/stores/user'
import { getLearningOverview } from '@/api/analysis'
import { getErrorStats } from '@/api/errors'
import { getSubjects } from '@/api/knowledge'
import { startExam } from '@/api/exam'
import type { Subject } from '@/types'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref(4)
const showAbout = ref(false)
const subjects = ref<Subject[]>([])

const overview = reactive({
  total_practiced: 0,
  total_exams: 0
})

const errorStats = reactive({
  total_errors: 0
})

const goToSubjects = () => {
  router.push('/subjects')
}

const goToErrors = () => {
  router.push('/errors')
}

const goToAnalysis = () => {
  router.push('/analysis')
}

const goToExams = () => {
  showToast('考试历史功能开发中')
}

const startQuickExam = async () => {
  if (subjects.value.length === 0) {
    showToast('暂无可用学科')
    return
  }

  showConfirmDialog({
    title: '快速考试',
    message: '将随机抽取20道题进行30分钟模拟考试，确定开始吗？'
  })
    .then(async () => {
      try {
        showLoadingToast({ message: '正在组卷...', duration: 0 })
        const result = await startExam({
          name: '快速考试',
          subject_id: subjects.value[0].id,
          question_count: 20,
          duration_minutes: 30
        })

        closeToast()
        router.push(`/exam/${result.session_id}`)
      } catch (error) {
        console.error(error)
        closeToast()
      }
    })
    .catch(() => {})
}

const handleLogout = () => {
  showConfirmDialog({
    title: '确认退出',
    message: '确定要退出登录吗？'
  })
    .then(() => {
      userStore.logout()
      router.push('/login')
    })
    .catch(() => {})
}

const fetchData = async () => {
  showLoadingToast({ message: '加载中...', duration: 0 })
  try {
    const [overviewData, errorStatsData, subjectsData] = await Promise.all([
      getLearningOverview(),
      getErrorStats(),
      getSubjects()
    ])

    overview.total_practiced = overviewData.total_practiced
    overview.total_exams = overviewData.total_exams
    errorStats.total_errors = errorStatsData.total_errors
    subjects.value = subjectsData
  } catch (error) {
    console.error(error)
  } finally {
    closeToast()
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #e8f3ff 0%, #f5f7fa 100%);
  padding-bottom: 60px;
}

.page-content {
  padding: 16px;
}

.user-card {
  display: flex;
  align-items: center;
  padding: 20px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 16px;
  margin-bottom: 12px;
}

.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  margin-right: 16px;
}

.user-info {
  flex: 1;
}

.username {
  font-size: 18px;
  font-weight: 600;
  color: white;
  margin-bottom: 6px;
}

.role-tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
}

.role-tag.admin {
  background: rgba(255, 255, 255, 0.3);
  color: white;
}

.role-tag.student {
  background: rgba(255, 255, 255, 0.2);
  color: white;
}

.stats-card {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.stats-item {
  flex: 1;
  text-align: center;
  cursor: pointer;
}

.stats-divider {
  width: 1px;
  height: 30px;
  background: #e2e8f0;
}

.stats-value {
  font-size: 20px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.stats-label {
  font-size: 12px;
  color: #64748b;
}

.menu-list {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.menu-section {
  border-bottom: 1px solid #f1f5f9;
}

.menu-section:last-child {
  border-bottom: none;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 16px;
  cursor: pointer;
  transition: background 0.2s;
}

.menu-item:active {
  background: #f8fafc;
}

.menu-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  margin-right: 12px;
}

.menu-label {
  flex: 1;
  font-size: 14px;
  color: #1a1a2e;
}

.menu-arrow {
  color: #cbd5e1;
  font-size: 14px;
}

.logout-section {
  margin-top: 24px;
}

.about-content {
  padding: 10px 0;
}

.about-version {
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.about-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 16px;
}

.about-features {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.about-feature {
  font-size: 12px;
  color: #475569;
}
</style>
