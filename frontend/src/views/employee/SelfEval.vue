<template>
  <div class="page-container">
    <van-nav-bar title="自评填写" left-arrow @click-left="$router.back()" fixed placeholder />

    <div class="page-content" v-if="record && plan">
      <!-- 考核信息 -->
      <div class="card">
        <div class="plan-name">{{ plan.name }}</div>
        <div class="plan-meta">{{ plan.cycle_type }} · 截止：{{ plan.self_eval_end || '未设置' }}</div>
      </div>

      <!-- 维度配置（仅在待自评/已退回时显示） -->
      <div class="card" v-if="record.status === 'pending' || record.status === 'returned'">
        <div class="section-title">配置评分维度</div>
        <van-radio-group v-model="dimSource" direction="horizontal" style="padding:8px 0;">
          <van-radio name="custom">自主创建</van-radio>
          <van-radio name="template">选用我的模板</van-radio>
        </van-radio-group>

        <!-- 选用个人模板 -->
        <div v-if="dimSource === 'template'">
          <van-field label="选择模板" required>
            <template #input>
              <select v-model="selectedTemplateId" style="border:1px solid #eee;padding:4px 8px;border-radius:4px;width:100%;" @change="onTemplateSelect">
                <option value="" disabled>请选择模板</option>
                <option v-for="t in myTemplates" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </template>
          </van-field>
          <div v-if="selectedTemplate" class="template-preview">
            <div v-for="(dim, idx) in selectedTemplate.dimensions" :key="idx" class="tpl-dim-item">
              <span>{{ dim.name }}</span>
              <span class="dim-weight">{{ dim.weight }}%</span>
            </div>
          </div>
        </div>

        <!-- 自主创建维度 -->
        <div v-if="dimSource === 'custom'">
          <div v-for="(dim, idx) in customDimensions" :key="idx" class="dim-row">
            <van-field v-model="dim.name" placeholder="维度名称" size="small" style="flex:2;" />
            <van-field v-model="dim.weight" type="number" placeholder="权重" size="small" style="flex:1;" />
            <van-field v-model="dim.type" placeholder="类型" size="small" style="flex:1;" />
            <van-icon name="delete-o" color="#ee0a24" size="20" style="padding:8px;" @click="customDimensions.splice(idx,1)" />
          </div>
          <div style="padding:0 16px 8px;">
            <van-button size="mini" plain type="primary" icon="plus" @click="customDimensions.push({name:'',weight:'',type:'kpi'})">添加维度</van-button>
          </div>
        </div>
      </div>

      <!-- 评分维度 -->
      <div class="card">
        <div class="section-title">评分维度</div>
        <div v-for="(dim, idx) in dimensions" :key="idx" class="dim-form-item">
          <div class="dim-form-header">
            <span class="dim-form-name">{{ dim.name }}</span>
            <span class="dim-weight">权重 {{ dim.weight }}%</span>
          </div>
          <van-field
            v-model="dim.score"
            type="number"
            label="评分"
            placeholder="0 - 100"
            :rules="[{ required: true, message: '请输入评分' }]"
          />
          <van-field
            v-model="dim.comment"
            type="textarea"
            label="评语"
            placeholder="请填写该维度的自我评价..."
            rows="2"
            autosize
          />
        </div>
      </div>

      <!-- 整体自评 -->
      <div class="card">
        <div class="section-title">整体自评</div>
        <van-field
          v-model="overallComment"
          type="textarea"
          placeholder="请填写本期工作总结和自我评价..."
          rows="4"
          autosize
          maxlength="1000"
          show-word-limit
        />
      </div>
    </div>

    <!-- 提交按钮 -->
    <div class="floating-bottom" v-if="record">
      <van-button
        type="primary"
        block
        round
        :loading="submitting"
        :disabled="!canSubmit"
        @click="handleSubmit"
      >
        提交自评
      </van-button>
    </div>

    <van-loading v-if="loading" class="page-loading" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getEvalRecord, submitSelfEval } from '../../api/evaluation'
import { getMyTemplates } from '../../api/templates'
import { showToast, showConfirmDialog } from 'vant'

const route = useRoute()
const router = useRouter()
const recordId = parseInt(route.params.id)

const loading = ref(false)
const submitting = ref(false)
const record = ref(null)
const plan = ref(null)
const dimensions = ref([])
const overallComment = ref('')

// 维度配置
const dimSource = ref('custom')
const myTemplates = ref([])
const selectedTemplateId = ref('')
const selectedTemplate = ref(null)
const customDimensions = ref([
  { name: '目标达成', weight: '40', type: 'kpi' },
  { name: '能力发展', weight: '30', type: '360' },
  { name: '价值观', weight: '30', type: 'okr' }
])

const canSubmit = computed(() => {
  return dimensions.value.every(d => d.score && d.score >= 0 && d.score <= 100)
})

// 将自定义维度同步到评分维度列表（保留已有评分数据）
function syncCustomToDimensions() {
  const validDims = customDimensions.value.filter(d => d.name && d.weight)
  dimensions.value = validDims.map(d => {
    const existing = dimensions.value.find(e => e.name === d.name)
    return {
      name: d.name,
      weight: parseFloat(d.weight),
      type: d.type || 'custom',
      score: existing ? existing.score : '',
      comment: existing ? existing.comment : ''
    }
  })
}

// 监听自定义维度变化，实时同步到评分维度列表
watch(customDimensions, () => {
  if (dimSource.value === 'custom') {
    syncCustomToDimensions()
  }
}, { deep: true })

// 监听维度来源切换
watch(dimSource, (source) => {
  if (source === 'custom') {
    syncCustomToDimensions()
  } else if (source === 'template') {
    if (selectedTemplate.value) {
      dimensions.value = selectedTemplate.value.dimensions.map(d => ({
        name: d.name,
        weight: d.weight,
        type: d.type || 'custom',
        score: '',
        comment: ''
      }))
    } else {
      dimensions.value = []
    }
  }
})

function onTemplateSelect() {
  selectedTemplate.value = myTemplates.value.find(t => t.id === selectedTemplateId.value) || null
  if (selectedTemplate.value) {
    dimensions.value = selectedTemplate.value.dimensions.map(d => ({
      name: d.name,
      weight: d.weight,
      type: d.type || 'custom',
      score: '',
      comment: ''
    }))
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await getEvalRecord(recordId)
    record.value = res
    plan.value = res.plan || {}

    // 加载个人模板
    try {
      myTemplates.value = await getMyTemplates() || []
    } catch (e) { /* ignore */ }

    // 从已有评估记录获取维度（退回重评场景）
    const existingDims = res.evaluations || []
    if (existingDims.length > 0) {
      dimensions.value = existingDims.map(d => ({
        name: d.dimension,
        weight: d.weight,
        type: d.dimension_type || 'custom',
        score: d.score || '',
        comment: d.comment || ''
      }))
    } else if (dimSource.value === 'custom') {
      // 首次进入且为自主创建模式，从 customDimensions 同步
      syncCustomToDimensions()
    }
  } catch (e) {
    showToast('加载失败')
  }
  loading.value = false
})

async function handleSubmit() {
  // 如果是待自评/已退回状态，需要先配置维度
  if (record.value.status === 'pending' || record.value.status === 'returned') {
    if (dimSource.value === 'custom') {
      const validDims = customDimensions.value.filter(d => d.name && d.weight)
      if (validDims.length === 0) {
        showToast('请至少添加一个评分维度')
        return
      }
    } else if (dimSource.value === 'template') {
      if (!selectedTemplate.value) {
        showToast('请选择一个模板')
        return
      }
    }
  }

  if (dimensions.value.length === 0) {
    showToast('请先配置评分维度')
    return
  }

  try {
    await showConfirmDialog({
      title: '确认提交',
      message: '提交后不可修改（除非被退回），确认提交自评？'
    })
  } catch {
    return
  }

  submitting.value = true
  try {
    const scores = dimensions.value.map(d => ({
      dimension_name: d.name,
      weight: d.weight,
      type: d.type,
      score: parseFloat(d.score),
      comment: d.comment
    }))
    const payload = {
      record_id: recordId,
      scores,
      source: dimSource.value,
    }
    if (dimSource.value === 'template' && selectedTemplateId.value) {
      payload.template_id = selectedTemplateId.value
    }
    if (dimSource.value === 'custom') {
      payload.dimensions = customDimensions.value.filter(d => d.name && d.weight).map(d => ({
        name: d.name, weight: parseFloat(d.weight), type: d.type || 'custom'
      }))
    }
    const response = await submitSelfEval(payload)
    showToast({ message: response.message || '自评已提交', type: 'success' })
    setTimeout(() => router.replace('/employee/assessments'), 1500)
  } catch (e) {
    showToast(e.response?.data?.detail || '提交失败')
  }
  submitting.value = false
}
</script>

<style scoped>
.plan-name { font-size: 16px; font-weight: 600; color: #333; margin-bottom: 4px; }
.plan-meta { font-size: 13px; color: #999; }
.page-loading { display: flex; justify-content: center; padding: 40px; }
.dim-row { display: flex; gap: 6px; align-items: center; padding: 0 16px; }
.template-preview { padding: 8px 16px; background: #f9f9f9; border-radius: 8px; margin: 0 16px 12px; }
.tpl-dim-item { display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; color: #666; }
.dim-weight { color: var(--primary-color); font-weight: 500; }
</style>
