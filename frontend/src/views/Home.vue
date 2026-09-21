<template>
  <div class="page-container">
    <van-nav-bar title="在线题库" />

    <div class="page-content">
      <div class="welcome-card card">
        <div class="welcome-info">
          <div class="welcome-title">
            您好，{{ userStore.userInfo?.username || '同学' }}
          </div>
          <div class="welcome-subtitle">今天也是学习的一天 ✨</div>
        </div>
        <div class="welcome-avatar">
          <span>👤</span>
        </div>
      </div>

      <div class="quick-actions card">
        <div class="section-title">快速开始</div>
        <div class="action-grid">
          <div class="action-item" @click="goToSubjects">
            <div class="action-icon" style="background: linear-gradient(135deg, #3b82f6, #1d4ed8)">
              📚
            </div>
            <span class="action-label">题库练习</span>
          </div>
          <div class="action-item" @click="startQuickExam">
            <div class="action-icon" style="background: linear-gradient(135deg, #f97316, #ea580c)">
              📝
            </div>
            <span class="action-label">模拟考试</span>
          </div>
          <div class="action-item" @click="goToErrors">
            <div class="action-icon" style="background: linear-gradient(135deg, #ef4444, #dc2626)">
              ❌
            </div>
            <span class="action-label">错题本</span>
          </div>
          <div class="action-item" @click="goToAnalysis">
            <div class="action-icon" style="background: linear-gradient(135deg, #22c55e, #16a34a)">
              📊
            </div>
            <span class="action-label">学习分析</span>
          </div>
        </div>
      </div>

      <div class="stats-card card">
        <div class="section-title">学习数据</div>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-value">{{ overview.total_practiced }}</div>
            <div class="stat-label">总练习题数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ overview.accuracy }}%</div>
            <div class="stat-label">正确率</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ overview.total_exams }}</div>
            <div class="stat-label">完成考试</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ errorStats.total_errors }}</div>
            <div class="stat-label">待掌握错题</div>
          </div>
        </div>
      </div>

      <div class="subjects-card card">
        <div class="section-title">
          学科题库
          <span class="section-link" @click="goToSubjects">查看全部 ›</span>
        </div>
        <div class="subject-list">
          <div
            v-for="subject in subjects"
            :key="subject.id"
            class="subject-item"
            @click="goToKnowledge(subject.id)"
          >
            <div class="subject-icon" :style="{ background: subject.color + '20', color: subject.color }">
              {{ subject.icon }}
            </div>
            <div class="subject-info">
              <div class="subject-name">{{ subject.name }}</div>
              <div class="subject-meta">
                {{ subject.question_count }} 题 · {{ subject.chapter_count }} 章
              </div>
            </div>
            <van-icon name="arrow" />
          </div>
        </div>
      </div>
    </div>

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
import { showToast, showConfirmDialog, showLoadingToast, closeToast } from 'vant'
import { useUserStore } from '@/stores/user'
import { getSubjects } from '@/api/knowledge'
import { getLearningOverview } from '@/api/analysis'
import { getErrorStats } from '@/api/errors'
import { startExam } from '@/api/exam'
import type { Subject } from '@/types'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref(0)
const subjects = ref<Subject[]>([])

const overview = reactive({
  total_practiced: 0,
  accuracy: 0,
  total_exams: 0
})

const errorStats = reactive({
  total_errors: 0
})

const fetchData = async () => {
  try {
    showLoadingToast({ message: '加载中...', duration: 0 })

    const [subjectsData, overviewData, errorStatsData] = await Promise.all([
      getSubjects(),
      getLearningOverview(),
      getErrorStats()
    ])

    subjects.value = subjectsData
    overview.total_practiced = overviewData.total_practiced
    overview.accuracy = overviewData.accuracy
    overview.total_exams = overviewData.total_exams
    errorStats.total_errors = errorStatsData.total_errors
  } catch (error) {
    console.error(error)
  } finally {
    closeToast()
  }
}

const goToSubjects = () => {
  router.push('/subjects')
}

const goToKnowledge = (subjectId: string) => {
  router.push(`/knowledge/${subjectId}`)
}

const goToErrors = () => {
  router.push('/errors')
}

const goToAnalysis = () => {
  router.push('/analysis')
}

const startQuickExam = async () => {
  if (subjects.value.length === 0) {
    showToast('暂无可用学科')
    return
  }

  const subjectOptions = subjects.value.map((s) => s.name).join('、')
  showConfirmDialog({
    title: '快速考试',
    message: `将从 ${subjectOptions} 中随机抽取题目进行模拟考试，确定开始吗？`
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

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.welcome-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
}

.welcome-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.welcome-subtitle {
  font-size: 13px;
  opacity: 0.9;
}

.welcome-avatar {
  width: 50px;
  height: 50px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.action-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  margin-bottom: 6px;
}

.action-label {
  font-size: 12px;
  color: #475569;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.section-link {
  font-size: 12px;
  color: #3b82f6;
  font-weight: normal;
  margin-left: auto;
}

.subject-list {
  margin-top: 8px;
}

.subject-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.subject-item:last-child {
  border-bottom: none;
}

.subject-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  margin-right: 12px;
}

.subject-info {
  flex: 1;
}

.subject-name {
  font-size: 15px;
  font-weight: 500;
  color: #1a1a2e;
  margin-bottom: 2px;
}

.subject-meta {
  font-size: 12px;
  color: #94a3b8;
}
</style>
