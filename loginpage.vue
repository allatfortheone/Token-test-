<template>
  <div class="container">
    <div class="inner">
      <img :src="logo" alt="Team Logo" class="logo" />
      <h1 class="title"><span class="red">Robo Raiders</span><span class="white">: Login</span></h1>

      <div class="inputContainer">
        <label class="label">Username</label>
        <input
          class="input"
          v-model="username"
          placeholder="Enter your username"
          @keydown="lightHaptic"
          autocomplete="username"
        />
      </div>

      <div class="inputContainer">
        <label class="label">Password</label>
        <div class="passwordContainer">
          <input
            class="passwordInput"
            :type="showPassword ? 'text' : 'password'"
            v-model="password"
            placeholder="Enter your password"
            @keydown="lightHaptic"
            autocomplete="current-password"
          />
          <button class="eyeButton" @click="toggleShow">
            <span class="eyeIcon">{{ showPassword ? '🚫👁️‍🗨️' : '👁️‍🗨️' }}</span>
          </button>
        </div>
      </div>

      <button class="loginButton" @click="handleLogin">Login</button>

      <button class="registerRedirectButton" @click="goRegister">
        Don't have an account? Register here
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRuntimeConfig, useCookie } from '#imports'
import logo from '~/assets/Team75LogoVUSE.png'

const router = useRouter()
const config = useRuntimeConfig()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const ACCESS_COOKIE = 'ACCESS_TOKEN'

// small helper to attempt a haptic effect on supporting devices
function lightHaptic() {
  if (navigator.vibrate) navigator.vibrate(10)
}

function toggleShow() {
  showPassword.value = !showPassword.value
  if (navigator.vibrate) navigator.vibrate(30)
}

async function handleLogin() {
  try {
    // build URL from runtime config public.apiBase
    const url = `${config.public.apiBase.replace(/\/$/, '')}/login`
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.value, password: password.value })
    })

    const data = await res.json().catch(() => ({}))

    if (!res.ok) {
      // error feedback
      if (navigator.vibrate) navigator.vibrate([50, 30, 50])
      alert(data.message || 'Login failed')
      return
    }

    const token = data.access_token
    if (!token) {
      alert(data.message || 'No access token returned')
      return
    }

    // store token in a cookie (client-side) and localStorage for easy testing
    const cookie = useCookie(ACCESS_COOKIE)
    cookie.value = token
    // optional: set expiry etc server-side for real apps

    // also keep in localStorage so you can inspect it quickly in browser DevTools
    try { localStorage.setItem(ACCESS_COOKIE, token) } catch (e) { /* ignore */ }

    if (navigator.vibrate) navigator.vibrate(100)
    // navigate to start page (replace history)
    await router.replace('/start')
  } catch (err) {
    console.error('Login error', err)
    if (navigator.vibrate) navigator.vibrate([50, 20, 50])
    alert('Network or unknown error, see console')
  }
}

function goRegister() {
  if (navigator.vibrate) navigator.vibrate(80)
  router.replace('/register')
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.inner {
  width: 100%;
  max-width: 420px;
}
.logo {
  width: 100px;
  height: 100px;
  display: block;
  margin: 0 auto 20px;
  object-fit: contain;
}
.title {
  font-size: 32px;
  font-weight: bold;
  text-align: center;
  margin-bottom: 30px;
  color: #fff;
}
.title .red { color: #ff0000 }
.title .white { color: #ffffff }
.inputContainer { margin-bottom: 20px; }
.label {
  display: block;
  color: #fff;
  font-weight: bold;
  margin-bottom: 6px;
}
.input, .passwordInput {
  width: 100%;
  height: 50px;
  padding: 0 15px;
  border-radius: 5px;
  border: 1px solid #ccc;
  background: #fff;
  color: #000;
  box-sizing: border-box;
}
.passwordContainer {
  display: flex;
  align-items: center;
  border-radius: 5px;
  overflow: hidden;
}
.eyeButton {
  padding: 10px;
  background: transparent;
  border: none;
  cursor: pointer;
}
.eyeIcon { font-size: 18px; }
.loginButton {
  width: 100%;
  background: #ff0000;
  color: #fff;
  padding: 15px;
  border: none;
  border-radius: 5px;
  font-weight: bold;
  cursor: pointer;
  margin-top: 10px;
}
.registerRedirectButton {
  width: 100%;
  margin-top: 10px;
  background: #fff;
  color: #ff0000;
  border: 1px solid #ff0000;
  padding: 15px;
  border-radius: 5px;
  font-weight: bold;
  cursor: pointer;
}
</style>
