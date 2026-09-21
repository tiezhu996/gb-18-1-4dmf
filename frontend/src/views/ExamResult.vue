<template>
  <div class="exam-result-page">
    <van-nav-bar title="考试结果" left-arrow @click-left="goHome" />

    <div class="result-header">
      <div class="score-circle" :class="scoreClass">
        <div class="score-value">{{ result?.score || 0 }}</div>
        <div class="score-label">分</div>
      </div>
      <div class="exam-info">
        <div class="exam-name">{{ result?.name }}</div>
        <div class="exam-time">用时 {{ formatDuration(result?.duration_used) }}</div>
      </div>
    </div>

    <div class="stats-card">
      <div class="stats-grid">
        <div class="stat-item">
          <div class="stat-value total">{{ result?.total_questions }}</div>
          <div class="stat-label">总题数</div>
        </div>
        <div class="stat-item">
          <div class="stat-value correct">{{ result?.correct_count }}</div>
          <div class="stat-label">答对</div>
        </div>
        <div class="stat-item">
          <div class="stat-value wrong">{{ wrongCount }}</div>
          <div class="stat-label">答错</div>
        </div>
        <div class="stat-item">
          <div class="stat-value accuracy">{{ result?.accuracy }}%</div>
          <div class="stat-label">正确率</div>
        </div>
      </div>
    </div>

    <div class="details-section">
      <div class="section-header">
        <span class="section-title">答案解析</span>
        <div class="filter-tabs">
          <van-tabs v-model:active="filterType" shrink>
            <van-tab title="全部" />
            <van-tab title="答错" />
          </van-tabs>
        </div>
      </div>

      <div class="question-list">
        <div
          v-for="(item, index) in filteredDetails"
          :key="item.question_id"
          class="question-card"
        >
          <div class="question-header">
            <span class="question-num">第 {{ getOriginalIndex(item) + 1 }} 题</span>
            <span class="question-badge" :class="item.is_correct ? 'correct' : 'wrong'">
              {{ item.is_correct ? '正确' : '错误' }}
            </span>
          </div>

          <div class="question-content">
            <div class="question-text">
              <span class="question-type-tag">{{ getTypeLabel(item.type) }}</span>
              {{ item.content }}
            </div>

            <div v-if="item.type !== 'fill_blank'" class="options-list">
              <div
                v-for="opt in getDetailOptions(item)"
                :key="opt.key"
                class="option-item"
                :class="getOptionResultClass(item, opt.key)"
              >
                <span class="option-key">{{ opt.key }}</span>
                <span class="option-content">{{ opt.content }}</span>
              </div>
            </div>

            <div v-else class="fill-result">
              <div class="result-row">
                <span class="result-label">你的答案：</span>
                <span class="result-value" :class="item.is_correct ? 'correct' : 'wrong'">
                  {{ item.user_answer || '未作答' }}
                </span>
              </div>
              <div class="result-row">
                <span class="result-label">正确答案：</span>
                <span class="result-value correct">
                  {{ item.correct_answer }}
                </span>
              </div>
            </div>

            <div v-if="item.explanation" class="explanation-box">
              <div class="explanation-title">解析</div>
              <div class="explanation-content">{{ item.explanation }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="bottom-actions">
      <van-button type="primary" block round @click="goHome">
        返回首页
      </van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showLoadingToast, closeToast } from 'vant'
import { getExamResult } from '@/api/exam'
import type { ExamResult, ExamQuestionDetail } from '@/types'

const route = useRoute()
const router = useRouter()

const sessionId = computed(() => route.params.sessionId as string)

const result = ref<ExamResult | null>(null)
const filterType = ref(0)

const wrongCount = computed(() => {
  if (!result.value) return 0
  return result.value.total_questions - result.value.correct_count
})

const scoreClass = computed(() => {
  const score = result.value?.score || 0
  if (score >= 80) return 'excellent'
  if (score >= 60) return 'pass'
  return 'fail'
})

const filteredDetails = computed(() => {
  if (!result.value?.details) return []
  if (filterType.value === 1) {
    return result.value.details.filter((d) => !d.is_correct)
  }
  return result.value.details
})

const formatDuration = (seconds?: number) => {
  if (!seconds) return '0分0秒'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}分${s}秒`
}

const getTypeLabel = (type: string) => {
  const typeMap: Record<string, string> = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    true_false: '判断题',
    fill_blank: '填空题'
  }
  return typeMap[type] || '题目'
}

const getOriginalIndex = (item: ExamQuestionDetail) => {
  if (!result.value?.details) return 0
  return result.value.details.findIndex((d) => d.question_id === item.question_id)
}

const getOptionResultClass = (item: ExamQuestionDetail, key: string) => {
  const classes: string[] = []
  const correctAnswer = Array.isArray(item.correct_answer) ? item.correct_answer : [item.correct_answer]
  const userAnswer = Array.isArray(item.user_answer) ? item.user_answer : [item.user_answer]

  if (correctAnswer.includes(key)) {
    classes.push('correct')
  } else if (userAnswer.includes(key) && !correctAnswer.includes(key)) {
    classes.push('wrong')
  }
  return classes
}

// 判断题种子数据可能缺少 options，补默认选项（A=正确，B=错误）
const getDetailOptions = (item: ExamQuestionDetail) => {
  if (item.type === 'true_false' && (!item.options || item.options.length === 0)) {
    return [
      { key: 'A', content: '正确' },
      { key: 'B', content: '错误' }
    ]
  }
  return item.options || []
}

const goHome = () => {
  router.push('/')
}

const fetchResult = async () => {
  showLoadingToast({ message: '加载中...', duration: 0 })
  try {
    result.value = await getExamResult(sessionId.value)
  } catch (error) {
    console.error(error)
  } finally {
    closeToast()
  }
}

onMounted(() => {
  fetchResult()
})
</script>

<style scoped>
.exam-result-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f0f9ff 0%, #f5f7fa 100%);
  padding-bottom: 80px;
}

.result-header {
  padding: 30px 20px;
  text-align: center;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  color: white;
}

.score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.score-circle.excellent {
  background: rgba(34, 197, 94, 0.3);
}

.score-circle.pass {
  background: rgba(251, 191, 36, 0.3);
}

.score-circle.fail {
  background: rgba(239, 68, 68, 0.3);
}

.score-value {
  font-size: 40px;
  font-weight: 700;
  line-height: 1;
}

.score-label {
  font-size: 14px;
  opacity: 0.9;
  margin-top: 4px;
}

.exam-name {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 6px;
}

.exam-time {
  font-size: 13px;
  opacity: 0.85;
}

.stats-card {
  margin: 16px;
  padding: 20px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.stat-value.total {
  color: #3b82f6;
}

.stat-value.correct {
  color: #22c55e;
}

.stat-value.wrong {
  color: #ef4444;
}

.stat-value.accuracy {
  color: #f59e0b;
}

.stat-label {
  font-size: 12px;
  color: #64748b;
}

.details-section {
  margin: 0 16px;
}

.section-header {
  margin-bottom: 12px;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}

.filter-tabs {
  margin-top: 8px;
}

.question-card {
  background: white;
  border-radius: 16px;
  margin-bottom: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.question-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.question-num {
  font-size: 13px;
  color: #64748b;
}

.question-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.question-badge.correct {
  background: #dcfce7;
  color: #15803d;
}

.question-badge.wrong {
  background: #fee2e2;
  color: #b91c1c;
}

.question-content {
  padding: 16px;
}

.question-text {
  font-size: 15px;
  line-height: 1.7;
  color: #1a1a2e;
  margin-bottom: 16px;
  white-space: pre-wrap;
}

.question-type-tag {
  display: inline-block;
  padding: 2px 8px;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 4px;
  font-size: 11px;
  margin-right: 8px;
  vertical-align: middle;
}

.options-list {
  margin-bottom: 16px;
}

.option-item {
  display: flex;
  align-items: flex-start;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 8px;
  border: 1px solid #e2e8f0;
}

.option-item.correct {
  background: #dcfce7;
  border-color: #bbf7d0;
}

.option-item.wrong {
  background: #fee2e2;
  border-color: #fecaca;
}

.option-key {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
  text-align: center;
  line-height: 24px;
  font-size: 12px;
  font-weight: 600;
  margin-right: 10px;
  flex-shrink: 0;
}

.correct .option-key {
  background: #22c55e;
  color: white;
}

.wrong .option-key {
  background: #ef4444;
  color: white;
}

.option-content {
  flex: 1;
  font-size: 14px;
  color: #334155;
  line-height: 1.5;
}

.fill-result {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}

.result-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.result-row:last-child {
  margin-bottom: 0;
}

.result-label {
  font-size: 13px;
  color: #64748b;
  margin-right: 8px;
  flex-shrink: 0;
}

.result-value {
  font-size: 14px;
  font-weight: 500;
}

.result-value.correct {
  color: #15803d;
}

.result-value.wrong {
  color: #b91c1c;
}

.explanation-box {
  background: #f0f9ff;
  border-radius: 8px;
  padding: 12px;
  border-left: 3px solid #3b82f6;
}

.explanation-title {
  font-size: 13px;
  font-weight: 600;
  color: #1d4ed8;
  margin-bottom: 6px;
}

.explanation-content {
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
}

.bottom-actions {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: white;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}
</style>
