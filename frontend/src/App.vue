<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { changePassword, getStats, healthCheck } from './api'
import { clearSession, currentUser, isAdmin, isLoggedIn } from './auth'

const route = useRoute()
const router = useRouter()
const health = ref(null)
const stats = ref({ total_chunks: 0, sources: [] })
const pwdVisible = ref(false)
const pwdLoading = ref(false)
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

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

function openChangePassword() {
  pwdForm.old_password = ''
  pwdForm.new_password = ''
  pwdForm.confirm_password = ''
  pwdVisible.value = true
}

async function submitChangePassword() {
  if (!pwdForm.old_password || !pwdForm.new_password) {
    ElMessage.warning('请填写当前密码和新密码')
    return
  }
  if (pwdForm.new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (pwdForm.new_password !== pwdForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  pwdLoading.value = true
  try {
    await changePassword({
      old_password: pwdForm.old_password,
      new_password: pwdForm.new_password,
    })
    ElMessage.success('密码已修改')
    pwdVisible.value = false
  } catch (e) {
    const detail = e?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '修改失败，请重试')
  } finally {
    pwdLoading.value = false
  }
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
          <el-button size="small" @click="openChangePassword">修改密码</el-button>
          <el-button size="small" @click="logout">退出登录</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="pwdVisible" title="修改密码" width="420px" destroy-on-close>
    <el-form label-position="top" @submit.prevent="submitChangePassword">
      <el-form-item label="当前密码">
        <el-input v-model="pwdForm.old_password" type="password" show-password autocomplete="current-password" />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input
          v-model="pwdForm.new_password"
          type="password"
          show-password
          maxlength="64"
          placeholder="至少 6 位"
          autocomplete="new-password"
        />
      </el-form-item>
      <el-form-item label="确认新密码">
        <el-input
          v-model="pwdForm.confirm_password"
          type="password"
          show-password
          maxlength="64"
          autocomplete="new-password"
          @keyup.enter="submitChangePassword"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="pwdVisible = false">取消</el-button>
      <el-button type="primary" :loading="pwdLoading" @click="submitChangePassword">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.top-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
