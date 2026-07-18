<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { getStats, healthCheck } from './api'

const route = useRoute()
const health = ref(null)
const stats = ref({ total_chunks: 0, sources: [] })

const menus = [
  { path: '/search', label: '智能检索', icon: 'Search' },
  { path: '/workflow', label: '作业指引', icon: 'List' },
  { path: '/knowledge', label: '知识管理', icon: 'Collection' },
]

const statusType = computed(() => (health.value?.status === 'ok' ? 'success' : 'danger'))
const sourceSummary = computed(() => {
  const manual = stats.value.sources?.find((s) => s.doc_type === 'manual')?.count || 0
  const cases = stats.value.sources?.find((s) => s.doc_type === 'case')?.count || 0
  return { manual, cases }
})

async function refreshSystem() {
  try {
    const [{ data: healthData }, { data: statsData }] = await Promise.all([healthCheck(), getStats()])
    health.value = healthData
    stats.value = statsData
  } catch {
    health.value = { status: 'offline', llm_mode: 'offline', arch: '-', note: '后端未启动' }
  }
}

onMounted(refreshSystem)
</script>

<template>
  <el-container class="layout">
    <el-aside class="sidebar" width="248px">
      <div class="brand">
        <el-icon size="24"><Setting /></el-icon>
        <div>
          <strong>设备检修助手</strong>
          <span>Soft Cup A1</span>
        </div>
      </div>

      <el-menu :default-active="route.path" router class="side-menu">
        <el-menu-item v-for="m in menus" :key="m.path" :index="m.path">
          <el-icon><component :is="m.icon" /></el-icon>
          <span>{{ m.label }}</span>
        </el-menu-item>
      </el-menu>

      <div class="system-panel">
        <div class="panel-row">
          <span>服务</span>
          <el-tag size="small" :type="statusType">{{ health?.status || 'checking' }}</el-tag>
        </div>
        <div class="panel-row">
          <span>LLM</span>
          <strong>{{ health?.llm_mode || '-' }}</strong>
        </div>
        <div class="panel-row">
          <span>架构</span>
          <strong>{{ health?.arch || '-' }}</strong>
        </div>
        <div class="metric-grid">
          <div>
            <strong>{{ sourceSummary.manual }}</strong>
            <span>手册片段</span>
          </div>
          <div>
            <strong>{{ sourceSummary.cases }}</strong>
            <span>案例片段</span>
          </div>
        </div>
      </div>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div>
          <h1>{{ route.meta.title || '智能检修工作台' }}</h1>
          <p>{{ health?.note || '正在读取系统状态' }}</p>
        </div>
        <el-button size="small" :icon="Refresh" @click="refreshSystem">刷新状态</el-button>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
