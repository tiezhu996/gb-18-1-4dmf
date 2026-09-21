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

      <div class="options-container">
        <div
          v-if="currentQuestion.type === 'fill_blank'"
          class="fill-blank-container"
        >
          <van-field
            v-model="answers[currentQuestion.id]"
            placeholder="请输入答案"
            :border="false"
            class="fill-input"
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
        @click="handleNextOrSubmit"
      >
        {{ currentIndex === questions.length - 1 ? '交卷' : '下一题' }}
      </van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showConfirmDialog, showLoadingToast, closeToast, showToast } from 'vant'
import { submitExam } from '@/api/exam'
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
const remainingTime = ref(3600)
const submitting = ref(false)
let timer: number | null = null

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
  submitting.value = true
  showLoadingToast({ message: '正在交卷...', duration: 0 })
  try {
    const submitAnswers = getSubmitAnswers()
    const result = await submitExam(sessionId.value, submitAnswers)
    closeToast()
    router.push(`/exam-result/${result.id}`)
  } catch (error) {
    console.error(error)
    closeToast()
    showToast('交卷失败，请重试')
  } finally {
    submitting.value = false
  }
}

const handleBack = () => {
  showConfirmDialog({
    title: '确认退出',
    message: '退出后考试进度将丢失，确定要退出吗？'
  })
    .then(() => {
      if (timer) clearInterval(timer)
      router.push('/')
    })
    .catch(() => {})
}

const loadExamData = () => {
  const stored = localStorage.getItem(`exam_${sessionId.value}`)
  if (stored) {
    try {
      const data = JSON.parse(stored)
      examName.value = data.name
      questions.value = data.questions
      durationMinutes.value = data.duration_minutes
      remainingTime.value = data.remaining_time
    } catch (e) {
      console.error(e)
      router.push('/')
    }
  } else {
    router.push('/')
  }
}

const startTimer = () => {
  timer = window.setInterval(() => {
    if (remainingTime.value > 0) {
      remainingTime.value--
      localStorage.setItem(
        `exam_${sessionId.value}`,
        JSON.stringify({
          name: examName.value,
          questions: questions.value,
          duration_minutes: durationMinutes.value,
          remaining_time: remainingTime.value
        })
      )
    } else {
      if (timer) clearInterval(timer)
      showToast('考试时间已到')
      doSubmit()
    }
  }, 1000)
}

onMounted(() => {
  loadExamData()
  startTimer()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
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
