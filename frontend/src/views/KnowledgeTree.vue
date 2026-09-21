<template>
  <div class="page-container">
    <van-nav-bar :title="subjectName" left-arrow @click-left="router.back()" />

    <div class="page-content">
      <van-search
        v-model="searchKeyword"
        placeholder="搜索知识点"
        background="transparent"
        shape="round"
        @search="handleSearch"
      />

      <div v-if="loading" class="loading-container">
        <van-loading />
      </div>

      <div v-else-if="searchResults.length > 0" class="search-results">
        <div class="section-title">搜索结果</div>
        <div
          v-for="node in searchResults"
          :key="node.id"
          class="knowledge-item"
          @click="selectKnowledge(node)"
        >
          <span class="knowledge-name">{{ node.name }}</span>
          <span class="knowledge-count">{{ node.question_count }} 题</span>
        </div>
      </div>

      <div v-else class="knowledge-tree">
        <div v-for="(chapter, cIndex) in knowledgeTree" :key="chapter.id">
          <div class="tree-item level-1" @click="toggleChapter(cIndex)">
            <van-icon :name="expandedChapters.includes(cIndex) ? 'arrow-down' : 'arrow'" />
            <span class="tree-name">{{ chapter.name }}</span>
            <span class="tree-count">{{ chapter.question_count }} 题</span>
          </div>

          <div v-show="expandedChapters.includes(cIndex)">
            <div
              v-for="(section, sIndex) in chapter.children"
              :key="section.id"
            >
              <div
                class="tree-item level-2"
                @click="toggleSection(cIndex, sIndex)"
              >
                <van-icon :name="isSectionExpanded(cIndex, sIndex) ? 'arrow-down' : 'arrow'" />
                <span class="tree-name">{{ section.name }}</span>
                <span class="tree-count">{{ section.question_count }} 题</span>
              </div>

              <div v-show="isSectionExpanded(cIndex, sIndex)">
                <div
                  v-for="point in section.children"
                  :key="point.id"
                  class="tree-item level-3 clickable"
                  @click="selectKnowledge(point)"
                >
                  <span class="tree-dot"></span>
                  <span class="tree-name">{{ point.name }}</span>
                  <span class="tree-count">{{ point.question_count }} 题</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="practice-options card">
        <div class="section-title">练习模式</div>
        <div class="mode-grid">
          <div class="mode-item" @click="startPractice('sequential')">
            <div class="mode-icon">📖</div>
            <span class="mode-name">顺序练习</span>
            <span class="mode-desc">按知识点顺序刷题</span>
          </div>
          <div class="mode-item" @click="startPractice('random')">
            <div class="mode-icon">🎲</div>
            <span class="mode-name">随机练习</span>
            <span class="mode-desc">随机抽取题目练习</span>
          </div>
        </div>
      </div>
    </div>

    <van-popup
      v-model:show="showModeSelector"
      position="bottom"
      :style="{ height: '60%' }"
      round
    >
      <div class="mode-selector">
        <div class="selector-header">
          <div class="selector-title">选择练习配置</div>
          <van-icon name="cross" @click="showModeSelector = false" />
        </div>

        <div class="selector-content">
          <div class="selector-item">
            <div class="selector-label">题目数量</div>
            <van-radio-group v-model="selectedCount">
              <van-radio name="10">10 题</van-radio>
              <van-radio name="20">20 题</van-radio>
              <van-radio name="50">50 题</van-radio>
            </van-radio-group>
          </div>

          <div class="selector-item">
            <div class="selector-label">难度范围</div>
            <van-radio-group v-model="selectedDifficulty">
              <van-radio name="">全部难度</van-radio>
              <van-radio name="easy">简单</van-radio>
              <van-radio name="medium">中等</van-radio>
              <van-radio name="hard">困难</van-radio>
            </van-radio-group>
          </div>
        </div>

        <div class="selector-footer">
          <van-button block type="primary" round @click="confirmStartPractice">
            开始练习
          </van-button>
        </div>
      </div>
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showLoadingToast, closeToast, showToast } from 'vant'
import { getKnowledgeTree, searchKnowledge } from '@/api/knowledge'
import { getSubjects } from '@/api/knowledge'
import type { KnowledgeNode, Subject } from '@/types'

const route = useRoute()
const router = useRouter()

const subjectId = computed(() => route.params.subjectId as string)

const loading = ref(true)
const searchKeyword = ref('')
const subjectName = ref('')
const knowledgeTree = ref<KnowledgeNode[]>([])
const searchResults = ref<KnowledgeNode[]>([])
const expandedChapters = ref<number[]>([0])
const expandedSections = ref<Record<string, boolean>>({})

const showModeSelector = ref(false)
const selectedMode = ref('')
const selectedKnowledge = ref<KnowledgeNode | null>(null)
const selectedCount = ref('10')
const selectedDifficulty = ref('')

const fetchData = async () => {
  try {
    showLoadingToast({ message: '加载中...', duration: 0 })
    const [subjects, tree] = await Promise.all([
      getSubjects(),
      getKnowledgeTree(subjectId.value)
    ])

    const subject = subjects.find((s: Subject) => s.id === subjectId.value)
    subjectName.value = subject?.name || '题库'
    knowledgeTree.value = tree
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
    closeToast()
  }
}

const toggleChapter = (index: number) => {
  const i = expandedChapters.value.indexOf(index)
  if (i > -1) {
    expandedChapters.value.splice(i, 1)
  } else {
    expandedChapters.value.push(index)
  }
}

const isSectionExpanded = (cIndex: number, sIndex: number) => {
  return expandedSections.value[`${cIndex}-${sIndex}`]
}

const toggleSection = (cIndex: number, sIndex: number) => {
  const key = `${cIndex}-${sIndex}`
  expandedSections.value[key] = !expandedSections.value[key]
}

const handleSearch = async () => {
  if (!searchKeyword.value.trim()) {
    searchResults.value = []
    return
  }

  try {
    searchResults.value = await searchKnowledge(subjectId.value, searchKeyword.value.trim())
  } catch (error) {
    console.error(error)
  }
}

const selectKnowledge = (node: KnowledgeNode) => {
  if (node.question_count === 0) {
    showToast('该知识点下暂无题目')
    return
  }
  selectedKnowledge.value = node
  showModeSelector.value = true
}

const startPractice = (mode: string) => {
  selectedMode.value = mode
  selectedKnowledge.value = null
  showModeSelector.value = true
}

const confirmStartPractice = () => {
  showModeSelector.value = false

  router.push({
    path: `/practice/${selectedMode.value}`,
    query: {
      subjectId: subjectId.value,
      knowledgeIds: selectedKnowledge.value?.id || '',
      count: selectedCount.value,
      difficulty: selectedDifficulty.value
    }
  })
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.tree-item {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  background: white;
  border-radius: 10px;
  margin-bottom: 8px;
  cursor: pointer;
}

.tree-item.level-1 {
  font-weight: 600;
  color: #1a1a2e;
  background: #f8fafc;
}

.tree-item.level-2 {
  margin-left: 16px;
  color: #334155;
}

.tree-item.level-3 {
  margin-left: 32px;
  color: #64748b;
  background: #fefefe;
}

.tree-item.clickable:active {
  background: #eff6ff;
}

.tree-name {
  flex: 1;
  font-size: 15px;
  margin-left: 8px;
}

.tree-count {
  font-size: 12px;
  color: #94a3b8;
}

.tree-dot {
  width: 6px;
  height: 6px;
  background: #3b82f6;
  border-radius: 50%;
  margin-left: 8px;
}

.knowledge-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: white;
  border-radius: 10px;
  margin-bottom: 8px;
}

.knowledge-name {
  font-size: 15px;
  color: #1a1a2e;
}

.knowledge-count {
  font-size: 12px;
  color: #3b82f6;
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 8px;
}

.mode-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 12px;
  background: #f8fafc;
  border-radius: 14px;
  cursor: pointer;
}

.mode-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.mode-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.mode-desc {
  font-size: 12px;
  color: #94a3b8;
}

.mode-selector {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #f1f5f9;
}

.selector-title {
  font-size: 16px;
  font-weight: 600;
}

.selector-content {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.selector-item {
  margin-bottom: 24px;
}

.selector-label {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 12px;
}

.selector-footer {
  padding: 16px;
  border-top: 1px solid #f1f5f9;
}
</style>
