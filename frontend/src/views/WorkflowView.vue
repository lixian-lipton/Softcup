<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getWorkflow } from '../api'

const deviceModel = ref('摩托车发动机')
const level = ref('level1')
const fault = ref('火花塞')
const loading = ref(false)
const workflow = ref(null)
const checkedSteps = ref([])

const levels = [
  { value: 'daily', label: '日常点检' },
  { value: 'level1', label: '一级检修' },
  { value: 'level2', label: '二级检修' },
  { value: 'emergency', label: '紧急故障' },
]

const requiredOrders = computed(() =>
  workflow.value ? workflow.value.steps.filter((s) => s.required).map((s) => s.order) : [],
)
const requiredDone = computed(() => requiredOrders.value.every((o) => checkedSteps.value.includes(o)))
const progress = computed(() => {
  if (!workflow.value?.steps.length) return 0
  return Math.round((checkedSteps.value.length / workflow.value.steps.length) * 100)
})
const riskType = computed(() => {
  if (workflow.value?.risk_level === 'high') return 'danger'
  if (workflow.value?.risk_level === 'medium') return 'warning'
  return 'success'
})

async function loadWorkflow() {
  loading.value = true
  checkedSteps.value = []
  try {
    const { data } = await getWorkflow({
      device_model: deviceModel.value,
      maintenance_level: level.value,
      fault_description: fault.value || null,
    })
    workflow.value = data
  } catch {
    ElMessage.error('获取作业指引失败')
  } finally {
    loading.value = false
  }
}

function toggleStep(order, val) {
  if (val && !checkedSteps.value.includes(order)) {
    checkedSteps.value = [...checkedSteps.value, order]
  } else if (!val) {
    checkedSteps.value = checkedSteps.value.filter((o) => o !== order)
  }
}

onMounted(loadWorkflow)
</script>

<template>
  <div class="work-grid workflow-grid">
    <section class="panel">
      <div class="section-title">
        <div>
          <h2>作业参数</h2>
          <p>按设备、等级和故障线索生成执行单。</p>
        </div>
      </div>
      <el-form label-position="top">
        <el-form-item label="设备型号">
          <el-input v-model="deviceModel" />
        </el-form-item>
        <el-form-item label="检修等级">
          <el-segmented v-model="level" :options="levels" block />
        </el-form-item>
        <el-form-item label="故障描述">
          <el-input v-model="fault" maxlength="300" show-word-limit />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="loadWorkflow">生成指引</el-button>
      </el-form>
    </section>

    <section class="panel status-panel" v-if="workflow">
      <div class="section-title">
        <div>
          <h2>{{ workflow.workflow_name }}</h2>
          <p>{{ workflow.device_model }} / {{ workflow.maintenance_level }}</p>
        </div>
        <el-tag :type="riskType">风险 {{ workflow.risk_level }}</el-tag>
      </div>
      <div class="status-grid">
        <div>
          <strong>{{ workflow.estimated_minutes }}</strong>
          <span>预计分钟</span>
        </div>
        <div>
          <strong>{{ workflow.steps.length }}</strong>
          <span>步骤</span>
        </div>
        <div>
          <strong>{{ workflow.evidence_hits.length }}</strong>
          <span>证据</span>
        </div>
      </div>
      <el-progress :percentage="progress" :status="requiredDone ? 'success' : undefined" />
      <p class="summary">{{ workflow.llm_summary }}</p>
      <div class="safety">
        <el-tag v-for="n in workflow.safety_notes" :key="n" type="danger">{{ n }}</el-tag>
      </div>
    </section>
  </div>

  <section v-if="workflow" class="panel step-panel">
    <div class="section-title compact">
      <h2>执行步骤</h2>
      <span>{{ workflow.progress_rule }}</span>
    </div>
    <div class="step-list">
      <article
        v-for="step in workflow.steps"
        :key="step.order"
        class="step-card"
        :class="{ done: checkedSteps.includes(step.order) }"
      >
        <div class="step-index">{{ step.order }}</div>
        <div class="step-content">
          <div class="step-title">
            <h3>{{ step.title }}</h3>
            <el-tag v-if="step.required" size="small" type="warning">必填</el-tag>
          </div>
          <p>{{ step.description }}</p>
          <div class="meta-row" v-if="step.tools.length">
            <strong>工具</strong>
            <span>{{ step.tools.join('、') }}</span>
          </div>
          <div class="meta-row" v-if="step.compliance.length">
            <strong>合规</strong>
            <span>{{ step.compliance.join('；') }}</span>
          </div>
          <div class="meta-row" v-if="step.checkpoint">
            <strong>检查点</strong>
            <span>{{ step.checkpoint }}</span>
          </div>
          <el-checkbox
            :model-value="checkedSteps.includes(step.order)"
            @change="(v) => toggleStep(step.order, v)"
          >
            已完成
          </el-checkbox>
        </div>
      </article>
    </div>

    <el-alert
      v-if="!requiredDone"
      title="尚有必填步骤未确认"
      type="warning"
      show-icon
      :closable="false"
      class="final-alert"
    />
    <el-result v-else icon="success" title="关键步骤已全部确认" sub-title="可归档本次检修记录" />
  </section>

  <section v-if="workflow?.evidence_hits.length" class="panel evidence-panel">
    <div class="section-title compact">
      <h2>关联证据</h2>
      <span>{{ workflow.evidence_hits.length }} 条</span>
    </div>
    <article v-for="hit in workflow.evidence_hits" :key="hit.id" class="hit-item">
      <div class="hit-meta">
        <strong>{{ hit.source }}</strong>
        <span>页码 {{ hit.page ?? '案例' }}</span>
        <el-tag size="small">{{ hit.score }}</el-tag>
      </div>
      <p>{{ hit.content }}</p>
    </article>
  </section>
</template>

<style scoped>
.workflow-grid {
  grid-template-columns: minmax(320px, 430px) minmax(0, 1fr);
}
.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 10px 0 16px;
}
.status-grid div {
  border: 1px solid #e0e7ef;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
}
.status-grid strong {
  display: block;
  font-size: 24px;
  color: #17324d;
}
.status-grid span {
  color: #607087;
}
.summary {
  line-height: 1.65;
  background: #f7f9fc;
  padding: 12px;
  border-radius: 8px;
}
.safety {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.step-panel,
.evidence-panel {
  margin-top: 18px;
}
.step-list {
  display: grid;
  gap: 12px;
}
.step-card {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 14px;
  border: 1px solid #dfe7f1;
  border-radius: 8px;
  padding: 14px;
  background: #fff;
}
.step-card.done {
  border-color: #93c5a3;
  background: #f7fbf8;
}
.step-index {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #17324d;
  color: #fff;
  font-weight: 700;
}
.step-title,
.meta-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.step-title h3 {
  margin: 0;
}
.step-content p {
  color: #42526a;
  line-height: 1.6;
}
.meta-row {
  color: #55657b;
  margin: 6px 0;
}
.meta-row strong {
  color: #17324d;
}
.final-alert {
  margin-top: 16px;
}
@media (max-width: 980px) {
  .workflow-grid {
    grid-template-columns: 1fr;
  }
}
</style>
