<template>
  <div class="page-container">
    <van-nav-bar title="学科题库" left-arrow @click-left="router.back()" />

    <div class="page-content">
      <van-search
        v-model="searchKeyword"
        placeholder="搜索学科或知识点"
        background="transparent"
        shape="round"
      />

      <div v-if="loading" class="loading-container">
        <van-loading />
      </div>

      <div v-else class="subjects-grid">
        <div
          v-for="subject in subjects"
          :key="subject.id"
          class="subject-card"
          @click="goToKnowledge(subject.id)"
        >
          <div class="subject-card-icon" :style="{ background: subject.color + '15', color: subject.color }">
            {{ subject.icon }}
          </div>
          <div class="subject-card-content">
            <div class="subject-card-name">{{ subject.name }}</div>
            <div class="subject-card-meta">
              <span>{{ subject.question_count }} 题</span>
              <span>{{ subject.chapter_count }} 章节</span>
            </div>
            <div class="subject-card-desc">{{ subject.description }}</div>
          </div>
          <van-icon name="arrow" color="#cbd5e1" />
        </div>
      </div>

      <div class="exam-section card">
        <div class="section-title">模拟考试</div>
        <div class="exam-info">
          <p class="exam-desc">选择学科，设定题目数量和时间，进行模拟考试练习</p>
          <div class="exam-options">
            <div class="exam-option" @click="startExam('math')">
              <div class="exam-option-icon">📐</div>
              <span class="exam-option-label">数学模拟考</span>
            </div>
            <div class="exam-option" @click="startExam('english')">
              <div class="exam-option-icon">📚</div>
              <span class="exam-option-label">英语模拟考</span>
            </div>
            <div class="exam-option" @click="startExam('physics')">
              <div class="exam-option-icon">⚛️</div>
              <span class="exam-option-label">物理模拟考</span>
            </div>
            <div class="exam-option" @click="startExam('chemistry')">
              <div class="exam-option-icon">🧪</div>
              <span class="exam-option-label">化学模拟考</span>
            </div>
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showLoadingToast, closeToast, showDialog, showConfirmDialog } from 'vant'
import { getSubjects } from '@/api/knowledge'
import { startExam as startExamApi } from '@/api/exam'
import type { Subject } from '@/types'

const router = useRouter()
const activeTab = ref(1)
const loading = ref(true)
const searchKeyword = ref('')
const subjects = ref<Subject[]>([])

const fetchSubjects = async () => {
  try {
    subjects.value = await getSubjects()
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const goToKnowledge = (subjectId: string) => {
  router.push(`/knowledge/${subjectId}`)
}

const startExam = async (subjectName: string) => {
  let subject = subjects.value.find((s) => s.name === subjectName)
  if (!subject) {
    const firstSubject = subjects.value[0]
    if (!firstSubject) return
    subject = firstSubject
  }

  showDialog({
    title: '选择考试配置',
    message: '请选择题目数量和考试时间'
  })

  showConfirmDialog({
    title: '模拟考试',
    message: `将从 ${subject.name} 题库中抽取 20 道题，考试时间 30 分钟，确定开始吗？`
  })
    .then(async () => {
      try {
        showLoadingToast({ message: '正在组卷...', duration: 0 })
        const result = await startExamApi({
          name: `${subject.name}模拟考试`,
          subject_id: subject.id,
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
  fetchSubjects()
})
</script>

<style scoped>
.subjects-grid {
  margin-top: 12px;
}

.subject-card {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.subject-card-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  margin-right: 14px;
}

.subject-card-content {
  flex: 1;
}

.subject-card-name {
  font-size: 17px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.subject-card-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
}

.subject-card-meta span {
  font-size: 12px;
  color: #64748b;
}

.subject-card-desc {
  font-size: 12px;
  color: #94a3b8;
}

.exam-info {
  margin-top: 8px;
}

.exam-desc {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 16px;
}

.exam-options {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.exam-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: #f8fafc;
  border-radius: 12px;
  cursor: pointer;
}

.exam-option-icon {
  font-size: 24px;
  margin-bottom: 6px;
}

.exam-option-label {
  font-size: 11px;
  color: #475569;
  text-align: center;
}
</style>
