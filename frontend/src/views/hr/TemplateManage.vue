<template>
  <div class="page-container">
    <van-nav-bar title="系统模板（只读）" left-arrow @click-left="$router.back()" fixed placeholder>

    </van-nav-bar>

    <div class="page-content">
      <div v-if="templates.length === 0" class="empty-wrapper">
        <van-empty description="暂无评估模板">

        </van-empty>
      </div>

      <div v-for="tpl in templates" :key="tpl.id" class="card tpl-card">
        <div class="tpl-header">
          <div>
            <span class="tpl-name">{{ tpl.name }}</span>
            <van-tag v-if="tpl.is_default" type="primary" size="medium" plain style="margin-left:6px;">默认</van-tag>
          </div>
          <van-tag :type="tpl.type === 'kpi' ? 'success' : tpl.type === 'okr' ? 'warning' : 'primary'" plain>
            {{ typeLabel(tpl.type) }}
          </van-tag>
        </div>
        <div class="tpl-dims">
          <div v-for="(dim, idx) in tpl.dimensions" :key="idx" class="tpl-dim">
            <span>{{ dim.name }}</span>
            <span class="tpl-dim-weight">{{ dim.weight }}%</span>
          </div>
        </div>

      </div>
    </div>


  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTemplates } from '../../api/templates'

const templates = ref([])

const typeLabel = (t) => ({ kpi: 'KPI', okr: 'OKR', '360': '360度', custom: '自定义' }[t] || t)

async function loadTemplates() {
  try {
    const res = await getTemplates()
    templates.value = res || []
  } catch (e) { templates.value = [] }
}

onMounted(loadTemplates)
</script>

<style scoped>
.tpl-card:active { background: #f9f9f9; }
.tpl-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.tpl-name { font-size: 15px; font-weight: 600; color: #333; }
.tpl-dims { margin-bottom: 10px; }
.tpl-dim { display: flex; justify-content: space-between; font-size: 13px; color: #666; padding: 4px 0; border-bottom: 1px solid #f5f5f5; }
.tpl-dim-weight { color: var(--primary-color); font-weight: 500; }
.popup-content { padding: 16px; }
.popup-title { font-size: 16px; font-weight: 600; text-align: center; margin-bottom: 12px; }
</style>
