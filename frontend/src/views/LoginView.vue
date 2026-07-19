<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../api'
import { setSession } from '../auth'

const router = useRouter()
const mode = ref('login')
const username = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value.trim() || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const apiFn = mode.value === 'login' ? login : register
    const { data } = await apiFn({
      username: username.value.trim(),
      password: password.value,
    })
    setSession(data.access_token, data.user)
    ElMessage.success(mode.value === 'login' ? '登录成功' : '注册成功')
    router.replace('/search')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <section class="login-card">
      <div class="brand-block">
        <img src="/brand-icon.png" alt="设备检修系统" class="brand-icon" @error="($e) => ($e.target.style.display='none')" />
        <h1>设备检修系统</h1>
        <p>登录后使用检索、作业指引与知识沉淀</p>
      </div>

      <el-segmented
        v-model="mode"
        :options="[
          { label: '登录', value: 'login' },
          { label: '注册', value: 'register' },
        ]"
        block
        style="margin-bottom: 18px"
      />

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="username" maxlength="32" placeholder="普通用户可注册；管理员用 admin" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" show-password maxlength="64" placeholder="至少 6 位" @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" style="width: 100%" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登录' : '注册并进入' }}
        </el-button>
      </el-form>

      <p class="hint">默认管理员：admin / 123456（仅演示，请部署后修改）</p>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 20% 20%, rgba(47, 128, 237, 0.18), transparent 40%),
    radial-gradient(circle at 80% 10%, rgba(39, 174, 96, 0.12), transparent 35%),
    linear-gradient(160deg, #f4f7fb 0%, #e8eef6 100%);
}
.login-card {
  width: min(420px, 100%);
  background: #fff;
  border: 1px solid #d9e2ec;
  border-radius: 14px;
  padding: 28px 24px 20px;
  box-shadow: 0 12px 40px rgba(23, 50, 77, 0.08);
}
.brand-block {
  text-align: center;
  margin-bottom: 18px;
}
.brand-icon {
  width: 72px;
  height: 72px;
  object-fit: contain;
  margin-bottom: 8px;
}
.brand-block h1 {
  margin: 0;
  font-size: 24px;
  color: #17324d;
}
.brand-block p,
.hint {
  color: #607087;
  font-size: 13px;
}
.hint {
  margin-top: 16px;
  text-align: center;
}
</style>
