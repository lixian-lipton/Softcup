<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { getStats, healthCheck } from './api'
import { clearSession, currentUser, isAdmin, isLoggedIn } from './auth'

const route = useRoute()
const router = useRouter()
const health = ref(null)
const stats = ref({ total_chunks: 0, sources: [] })

const menus = computed(() => [
  { path: '/search', label: '智能检索', icon: 'Search' },
  { path: '/workflow', label: '作业指引', icon: 'List' },
  { path: '/knowledge', label: '知识管理', icon: 'Collection' },
])

const statusType = computed(() => (health.value?.status === 'ok' ? 'success' : 'danger'))
const sourceSummary = computed(() => {
  const manual = stats.value.sources?.find((s) => s.doc_type === 'manual')?.count || 0
  const cases = stats.value.sources?.find((s) => s.doc_type === 'case')?.count || 0
  return { manual, cases }
})
const isLoginPage = computed(() => route.path === '/login')
const llmLabel = computed(() => {
  const mode = health.value?.llm_mode
  if (mode === 'api') return '云端模型'
  if (mode === 'local') return '本地模型'
  if (mode === 'mock') return '内置应答'
  if (mode === 'offline') return '未连接'
  return mode || '-'
})
const statusLabel = computed(() => {
  if (health.value?.status === 'ok') return '正常'
  if (health.value?.status === 'offline') return '离线'
  return health.value?.status || '检查中'
})
const headerSubtitle = computed(() => route.meta.subtitle || '设备检修知识检索与作业平台')

async function refreshSystem() {
  try {
    const [{ data: healthData }, { data: statsData }] = await Promise.all([healthCheck(), getStats()])
    health.value = healthData
    stats.value = statsData
  } catch {
    health.value = { status: 'offline', llm_mode: 'offline', arch: '-' }
  }
}

function logout() {
  clearSession()
  router.replace('/login')
}

onMounted(() => {
  if (!isLoginPage.value) refreshSystem()
})
</script>

<template>
  <router-view v-if="isLoginPage" />

  <el-container v-else class="layout">
    <el-aside class="sidebar" width="248px">
      <div class="brand">
        <el-icon size="24"><Setting /></el-icon>
        <div>
          <strong>设备检修系统</strong>
          <span>知识检索与作业平台</span>
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
          <el-tag size="small" :type="statusType">{{ statusLabel }}</el-tag>
        </div>
        <div class="panel-row">
          <span>智能引擎</span>
          <strong>{{ llmLabel }}</strong>
        </div>
        <div class="panel-row" v-if="isLoggedIn">
          <span>当前用户</span>
          <strong>{{ currentUser?.username }}（{{ isAdmin ? '管理员' : '用户' }}）</strong>
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
          <h1>{{ route.meta.title || '工作台' }}</h1>
          <p>{{ headerSubtitle }}</p>
        </div>
        <div class="top-actions">
          <el-button size="small" :icon="Refresh" @click="refreshSystem">刷新状态</el-button>
          <el-button size="small" @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.top-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
