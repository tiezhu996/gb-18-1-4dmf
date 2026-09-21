<template>
  <div class="exam-page">
    <van-nav-bar
      :title="examName"
      left-arrow
      @click-left="handleBack"
    >
      <template #right>
        <div class="timer" :class="{ warning: remainingTime <= 300 }">
          <span class="timer-icon">⏱️</span>
          {{ formatTime(remainingTime) }}
        </div>
      </template>
    </van-nav-bar>

    <div class="progress-header">
      <div class="question-progress">
        <div class="progress-text">
          当前第 {{ currentIndex + 1 }} 题 / 共 {{ questions.length }} 题
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>
      <div class="question-nav">
        <div class="nav-grid">
          <div
            v-for="(_, index) in questions"
            :key="index"
            class="nav-item"
            :class="getNavItemClass(index)"
            @click="goToQuestion(index)"
          >
            {{ index + 1 }}
          </div>
        </div>
      </div>
    </div>

    <div class="question-container" v-if="currentQuestion">
      <div class="question-header">
        <span class="question-type">{{ questionTypeLabel }}</span>
        <span class="difficulty-tag" :class="'difficulty-' + currentQuestion.difficulty">
          {{ difficultyLabel }}
        </span>
      </div>

      <div class="question-content">
        {{ currentQuestion.content }}
      </div>

      <div class="options-container" :class="{ locked: expired }">
        <div
          v-if="currentQuestion.type === 'fill_blank'"
          class="fill-blank-container"
        >
          <van-field
            v-model="answers[currentQuestion.id]"
            placeholder="请输入答案"
            :border="false"
            class="fill-input"
            :disabled="expired"
          />
        </div>

        <template v-else>
          <div
            v-for="option in currentQuestion.options"
            :key="option.key"
            class="option-item"
            :class="{ selected: isOptionSelected(option.key) }"
            @click="selectOption(option.key)"
          >
            <span class="option-key">{{ option.key }}</span>
            <span class="option-content">{{ option.content }}</span>
          </div>
        </template>
      </div>
    </div>

    <div class="nav-bottom">
      <van-button
        plain
        size="large"
        :disabled="currentIndex === 0"
        @click="goPrev"
      >
        上一题
      </van-button>

      <van-button
        type="primary"
        size="large"
        :loading="submitting"
        :disabled="expired"
        @click="handleNextOrSubmit"
      >
        {{ currentIndex === questions.length - 1 ? '交卷' : '下一题' }}
      </van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showLoadingToast, closeToast, showToast } from 'vant'
import { getExam, saveExamAnswers, submitExam } from '@/api/exam'
import type { Question } from '@/types'

const route = useRoute()
const router = useRouter()

const sessionId = computed(() => route.params.sessionId as string)

const examName = ref('模拟考试')
const questions = ref<Question[]>([])
const currentIndex = ref(0)
const answers = reactive<Record<string, any>>({})
const selectedAnswers = reactive<Record<string, string[]>>({})
const durationMinutes = ref(60)
const remainingTime = ref(0)
const submitting = ref(false)
// 到达截止时间后立即锁定页面，停止修改答案
const expired = ref(false)
let timer: number | null = null
let saveTimer: number | null = null
let deadlineTs = 0
let settling = false

const currentQuestion = computed(() => questions.value[currentIndex.value] || null)

const progressPercent = computed(() => {
  return Math.round(((currentIndex.value + 1) / questions.value.length) * 100)
})

const questionTypeLabel = computed(() => {
  const typeMap: Record<string, string> = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    true_false: '判断题',
    fill_blank: '填空题'
  }
  return typeMap[currentQuestion.value?.type || ''] || '题目'
})

const difficultyLabel = computed(() => {
  const diffMap: Record<string, string> = {
    easy: '简单',
    medium: '中等',
    hard: '困难'
  }
  return diffMap[currentQuestion.value?.difficulty || ''] || ''
})

const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const isOptionSelected = (key: string) => {
  const qid = currentQuestion.value?.id
  if (!qid) return false
  if (currentQuestion.value?.type === 'multiple_choice') {
    return (selectedAnswers[qid] || []).includes(key)
  }
  return answers[qid] === key
}

const getNavItemClass = (index: number) => {
  const classes: string[] = []
  const qid = questions.value[index]?.id

  if (index === currentIndex.value) {
    classes.push('current')
  }
  if (qid && (answers[qid] !== undefined || (selectedAnswers[qid] || []).length > 0)) {
    classes.push('answered')
  }
  return classes
}

const selectOption = (key: string) => {
  if (expired.value) return
  const qid = currentQuestion.value?.id
  if (!qid) return

  if (currentQuestion.value?.type === 'multiple_choice') {
    if (!selectedAnswers[qid]) {
      selectedAnswers[qid] = []
    }
    const idx = selectedAnswers[qid].indexOf(key)
    if (idx > -1) {
      selectedAnswers[qid].splice(idx, 1)
    } else {
      selectedAnswers[qid].push(key)
    }
    selectedAnswers[qid].sort()
  } else {
    answers[qid] = key
  }
}

const goToQuestion = (index: number) => {
  currentIndex.value = index
}

const goPrev = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
  }
}

const handleNextOrSubmit = () => {
  if (expired.value) return
  if (currentIndex.value === questions.value.length - 1) {
    confirmSubmit()
  } else {
    currentIndex.value++
  }
}

const getSubmitAnswers = () => {
  const result: Record<string, any> = {}
  questions.value.forEach((q) => {
    if (q.type === 'multiple_choice') {
      result[q.id] = selectedAnswers[q.id] || []
    } else if (q.type === 'fill_blank') {
      result[q.id] = answers[q.id] || ''
    } else {
      result[q.id] = answers[q.id]
    }
  })
  return result
}

// 答题进度自动保存到服务端，刷新或到点后按已保存答案恢复/结算
const flushSave = async () => {
  if (expired.value || settling || questions.value.length === 0) return
  try {
    const res = await saveExamAnswers(sessionId.value, getSubmitAnswers())
    if (!res.saved && res.is_submitted) {
      goToResult()
    }
  } catch (error) {
    // 保存失败不打断答题，下次变更或到点时重试
    console.error(error)
  }
}

const scheduleSave = () => {
  if (expired.value || settling) return
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = window.setTimeout(flushSave, 800)
}

watch(answers, scheduleSave, { deep: true })
watch(selectedAnswers, scheduleSave, { deep: true })

const confirmSubmit = () => {
  const totalAnswered = questions.value.filter((q) => {
    if (q.type === 'multiple_choice') {
      return (selectedAnswers[q.id] || []).length > 0
    }
    return answers[q.id] !== undefined && answers[q.id] !== ''
  }).length

  const unanswered = questions.value.length - totalAnswered
  const message = unanswered > 0
    ? `还有 ${unanswered} 道题未作答，确定要交卷吗？`
    : '确定要交卷吗？'

  showConfirmDialog({
    title: '确认交卷',
    message
  })
    .then(() => {
      doSubmit()
    })
    .catch(() => {})
}

const doSubmit = async () => {
  if (settling) return
  settling = true
  submitting.value = true
  showLoadingToast({ message: '正在交卷...', duration: 0 })
  try {
    const result = await submitExam(sessionId.value, getSubmitAnswers())
    closeToast()
    router.replace(`/exam-result/${result.id}`)
  } catch (error) {
    console.error(error)
    closeToast()
    showToast('交卷失败，请重试')
    settling = false
  } finally {
    submitting.value = false
  }
}

// 到点自动交卷：锁定页面并按已保存答案结算
const handleTimeout = async () => {
  if (settling) return
  settling = true
  expired.value = true
  if (saveTimer) clearTimeout(saveTimer)
  showLoadingToast({ message: '考试时间已到，正在交卷...', duration: 0 })
  try {
    const result = await submitExam(sessionId.value, getSubmitAnswers())
    closeToast()
    router.replace(`/exam-result/${result.id}`)
  } catch (error) {
    console.error(error)
    closeToast()
    // 即使交卷请求失败，服务端也会按已保存答案自动结算，直接查看结果
    goToResult()
  }
}

const goToResult = () => {
  router.replace(`/exam-result/${sessionId.value}`)
}

const handleBack = () => {
  showConfirmDialog({
    title: '确认退出',
    message: '退出后考试仍将继续计时，到点未交卷将按已保存答案自动结算，确定退出吗？'
  })
    .then(() => {
      if (timer) clearInterval(timer)
      router.push('/')
    })
    .catch(() => {})
}

const restoreAnswers = (saved: Record<string, any>) => {
  questions.value.forEach((q) => {
    const value = saved[q.id]
    if (value === undefined || value === null) return
    if (q.type === 'multiple_choice') {
      selectedAnswers[q.id] = Array.isArray(value) ? [...value] : [value]
    } else if (value !== '') {
      answers[q.id] = value
    }
  })
}

const loadExamData = async () => {
  try {
    const data = await getExam(sessionId.value)
    // 已交卷或已到截止时间：直接显示结果（服务端已自动结算）
    if (data.is_submitted || data.remaining_seconds <= 0) {
      goToResult()
      return
    }
    examName.value = data.name
    questions.value = data.questions
    durationMinutes.value = data.duration_minutes
    restoreAnswers(data.answers || {})
    // 以服务端剩余时间为准恢复倒计时，刷新页面不丢失
    deadlineTs = Date.now() + data.remaining_seconds * 1000
    remainingTime.value = data.remaining_seconds
    startTimer()
  } catch (error) {
    console.error(error)
    router.push('/')
  }
}

const startTimer = () => {
  if (timer) clearInterval(timer)
  timer = window.setInterval(() => {
    const remain = Math.max(0, Math.round((deadlineTs - Date.now()) / 1000))
    remainingTime.value = remain
    if (remain <= 0) {
      if (timer) clearInterval(timer)
      handleTimeout()
    }
  }, 500)
}

onMounted(() => {
  loadExamData()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (saveTimer) clearTimeout(saveTimer)
  // 离开页面前尽量保存一次进度
  flushSave()
})
</script>

<style scoped>
.exam-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fef2f2 0%, #f5f7fa 100%);
  padding-bottom: 80px;
}

.timer {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: white;
  background: rgba(0, 0, 0, 0.15);
  padding: 4px 12px;
  border-radius: 20px;
}

.timer.warning {
  background: #ef4444;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.timer-icon {
  margin-right: 4px;
}

.progress-header {
  background: white;
  padding: 12px 16px;
}

.question-progress {
  margin-bottom: 16px;
}

.progress-text {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
}

.progress-bar {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #f97316, #ea580c);
  border-radius: 3px;
  transition: width 0.3s;
}

.nav-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 6px;
}

.nav-item {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.nav-item.current {
  background: #3b82f6;
  color: white;
}

.nav-item.answered {
  background: #dcfce7;
  color: #15803d;
}

.nav-item.answered.current {
  background: #16a34a;
  color: white;
}

.question-container {
  padding: 16px;
}

.question-header {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.question-type {
  padding: 4px 10px;
  background: #fef3c7;
  color: #b45309;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.difficulty-tag {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
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

.question-content {
  font-size: 16px;
  line-height: 1.8;
  color: #1a1a2e;
  margin-bottom: 24px;
  white-space: pre-wrap;
}

.options-container {
  margin-bottom: 20px;
}

.options-container.locked {
  pointer-events: none;
  opacity: 0.7;
}

.option-item {
  display: flex;
  align-items: flex-start;
  padding: 14px 16px;
  background: white;
  border-radius: 12px;
  margin-bottom: 10px;
  border: 1px solid #e2e8f0;
  cursor: pointer;
}

.option-item.selected {
  border-color: #f97316;
  background: #fff7ed;
}

.option-key {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #f1f5f9;
  color: #475569;
  text-align: center;
  line-height: 28px;
  font-weight: 600;
  margin-right: 12px;
  flex-shrink: 0;
}

.selected .option-key {
  background: #f97316;
  color: white;
}

.option-content {
  flex: 1;
  font-size: 15px;
  color: #334155;
  line-height: 1.6;
}

.fill-blank-container {
  background: white;
  border-radius: 12px;
  padding: 16px;
}

.fill-input {
  font-size: 16px;
}

.nav-bottom {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: white;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
  display: flex;
  gap: 12px;
}

.nav-bottom .van-button {
  flex: 1;
}
</style>
