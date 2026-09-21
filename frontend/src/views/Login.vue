<template>
  <div class="login-page">
    <div class="login-header">
      <div class="logo">📚</div>
      <h1 class="app-title">在线题库</h1>
      <p class="app-subtitle">高效刷题，轻松备考</p>
    </div>

    <div class="login-card">
      <van-tabs v-model:active="activeTab" class="login-tabs">
        <van-tab title="登录">
          <van-form @submit="handleLogin">
            <van-cell-group inset>
              <van-field
                v-model="loginForm.username"
                name="username"
                label="用户名"
                placeholder="请输入用户名"
                :rules="[{ required: true, message: '请输入用户名' }]"
              />
              <van-field
                v-model="loginForm.password"
                type="password"
                name="password"
                label="密码"
                placeholder="请输入密码"
                :rules="[{ required: true, message: '请输入密码' }]"
              />
            </van-cell-group>
            <div style="margin: 16px">
              <van-button round block type="primary" native-type="submit" :loading="loading">
                登录
              </van-button>
            </div>
          </van-form>

          <div class="demo-accounts">
            <p class="demo-title">演示账号</p>
            <p class="demo-item">管理员：admin / admin123</p>
            <p class="demo-item">学生：student / student123</p>
          </div>
        </van-tab>

        <van-tab title="注册">
          <van-form @submit="handleRegister">
            <van-cell-group inset>
              <van-field
                v-model="registerForm.username"
                name="username"
                label="用户名"
                placeholder="请输入用户名"
                :rules="[{ required: true, message: '请输入用户名' }]"
              />
              <van-field
                v-model="registerForm.email"
                name="email"
                label="邮箱"
                placeholder="请输入邮箱（选填）"
              />
              <van-field
                v-model="registerForm.password"
                type="password"
                name="password"
                label="密码"
                placeholder="请输入密码（至少6位）"
                :rules="[{ required: true, message: '请输入密码' }]"
              />
              <van-field
                v-model="registerForm.confirmPassword"
                type="password"
                name="confirmPassword"
                label="确认密码"
                placeholder="请再次输入密码"
                :rules="[{ required: true, message: '请确认密码' }]"
              />
            </van-cell-group>
            <div style="margin: 16px">
              <van-button round block type="primary" native-type="submit" :loading="loading">
                注册
              </van-button>
            </div>
          </van-form>
        </van-tab>
      </van-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { showToast } from 'vant'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const activeTab = ref(0)
const loading = ref(false)

const loginForm = reactive({
  username: 'student',
  password: 'student123'
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const handleLogin = async () => {
  try {
    loading.value = true
    await userStore.handleLogin(loginForm.username, loginForm.password)
    showToast('登录成功')
    router.push('/')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  if (registerForm.password !== registerForm.confirmPassword) {
    showToast('两次密码不一致')
    return
  }

  try {
    loading.value = true
    await userStore.handleRegister(
      registerForm.username,
      registerForm.password,
      registerForm.email || undefined
    )
    showToast('注册成功')
    router.push('/')
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #3b82f6 0%, #1d4ed8 50%, #f5f7fa 50%, #f5f7fa 100%);
  padding: 0 20px;
}

.login-header {
  padding-top: 80px;
  text-align: center;
  color: white;
}

.logo {
  width: 80px;
  height: 80px;
  background: white;
  border-radius: 20px;
  margin: 0 auto 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.app-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.app-subtitle {
  font-size: 14px;
  opacity: 0.9;
}

.login-card {
  margin-top: 40px;
  background: white;
  border-radius: 20px;
  padding: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.login-tabs {
  --van-tabbar-height: 60px;
}

.demo-accounts {
  margin-top: 24px;
  padding: 16px;
  background: #eff6ff;
  border-radius: 12px;
  margin-left: 16px;
  margin-right: 16px;
}

.demo-title {
  font-size: 13px;
  color: #1d4ed8;
  font-weight: 600;
  margin-bottom: 8px;
}

.demo-item {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}
</style>
