<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api'
import { setSession } from '../auth'

const router = useRouter()
const mode = ref('login')
const loginAs = ref('user')
const username = ref('')
const password = ref('')
const loading = ref(false)

watch(mode, (m) => {
  if (m === 'register') loginAs.value = 'user'
})

async function submit() {
  if (!username.value.trim() || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (mode.value === 'register' && password.value.length < 6) {
    ElMessage.warning('注册密码至少 6 位')
    return
  }
  loading.value = true
  try {
    if (mode.value === 'register') {
      const { data } = await register({
        username: username.value.trim(),
        password: password.value,
      })
      setSession(data.access_token, data.user)
      ElMessage.success('注册成功')
    } else {
      const { data } = await login({
        username: username.value.trim(),
        password: password.value,
        login_as: loginAs.value,
      })
      setSession(data.access_token, data.user)
      ElMessage.success('登录成功')
    }
    router.replace('/search')
  } catch (e) {
    const status = e?.response?.status
    const detail = e?.response?.data?.detail
    if (status === 405 || status === 404) {
      ElMessage.error('登录服务暂不可用，请稍后重试或联系管理员')
    } else if (typeof detail === 'string') {
      ElMessage.error(detail)
    } else {
      ElMessage.error('登录失败，请检查账号密码后重试')
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-atmosphere" aria-hidden="true" />
    <section class="login-shell">
      <aside class="login-hero">
        <img src="/brand-icon.png" alt="" class="hero-icon" @error="($e) => ($e.target.style.display = 'none')" />
        <h1>设备检修系统</h1>
        <p>面向现场检修的知识检索、作业指引与经验沉淀平台</p>
        <ul>
          <li>多模态故障检索</li>
          <li>标准化作业指引</li>
          <li>案例审核与知识入库</li>
        </ul>
      </aside>

      <div class="login-card">
        <div class="card-head">
          <h2>{{ mode === 'login' ? '欢迎回来' : '创建账号' }}</h2>
          <p>{{ mode === 'login' ? '请选择身份并登录系统' : '注册后以普通用户身份使用' }}</p>
        </div>

        <el-segmented
          v-model="mode"
          :options="[
            { label: '登录', value: 'login' },
            { label: '注册', value: 'register' },
          ]"
          block
          class="mode-switch"
        />

        <el-form label-position="top" @submit.prevent="submit">
          <el-form-item v-if="mode === 'login'" label="登录身份">
            <el-segmented
              v-model="loginAs"
              :options="[
                { label: '普通用户', value: 'user' },
                { label: '管理员', value: 'admin' },
              ]"
              block
            />
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="username" maxlength="32" placeholder="请输入用户名" autocomplete="username" size="large" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="password"
              type="password"
              show-password
              maxlength="64"
              size="large"
              :placeholder="mode === 'register' ? '至少 6 位' : '请输入密码'"
              autocomplete="current-password"
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-button type="primary" class="submit-btn" size="large" :loading="loading" @click="submit">
            {{ mode === 'login' ? '进入系统' : '注册并进入' }}
          </el-button>
        </el-form>

        <p v-if="mode === 'register'" class="hint">注册账号为普通用户，管理员账号由系统管理员分配。</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 20px;
  position: relative;
  overflow: hidden;
}

.login-atmosphere {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 20%, rgba(31, 122, 90, 0.28), transparent 34%),
    radial-gradient(circle at 82% 12%, rgba(22, 58, 82, 0.22), transparent 32%),
    linear-gradient(145deg, #0f2a3d 0%, #163a52 42%, #1a4a3a 100%);
  z-index: 0;
}

.login-atmosphere::after {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.22;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(circle at 40% 40%, #000 20%, transparent 75%);
  animation: grid-drift 18s linear infinite;
}

@keyframes grid-drift {
  from {
    transform: translate3d(0, 0, 0);
  }
  to {
    transform: translate3d(-48px, -48px, 0);
  }
}

.login-shell {
  position: relative;
  z-index: 1;
  width: min(920px, 100%);
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.14);
  box-shadow: 0 24px 60px rgba(6, 18, 28, 0.35);
  animation: shell-in 0.45s ease both;
}

@keyframes shell-in {
  from {
    opacity: 0;
    transform: translateY(14px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.login-hero {
  padding: 42px 36px;
  color: #f3faf7;
  background:
    linear-gradient(160deg, rgba(31, 122, 90, 0.35), transparent 55%),
    linear-gradient(180deg, rgba(15, 42, 61, 0.2), rgba(15, 42, 61, 0.55));
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.hero-icon {
  width: 72px;
  height: 72px;
  object-fit: contain;
  border-radius: 16px;
  margin-bottom: 18px;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.login-hero h1 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(28px, 3.2vw, 36px);
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.2;
}

.login-hero > p {
  margin: 12px 0 0;
  color: rgba(243, 250, 247, 0.78);
  line-height: 1.65;
  font-size: 14px;
  max-width: 28em;
}

.login-hero ul {
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 10px;
}

.login-hero li {
  position: relative;
  padding-left: 18px;
  color: rgba(243, 250, 247, 0.88);
  font-size: 13px;
}

.login-hero li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.55em;
  width: 7px;
  height: 7px;
  border-radius: 2px;
  background: #4ecf9a;
}

.login-card {
  background: #fff;
  padding: 36px 32px 28px;
}

.card-head {
  margin-bottom: 18px;
}

.card-head h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 24px;
  color: var(--ink);
}

.card-head p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.mode-switch {
  margin-bottom: 18px;
}

.submit-btn {
  width: 100%;
  margin-top: 4px;
}

.hint {
  margin: 16px 0 0;
  text-align: center;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 820px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .login-hero {
    padding: 28px 24px 20px;
  }

  .login-hero ul {
    grid-template-columns: 1fr;
    margin-top: 18px;
  }

  .login-card {
    padding: 24px 20px 20px;
  }
}
</style>
