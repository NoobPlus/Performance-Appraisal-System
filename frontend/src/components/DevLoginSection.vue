<template>
  <div class="dev-login-section">
    <van-divider>开发测试登录</van-divider>
    <div class="dev-login-content">
      <van-field
        v-model="selectedLabel"
        label="测试账号"
        readonly
        clickable
        @click="showPicker = true"
        placeholder="请选择测试账号"
      />
      <van-popup v-model:show="showPicker" position="bottom">
        <van-picker
          :columns="userOptions"
          @confirm="onConfirm"
          @cancel="showPicker = false"
        />
      </van-popup>
      <div class="user-info-preview" v-if="selectedUser && currentUser">
        <span class="user-role-tag" :class="currentUser.role">
          {{ getRoleLabel(currentUser.role) }}
        </span>
        <span class="user-name">{{ currentUser.name }}</span>
      </div>
      <van-button 
        type="warning" 
        block 
        round 
        size="large" 
        @click="handleDevLogin" 
        :loading="loading"
        :disabled="!selectedUser"
      >
        快速登录测试账号
      </van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { devLogin, getDevUsers } from '../api/auth'
import { setToken } from '../utils/auth'

// Props
defineProps({
  loading: Boolean,
})

// Emits
const emit = defineEmits(['login-success'])

// 状态
const selectedUser = ref('')
const selectedLabel = ref('')
const showPicker = ref(false)
const userOptions = ref([])
const devUsers = ref([])

// 当前选中用户信息
const currentUser = computed(() => {
  if (!selectedUser.value) return null
  return devUsers.value.find(u => u.key === selectedUser.value)
})

// 角色标签映射
const getRoleLabel = (role) => {
  const labels = {
    admin: '管理员',
    hr: 'HR',
    manager: '经理',
    employee: '员工',
  }
  return labels[role] || role
}

// 获取可用的测试账号列表（静态数据，确保即使后端关闭也能选）
const fetchDevUsers = async () => {
  try {
    // 静态定义用户选项，确保前端独立可用
    devUsers.value = [
      { key: 'test_admin', name: '开发-管理员', role: 'admin' },
      { key: 'test_hr', name: '开发-HR', role: 'hr' },
      { key: 'test_manager', name: '开发-经理', role: 'manager' },
      { key: 'test_employee', name: '开发-员工', role: 'employee' },
    ]
    
    userOptions.value = [
      { text: '开发-管理员 (管理员)', value: 'test_admin' },
      { text: '开发-HR (HR)', value: 'test_hr' },
      { text: '开发-经理 (经理)', value: 'test_manager' },
      { text: '开发-员工 (员工)', value: 'test_employee' },
    ]
    
    // 默认选中第一个
    if (userOptions.value.length > 0) {
      selectedUser.value = userOptions.value[0].value
      selectedLabel.value = userOptions.value[0].text
    }
  } catch (err) {
    console.error('获取测试账号列表失败:', err)
  }
}

// 选择器确认
const onConfirm = ({ selectedValues }) => {
  const user = devUsers.value.find(u => u.key === selectedValues[0])
  if (user) {
    selectedUser.value = user.key
    selectedLabel.value = userOptions.value.find(o => o.value === user.key)?.text || user.name
  }
  showPicker.value = false
}

// 开发环境快速登录
const handleDevLogin = async () => {
  if (!selectedUser.value) return
  
  try {
    const res = await devLogin(selectedUser.value)
    if (res?.token) {
      setToken(res.token)
      emit('login-success')
    }
  } catch (err) {
    console.error('开发登录失败:', err)
  }
}

// 初始化
onMounted(() => {
  fetchDevUsers()
})
</script>

<style scoped>
.dev-login-section {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px dashed #e0e0e0;
}

.dev-login-content {
  padding: 0 16px;
}

.user-info-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 12px 0 16px;
}

.user-role-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #fff;
}

.user-role-tag.admin {
  background-color: #e74c3c;
}

.user-role-tag.hr {
  background-color: #f39c12;
}

.user-role-tag.manager {
  background-color: #3498db;
}

.user-role-tag.employee {
  background-color: #2ecc71;
}

.user-name {
  font-size: 14px;
  color: #666;
}
</style>