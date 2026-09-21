<template>
  <div class="analysis-page">
    <van-nav-bar title="学习分析" />

    <div class="page-content">
      <div class="overview-card">
        <div class="card-title">学习概览</div>
        <div class="overview-grid">
          <div class="overview-item">
            <div class="overview-value">{{ overview.total_practiced }}</div>
            <div class="overview-label">总练习题</div>
          </div>
          <div class="overview-item">
            <div class="overview-value accuracy">{{ overview.accuracy }}%</div>
            <div class="overview-label">正确率</div>
          </div>
          <div class="overview-item">
            <div class="overview-value exam">{{ overview.total_exams }}</div>
            <div class="overview-label">完成考试</div>
          </div>
          <div class="overview-item">
            <div class="overview-value avg">{{ overview.avg_exam_score }}</div>
            <div class="overview-label">平均分数</div>
          </div>
        </div>
      </div>

      <div class="chart-card">
        <div class="card-title">正确率趋势（近7天）</div>
        <div ref="trendChartRef" class="chart-container"></div>
      </div>

      <div class="chart-card">
        <div class="card-title">知识点掌握度</div>
        <div ref="radarChartRef" class="chart-container"></div>
      </div>

      <div class="weak-section">
        <div class="card-title">薄弱知识点</div>
        <div v-if="weakKnowledge.length > 0" class="weak-list">
          <div
            v-for="(item, index) in weakKnowledge"
            :key="item.knowledge_id"
            class="weak-item"
          >
            <div class="weak-rank" :class="'rank-' + (index + 1)">
              {{ index + 1 }}
            </div>
            <div class="weak-info">
              <div class="weak-name">{{ item.knowledge_name }}</div>
              <div class="weak-meta">错误 {{ item.error_count }} 次</div>
            </div>
            <van-button size="small" type="primary" @click="practiceWeak(item)">
              练习
            </van-button>
          </div>
        </div>
        <div v-else class="empty-weak">
          <div class="empty-icon">🎯</div>
          <div class="empty-text">暂无薄弱知识点，继续保持！</div>
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
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { showLoadingToast, closeToast } from 'vant'
import * as echarts from 'echarts'
import { getLearningOverview, getAccuracyTrend, getKnowledgeMastery } from '@/api/analysis'
import { getSubjects } from '@/api/knowledge'
import type {
  LearningOverview,
  AccuracyTrend,
  KnowledgeMastery,
  Subject
} from '@/types'

const router = useRouter()

const activeTab = ref(3)
const trendChartRef = ref<HTMLElement | null>(null)
const radarChartRef = ref<HTMLElement | null>(null)

let trendChart: echarts.ECharts | null = null
let radarChart: echarts.ECharts | null = null

const overview = ref<LearningOverview>({
  total_practiced: 0,
  total_correct: 0,
  accuracy: 0,
  total_exams: 0,
  avg_exam_score: 0,
  weak_knowledge: []
})

const trendData = ref<AccuracyTrend[]>([])
const masteryData = ref<KnowledgeMastery[]>([])
const subjects = ref<Subject[]>([])

const weakKnowledge = ref<{ knowledge_id: string; knowledge_name: string; error_count: number }[]>([])

const initTrendChart = () => {
  if (!trendChartRef.value) return

  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }

  const dates = trendData.value.map((d) => d.date)
  const accuracies = trendData.value.map((d) => d.accuracy)

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: '{b}<br/>正确率: {c}%'
    },
    grid: {
      left: '10%',
      right: '5%',
      top: '15%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisLabel: { color: '#64748b', fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
      axisLabel: { color: '#64748b', fontSize: 10, formatter: '{value}%' }
    },
    series: [
      {
        type: 'line',
        data: accuracies,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#3b82f6',
          width: 2
        },
        itemStyle: {
          color: '#3b82f6'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
          ])
        }
      }
    ]
  }

  trendChart.setOption(option)
}

const initRadarChart = () => {
  if (!radarChartRef.value) return

  if (!radarChart) {
    radarChart = echarts.init(radarChartRef.value)
  }

  const topMastery = masteryData.value.slice(0, 6)

  const indicator = topMastery.map((m) => ({
    name: m.knowledge_name.length > 6 ? m.knowledge_name.slice(0, 6) + '...' : m.knowledge_name,
    max: 100
  }))

  const values = topMastery.map((m) => m.mastery_rate)

  const option = {
    tooltip: {
      trigger: 'item'
    },
    radar: {
      indicator,
      axisName: {
        color: '#64748b',
        fontSize: 10
      },
      splitArea: {
        areaStyle: {
          color: ['#f8fafc', '#f1f5f9']
        }
      },
      splitLine: {
        lineStyle: {
          color: '#e2e8f0'
        }
      },
      axisLine: {
        lineStyle: {
          color: '#e2e8f0'
        }
      }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: '掌握度',
            areaStyle: {
              color: 'rgba(59, 130, 246, 0.3)'
            },
            lineStyle: {
              color: '#3b82f6',
              width: 2
            },
            itemStyle: {
              color: '#3b82f6'
            }
          }
        ]
      }
    ]
  }

  radarChart.setOption(option)
}

const practiceWeak = (item: { knowledge_id: string; knowledge_name: string }) => {
  router.push(
    `/practice/random?knowledgeIds=${item.knowledge_id}&count=10`
  )
}

const fetchData = async () => {
  showLoadingToast({ message: '加载中...', duration: 0 })
  try {
    const [overviewRes, trendRes, masteryRes, subjectsRes] = await Promise.all([
      getLearningOverview(),
      getAccuracyTrend(7),
      getKnowledgeMastery(),
      getSubjects()
    ])

    overview.value = overviewRes
    trendData.value = trendRes
    masteryData.value = masteryRes
    subjects.value = subjectsRes
    weakKnowledge.value = overviewRes.weak_knowledge.slice(0, 5)

    await nextTick()
    initTrendChart()
    initRadarChart()
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
.analysis-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f0f9ff 0%, #f5f7fa 100%);
  padding-bottom: 60px;
}

.page-content {
  padding: 16px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 16px;
}

.overview-card {
  background: white;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.overview-item {
  text-align: center;
}

.overview-value {
  font-size: 20px;
  font-weight: 700;
  color: #3b82f6;
  margin-bottom: 4px;
}

.overview-value.accuracy {
  color: #22c55e;
}

.overview-value.exam {
  color: #f97316;
}

.overview-value.avg {
  color: #8b5cf6;
}

.overview-label {
  font-size: 11px;
  color: #64748b;
}

.chart-card {
  background: white;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.chart-container {
  height: 220px;
  width: 100%;
}

.weak-section {
  background: white;
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.weak-list {
  margin-top: 8px;
}

.weak-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f1f5f9;
}

.weak-item:last-child {
  border-bottom: none;
}

.weak-rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  margin-right: 12px;
  flex-shrink: 0;
}

.weak-rank.rank-1 {
  background: #fef3c7;
  color: #b45309;
}

.weak-rank.rank-2 {
  background: #e2e8f0;
  color: #475569;
}

.weak-rank.rank-3 {
  background: #fed7aa;
  color: #9a3412;
}

.weak-info {
  flex: 1;
  min-width: 0;
}

.weak-name {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.weak-meta {
  font-size: 12px;
  color: #94a3b8;
}

.empty-weak {
  text-align: center;
  padding: 30px 20px;
}

.empty-icon {
  font-size: 40px;
  margin-bottom: 8px;
}

.empty-text {
  font-size: 13px;
  color: #64748b;
}
</style>
