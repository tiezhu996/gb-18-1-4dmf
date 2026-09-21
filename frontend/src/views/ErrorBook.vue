<template>
  <div class="error-book-page">
    <van-nav-bar title="错题本" />

    <div class="page-content">
      <div class="stats-card">
        <div class="stats-grid">
          <div class="stat-item" @click="filterByMastered(null)">
            <div class="stat-value">{{ stats.total_errors }}</div>
            <div class="stat-label">总错题</div>
          </div>
          <div class="stat-item" @click="filterByMastered(false)">
            <div class="stat-value pending">{{ stats.pending_errors }}</div>
            <div class="stat-label">待掌握</div>
          </div>
          <div class="stat-item" @click="filterByMastered(true)">
            <div class="stat-value mastered">{{ stats.mastered_errors }}</div>
            <div class="stat-label">已掌握</div>
          </div>
        </div>
      </div>

      <div class="filter-tabs">
        <van-tabs v-model:active="activeTab" shrink @change="onTabChange">
          <van-tab title="全部" />
          <van-tab title="待掌握" />
          <van-tab title="已掌握" />
        </van-tabs>
      </div>

      <div class="error-list" v-if="filteredErrors.length > 0">
        <div
          v-for="error in filteredErrors"
          :key="error.id"
          class="error-card"
        >
          <div class="card-header">
            <div class="question-tags">
              <span class="type-tag">{{ getTypeLabel(error.question.type) }}</span>
              <span class="difficulty-tag" :class="'difficulty-' + error.question.difficulty">
                {{ getDifficultyLabel(error.question.difficulty) }}
              </span>
            </div>
            <div class="error-meta">
              <span class="wrong-count">错 {{ error.wrong_count }} 次</span>
              <span v-if="error.mastered" class="mastered-badge">已掌握</span>
            </div>
          </div>

          <div class="question-content" @click="toggleExpand(error.id)">
            {{ error.question.content }}
            <van-icon name="arrow-down" class="expand-icon" :class="{ expanded: expandedIds.includes(error.id) }" />
          </div>

          <div v-if="expandedIds.includes(error.id)" class="detail-section">
            <div v-if="error.question.type !== 'fill_blank'" class="options-list">
              <div
                v-for="opt in error.question.options"
                :key="opt.key"
                class="option-item"
                :class="getOptionClass(error.question, opt.key)"
              >
                <span class="option-key">{{ opt.key }}</span>
                <span class="option-content">{{ opt.content }}</span>
              </div>
            </div>

            <div v-else class="fill-answer">
              <span class="label">正确答案：</span>
              <span class="correct-answer">{{ error.question.correct_answer }}</span>
            </div>

            <div v-if="error.question.explanation" class="explanation-box">
              <div class="explanation-title">解析</div>
              <div class="explanation-content">{{ error.question.explanation }}</div>
            </div>

            <div class="action-buttons">
              <van-button
                v-if="!error.mastered"
                type="success"
                size="small"
                @click.stop="handleMarkMastered(error.id)"
              >
                标记已掌握
              </van-button>
              <van-button
                v-else
                size="small"
                @click.stop="handleUnmarkMastered(error.id)"
              >
                取消标记
              </van-button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <div class="empty-icon">🎉</div>
        <div class="empty-text">
          {{ activeTab === 0 ? '暂无错题，继续加油！' : (activeTab === 1 ? '待掌握列表为空' : '已掌握列表为空') }}
        </div>
      </div>

      <div class="bottom-action" v-if="stats.pending_errors > 0">
        <van-button type="primary" block round @click="startErrorPractice">
          错题重练 ({{ stats.pending_errors }} 题)
        </van-button>
      </div>
    </div>

    <van-tabbar v-model="activeTabbar" route>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showLoadingToast, closeToast, showToast, showConfirmDialog } from 'vant'
import { getErrorList, getErrorStats, markMastered, unmarkMastered } from '@/api/errors'
import type { ErrorRecord, Question } from '@/types'

const router = useRouter()

const activeTabbar = ref(2)
const activeTab = ref(0)
const errors = ref<ErrorRecord[]>([])
const expandedIds = ref<string[]>([])

const stats = ref({
  total_errors: 0,
  pending_errors: 0,
  mastered_errors: 0
})

const filteredErrors = computed(() => {
  if (activeTab.value === 1) {
    return errors.value.filter((e) => !e.mastered)
  }
  if (activeTab.value === 2) {
    return errors.value.filter((e) => e.mastered)
  }
  return errors.value
})

const getTypeLabel = (type: string) => {
  const typeMap: Record<string, string> = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    true_false: '判断题',
    fill_blank: '填空题'
  }
  return typeMap[type] || '题目'
}

const getDifficultyLabel = (diff: string) => {
  const diffMap: Record<string, string> = {
    easy: '简单',
    medium: '中等',
    hard: '困难'
  }
  return diffMap[diff] || ''
}

const getOptionClass = (question: Question, key: string) => {
  const correctAnswer = Array.isArray(question.correct_answer)
    ? question.correct_answer
    : [question.correct_answer]

  if (correctAnswer.includes(key)) {
    return 'correct'
  }
  return ''
}

const toggleExpand = (id: string) => {
  const index = expandedIds.value.indexOf(id)
  if (index > -1) {
    expandedIds.value.splice(index, 1)
  } else {
    expandedIds.value.push(id)
  }
}

const onTabChange = () => {
  fetchErrors()
}

const filterByMastered = (mastered: boolean | null) => {
  if (mastered === null) activeTab.value = 0
  else if (mastered === false) activeTab.value = 1
  else activeTab.value = 2
}

const handleMarkMastered = async (id: string) => {
  showConfirmDialog({
    title: '确认掌握',
    message: '确定将此题标记为已掌握吗？'
  })
    .then(async () => {
      try {
        await markMastered(id)
        showToast('已标记为掌握')
        fetchData()
      } catch (error) {
        console.error(error)
      }
    })
    .catch(() => {})
}

const handleUnmarkMastered = async (id: string) => {
  try {
    await unmarkMastered(id)
    showToast('已取消标记')
    fetchData()
  } catch (error) {
    console.error(error)
  }
}

const startErrorPractice = () => {
  router.push('/practice/error_practice?count=20')
}

const fetchData = async () => {
  showLoadingToast({ message: '加载中...', duration: 0 })
  try {
    const errorStatsData = await getErrorStats()
    stats.value.total_errors = errorStatsData.total_errors
    stats.value.pending_errors = errorStatsData.total_errors - errorStatsData.mastered_count
    stats.value.mastered_errors = errorStatsData.mastered_count
  } catch (error) {
    console.error(error)
  } finally {
    closeToast()
  }
}

const fetchErrors = async () => {
  showLoadingToast({ message: '加载中...', duration: 0 })
  try {
    const mastered = activeTab.value === 0 ? undefined : activeTab.value === 2
    const data = await getErrorList({
      page: 1,
      page_size: 100,
      mastered
    })
    errors.value = data.items
  } catch (error) {
    console.error(error)
  } finally {
    closeToast()
  }
}

onMounted(() => {
  fetchData()
  fetchErrors()
})
</script>

<style scoped>
.error-book-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fef2f2 0%, #f5f7fa 100%);
  padding-bottom: 100px;
}

.page-content {
  padding: 16px;
}

.stats-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
}

.stat-item {
  text-align: center;
  cursor: pointer;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #ef4444;
  margin-bottom: 4px;
}

.stat-value.pending {
  color: #f59e0b;
}

.stat-value.mastered {
  color: #22c55e;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
}

.filter-tabs {
  margin-bottom: 12px;
}

.error-card {
  background: white;
  border-radius: 16px;
  margin-bottom: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.question-tags {
  display: flex;
  gap: 8px;
}

.type-tag {
  padding: 3px 10px;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.difficulty-tag {
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.difficulty-easy {
  background: #dcfce7;
  color: #15803d;
}

.difficulty-medium {
  background: #fef3c7;
  color: #b45309;
}

.difficulty-hard {
  background: #fee2e2;
  color: #b91c1c;
}

.error-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wrong-count {
  font-size: 12px;
  color: #64748b;
}

.mastered-badge {
  padding: 3px 10px;
  background: #dcfce7;
  color: #15803d;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.question-content {
  padding: 16px;
  font-size: 14px;
  line-height: 1.7;
  color: #1a1a2e;
  white-space: pre-wrap;
  cursor: pointer;
  position: relative;
}

.expand-icon {
  position: absolute;
  right: 16px;
  bottom: 16px;
  color: #94a3b8;
  transition: transform 0.3s;
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.detail-section {
  padding: 0 16px 16px;
  border-top: 1px solid #f1f5f9;
}

.options-list {
  margin-top: 12px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 8px;
}

.option-item.correct {
  background: #dcfce7;
}

.option-key {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
  text-align: center;
  line-height: 22px;
  font-size: 11px;
  font-weight: 600;
  margin-right: 10px;
  flex-shrink: 0;
}

.correct .option-key {
  background: #22c55e;
  color: white;
}

.option-content {
  flex: 1;
  font-size: 13px;
  color: #334155;
  line-height: 1.5;
}

.fill-answer {
  margin-top: 12px;
  padding: 12px;
  background: #dcfce7;
  border-radius: 8px;
}

.fill-answer .label {
  font-size: 13px;
  color: #64748b;
}

.correct-answer {
  font-size: 14px;
  font-weight: 600;
  color: #15803d;
}

.explanation-box {
  background: #f0f9ff;
  border-radius: 8px;
  padding: 12px;
  margin-top: 12px;
  border-left: 3px solid #3b82f6;
}

.explanation-title {
  font-size: 12px;
  font-weight: 600;
  color: #1d4ed8;
  margin-bottom: 6px;
}

.explanation-content {
  font-size: 12px;
  line-height: 1.6;
  color: #475569;
}

.action-buttons {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 60px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 14px;
  color: #64748b;
}

.bottom-action {
  position: fixed;
  bottom: 56px;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: transparent;
}
</style>
