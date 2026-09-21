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
            :readonly="locked"
          />
        </div>

        <template v-else>
          <div
            v-for="option in displayOptions"
            :key="option.key"
            class="option-item"
            :class="{ selected: isOptionSelected(option.key), disabled: locked }"
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
        :disabled="currentIndex === 0 || locked"
        @click="goPrev"
      >
        上一题
      </van-button>

      <van-button
        type="primary"
        size="large"
        :loading="submitting"
        :disabled="locked"
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
import {
  submitExam,
  saveExamAnswers,
  getExamState
} from '@/api/exam'
import type { Question } from '@/types'

const route = useRoute()
const router = useRouter()

const sessionId = computed(() => route.params.sessionId as string)
const storageKey = computed(() => `exam_${sessionId.value}`)

const examName = ref('模拟考试')
const questions = ref<Question[]>([])
const currentIndex = ref(0)
// 统一答案格式：单选/判断为字符串，多选为字符串数组，填空为字符串；未作答为 null
const answers = reactive<Record<string, any>>({})
const durationMinutes = ref(60)
const remainingTime = ref(0)
const submitting = ref(false)
const locked = ref(false)
const initialized = ref(false)

let timer: number | null = null
let saveTimer: number | null = null
let lastSavedAt = 0
let serverDeadlineMs = 0
const LOCAL_SAVE_DELAY = 800

const currentQuestion = computed(() => questions.value[currentIndex.value] || null)

// 判断题种子数据可能没有 options，补默认的“正确/错误”（答案键沿用 A/B）
const TF_OPTIONS = [
  { key: 'A', content: '正确' },
  { key: 'B', content: '错误' }
]

const displayOptions = computed(() => {
  const q = currentQuestion.value
  if (!q) return []
  if (q.type === 'true_false' && !q.options?.length) return TF_OPTIONS
  return q.options || []
})

const progressPercent = computed(() => {
  if (!questions.value.length) return 0
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
  const safe = Math.max(0, seconds)
  const m = Math.floor(safe / 60)
  const s = safe % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const isAnswered = (qid: string) => {
  const val = answers[qid]
  return val !== undefined && val !== null && val !== '' && !(Array.isArray(val) && val.length === 0)
}

const isOptionSelected = (key: string) => {
  const qid = currentQuestion.value?.id
  if (!qid) return false
  const val = answers[qid]
  if (currentQuestion.value?.type === 'multiple_choice') {
    return Array.isArray(val) && val.includes(key)
  }
  return val === key
}

const getNavItemClass = (index: number) => {
  const classes: string[] = []
  const qid = questions.value[index]?.id

  if (index === currentIndex.value) {
    classes.push('current')
  }
  if (qid && isAnswered(qid)) {
    classes.push('answered')
  }
  return classes
}

const selectOption = (key: string) => {
  if (locked.value) return
  const qid = currentQuestion.value?.id
  if (!qid) return

  if (currentQuestion.value?.type === 'multiple_choice') {
    const list: string[] = Array.isArray(answers[qid]) ? [...answers[qid]] : []
    const idx = list.indexOf(key)
    if (idx > -1) {
      list.splice(idx, 1)
    } else {
      list.push(key)
    }
    answers[qid] = list.sort()
  } else {
    answers[qid] = key
  }
}

const goToQuestion = (index: number) => {
  if (locked.value) return
  currentIndex.value = index
}

const goPrev = () => {
  if (currentIndex.value > 0) {
    currentIndex.value--
  }
}

const handleNextOrSubmit = () => {
  if (locked.value) return
  if (currentIndex.value === questions.value.length - 1) {
    confirmSubmit()
  } else {
    currentIndex.value++
  }
}

const getSubmitAnswers = () => {
  const result: Record<string, any> = {}
  questions.value.forEach((q) => {
    const val = answers[q.id]
    if (q.type === 'multiple_choice') {
      result[q.id] = Array.isArray(val) ? [...val] : []
    } else {
      result[q.id] = val ?? null
    }
  })
  return result
}

const persistLocal = () => {
  if (!initialized.value || !questions.value.length) return
  localStorage.setItem(
    storageKey.value,
    JSON.stringify({
      name: examName.value,
      questions: questions.value,
      duration_minutes: durationMinutes.value,
      current_index: currentIndex.value,
      answers: { ...answers },
      deadline_ms: serverDeadlineMs || undefined
    })
  )
}

// 答案变化：立即本地落盘（防刷新丢失），远程自动保存做防抖/节流
watch(
  answers,
  () => {
    if (!initialized.value || locked.value) return
    persistLocal()
    scheduleRemoteSave()
  },
  { deep: true }
)

const scheduleRemoteSave = () => {
  const now = Date.now()
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  const wait = Math.max(0, LOCAL_SAVE_DELAY - (now - lastSavedAt))
  saveTimer = window.setTimeout(() => {
    saveTimer = null
    flushAnswers(true)
  }, wait)
}

const flushAnswers = async (silent: boolean = false) => {
  if (!questions.value.length) return getSubmitAnswers()
  const payload = getSubmitAnswers()
  try {
    const res = await saveExamAnswers(sessionId.value, payload, silent)
    lastSavedAt = Date.now()
    if (res?.is_submitted) {
      goToResult()
    }
  } catch (e) {
    // 静默自动保存失败不打断答题，本地已留存，到点/下次还会重试
    console.warn('答案自动保存失败', e)
  }
  return payload
}

const goToResult = () => {
  if (timer) clearInterval(timer)
  if (saveTimer) clearTimeout(saveTimer)
  localStorage.removeItem(storageKey.value)
  locked.value = true
  router.replace(`/exam-result/${sessionId.value}`)
}

const confirmSubmit = () => {
  const unanswered = questions.value.filter((q) => !isAnswered(q.id)).length
  const message = unanswered > 0
    ? `还有 ${unanswered} 道题未作答，确定要交卷吗？`
    : '确定要交卷吗？'

  showConfirmDialog({
    title: '确认交卷',
    message
  })
    .then(() => doSubmit(false))
    .catch(() => {})
}

const doSubmit = async (auto: boolean) => {
  if (submitting.value || locked.value) return
  submitting.value = true
  if (!auto) showLoadingToast({ message: '正在交卷...', duration: 0 })
  try {
    const payload = await flushAnswers(true)
    try {
      const result = await submitExam(sessionId.value, payload)
      closeToast()
      void result
      goToResult()
      return
    } catch (err: any) {
      // 到点自动交卷时后端可能已完成惰性结算，直接进结果页由结果接口读取首次报告
      const already = err?.response?.data?.detail || ''
      if (auto || String(already).includes('提交') || String(already).includes('结算')) {
        closeToast()
        goToResult()
        return
      }
      closeToast()
      showToast('交卷失败，请重试')
      submitting.value = false
    }
  } catch (e) {
    closeToast()
    showToast('交卷失败，请重试')
    submitting.value = false
  }
}

const handleBack = () => {
  showConfirmDialog({
    title: '确认退出',
    message: '退出后考试仍在计时，确定要退出吗？'
  })
    .then(() => {
      flushAnswers(true)
      router.push('/')
    })
    .catch(() => {})
}

// 页面隐藏（切后台/关页面）时尽力同步一次已保存答案
const handlePageHide = () => {
  if (!questions.value.length || locked.value) return
  let token = ''
  try {
    token = JSON.parse(localStorage.getItem('user-store') || '{}')?.token || ''
  } catch {
    token = ''
  }
  try {
    const payload = JSON.stringify({
      session_id: sessionId.value,
      answers: getSubmitAnswers()
    })
    // sendBeacon 无法自定义鉴权头，改用 keepalive 的 fetch；失败则依赖到点后台惰性结算
    fetch('/api/exam/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: payload,
      keepalive: true
    }).catch(() => {})
  } catch {
    /* 忽略：本地已留存，到点后台也会按已保存答案结算 */
  }
  persistLocal()
}

// 记录答题位置，便于刷新恢复
watch(currentIndex, persistLocal)

const applyAnswers = (saved: Record<string, any> | undefined) => {
  questions.value.forEach((q) => {
    const val = saved?.[q.id]
    if (val !== undefined && val !== null) {
      answers[q.id] = q.type === 'multiple_choice'
        ? (Array.isArray(val) ? [...val].sort() : [])
        : val
    } else if (q.type === 'multiple_choice') {
      answers[q.id] = []
    }
  })
}

const initFromServer = async () => {
  const state = await getExamState(sessionId.value)
  examName.value = state.name || '模拟考试'
  durationMinutes.value = state.duration_minutes

  if (state.is_submitted) {
    // 已交卷（含到点自动结算）：直接显示结果
    router.replace(`/exam-result/${sessionId.value}`)
    return false
  }

  questions.value = state.questions || []
  if (!questions.value.length) {
    showToast('试卷加载失败')
    router.push('/')
    return false
  }

  applyAnswers(state.saved_answers)

  // 服务端时间为准计算截止时刻，防止本地倒计时/刷新作弊
  const nowMs = Date.now()
  serverDeadlineMs = nowMs + state.remaining_seconds * 1000
  remainingTime.value = state.remaining_seconds

  // 恢复答题位置（仅本地保留）
  const stored = localStorage.getItem(storageKey.value)
  if (stored) {
    try {
      const local = JSON.parse(stored)
      if (Array.isArray(local.questions) && local.questions.length === questions.value.length) {
        currentIndex.value = Math.min(local.current_index || 0, questions.value.length - 1)
        // 本地比服务端更新的答案先保留，稍后再同步
        if (local.answers) {
          Object.keys(local.answers).forEach((qid) => {
            const v = local.answers[qid]
            if (v !== undefined && v !== null && !(Array.isArray(v) && v.length === 0)) {
              answers[qid] = v
            }
          })
        }
      }
    } catch {
      /* 本地缓存损坏则忽略 */
    }
  }

  initialized.value = true
  persistLocal()
  return true
}

const initFromLocal = () => {
  // 网络失败时的兜底：用本地缓存继续答题，截止时间也以本地记录为准
  const stored = localStorage.getItem(storageKey.value)
  if (!stored) {
    showToast('考试信息加载失败，请检查网络')
    router.push('/')
    return false
  }
  try {
    const data = JSON.parse(stored)
    examName.value = data.name
    questions.value = data.questions
    durationMinutes.value = data.duration_minutes
    applyAnswers(data.answers)
    if (data.deadline_ms) {
      serverDeadlineMs = data.deadline_ms
      remainingTime.value = Math.max(0, Math.round((serverDeadlineMs - Date.now()) / 1000))
    } else {
      // 首次离线进入（极少见），按整卷时长计时
      remainingTime.value = durationMinutes.value * 60
      serverDeadlineMs = Date.now() + remainingTime.value * 1000
    }
    initialized.value = true
    persistLocal()
    return true
  } catch (e) {
    console.error(e)
    router.push('/')
    return false
  }
}

const startTimer = () => {
  const tick = () => {
    const left = Math.max(0, Math.round((serverDeadlineMs - Date.now()) / 1000))
    remainingTime.value = left
    if (left <= 0) {
      handleTimeUp()
    }
  }
  tick()
  timer = window.setInterval(tick, 1000)
}

const handleTimeUp = () => {
  if (locked.value) return
  locked.value = true
  if (timer) clearInterval(timer)
  if (saveTimer) clearTimeout(saveTimer)
  persistLocal()
  showToast('考试时间已到，自动交卷')
  doSubmit(true)
}

onMounted(async () => {
  showLoadingToast({ message: '加载中...', duration: 0 })
  let ok = false
  try {
    ok = await initFromServer()
  } catch (e) {
    console.error(e)
    ok = initFromLocal()
  }
  closeToast()
  if (ok) {
    startTimer()
    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener('pagehide', handlePageHide)
    // 把本地比服务端更新的答案补同步一次（恢复本地缓存时可能存在差异）
    flushAnswers(true)
  }
})

const onVisibilityChange = () => {
  if (document.visibilityState === 'hidden') {
    handlePageHide()
  }
}

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (saveTimer) clearTimeout(saveTimer)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  window.removeEventListener('pagehide', handlePageHide)
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

.option-item.disabled {
  cursor: not-allowed;
  opacity: 0.85;
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
