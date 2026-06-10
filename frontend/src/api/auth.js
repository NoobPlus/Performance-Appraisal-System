import request from './request'

export function getUserInfo() {
  return request.get('/auth/me')
}

export function login() {
  window.location.href = '/auth/login'
}

export function logout() {
  return request.post('/auth/logout')
}

export function devLogin(testUserId) {
  return request.post('/auth/dev-login', { test_user_id: testUserId })
}

export function getDevUsers() {
  return request.get('/auth/dev-users')
}
