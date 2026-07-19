import { computed, ref } from 'vue'

const TOKEN_KEY = 'softcup_token'
const USER_KEY = 'softcup_user'

const token = ref(localStorage.getItem(TOKEN_KEY) || '')
const user = ref(safeParse(localStorage.getItem(USER_KEY)))

function safeParse(raw) {
  try {
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const isLoggedIn = computed(() => Boolean(token.value))
export const isAdmin = computed(() => user.value?.role === 'admin')
export const currentUser = computed(() => user.value)

export function getToken() {
  return token.value
}

export function setSession(accessToken, userInfo) {
  token.value = accessToken
  user.value = userInfo
  localStorage.setItem(TOKEN_KEY, accessToken)
  localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
}

export function clearSession() {
  token.value = ''
  user.value = null
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}
