<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createCase, getGraph, listAnnotations, listCases, reviewCase } from '../api'

const tab = ref('cases')
const cases = ref([])
const annotations = ref([])
const graph = ref({ nodes: [], edges: [], summary: {} })
const loading = ref(false)
const statusFilter = ref('')

const form = ref({
  title: '',
  device_model: '摩托车发动机',
  symptom: '',
  solution: '',
})
const imageFile = ref(null)
const imagePreview = ref('')

const typeLabel = { device: '设备', fault: '故障', part: '部件', procedure: '方案' }
const relLabel = {
  has_fault: '存在故障',
  resolved_by: '处理方案',
  contains: '包含',
  related_to: '关联故障',
}

const caseSummary = computed(() => {
  const result = { pending: 0, approved: 0, rejected: 0 }
  for (const item of cases.value) result[item.status] = (result[item.status] || 0) + 1
  return result
})

async function refreshCases() {
  const { data } = await listCases(statusFilter.value || undefined)
  cases.value = data
}

async function refreshGraph() {
  const { data } = await getGraph()
  graph.value = data
}

async function refreshAnnotations() {
  const { data } = await listAnnotations()
  annotations.value = data
}

async function refreshAll() {
  loading.value = true
  try {
    await Promise.all([refreshCases(), refreshGraph(), refreshAnnotations()])
  } finally {
    loading.value = false
  }
}

onMounted(refreshAll)

function onFileChange(f) {
  imageFile.value = f.raw
  imagePreview.value = URL.createObjectURL(f.raw)
}

function clearImage() {
  imageFile.value = null
  imagePreview.value = ''
}

async function submitCase() {
  if (!form.value.title || !form.value.symptom || !form.value.solution) {
    ElMessage.warning('请填写标题、故障现象和处理方案')
    return
  }
  const fd = new FormData()
  Object.entries(form.value).forEach(([k, v]) => fd.append(k, v))
  if (imageFile.value) fd.append('image', imageFile.value)
  await createCase(fd)
  ElMessage.success('案例已提交，等待审核')
  form.value = { title: '', device_model: '摩托车发动机', symptom: '', solution: '' }
  clearImage()
  statusFilter.value = ''
  await refreshCases()
  tab.value = 'cases'
}

async function doReview(id, approve) {
  await reviewCase(id, { approve })
  ElMessage.success(approve ? '已通过并入库' : '已驳回')
  await Promise.all([refreshCases(), refreshGraph()])
}
</script>

<template>
  <div class="work-grid knowledge-grid">
    <section class="panel">
      <div class="section-title">
        <div>
          <h2>知识沉淀</h2>
          <p>案例审核通过后进入检索库并更新图谱。</p>
        </div>
        <el-button size="small" :loading="loading" @click="refreshAll">刷新</el-button>
      </div>
      <div class="status-grid">
        <div>
          <strong>{{ caseSummary.pending }}</strong>
          <span>待审</span>
        </div>
        <div>
          <strong>{{ caseSummary.approved }}</strong>
          <span>已入库</span>
        </div>
        <div>
          <strong>{{ annotations.length }}</strong>
          <span>标注</span>
        </div>
      </div>
      <el-tabs v-model="tab">
        <el-tab-pane label="案例审核" name="cases" />
        <el-tab-pane label="案例上传" name="upload" />
        <el-tab-pane label="知识图谱" name="graph" />
        <el-tab-pane label="人工标注" name="annotations" />
      </el-tabs>
    </section>

    <section class="panel" v-if="tab === 'upload'">
      <div class="section-title compact">
        <h2>新增案例</h2>
      </div>
      <el-form label-position="top">
        <el-form-item label="标题"><el-input v-model="form.title" maxlength="120" show-word-limit /></el-form-item>
        <el-form-item label="设备型号"><el-input v-model="form.device_model" maxlength="128" /></el-form-item>
        <el-form-item label="故障现象">
          <el-input v-model="form.symptom" type="textarea" :rows="3" maxlength="1000" show-word-limit />
        </el-form-item>
        <el-form-item label="处理方案">
          <el-input v-model="form.solution" type="textarea" :rows="4" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="现场图片">
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept="image/jpeg,image/png,image/webp"
            :on-change="onFileChange"
            :on-remove="clearImage"
          >
            <el-button>选择图片</el-button>
          </el-upload>
          <img v-if="imagePreview" :src="imagePreview" class="case-preview" alt="案例图片预览" />
        </el-form-item>
        <el-button type="primary" @click="submitCase">提交审核</el-button>
      </el-form>
    </section>
  </div>

  <section v-if="tab === 'cases'" class="panel content-panel">
    <div class="section-title compact">
      <h2>案例审核</h2>
      <el-select v-model="statusFilter" clearable placeholder="全部状态" style="width: 140px" @change="refreshCases">
        <el-option label="待审" value="pending" />
        <el-option label="已入库" value="approved" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
    </div>

    <el-empty v-if="!cases.length" description="暂无案例" />
    <div v-else class="case-list" v-loading="loading">
      <article v-for="item in cases" :key="item.id" class="case-card" :class="{ 'has-image': item.image_url }">
        <img v-if="item.image_url" :src="item.image_url" alt="现场图" />
        <div class="case-body">
          <div class="case-head">
            <div>
              <h3>{{ item.title }}</h3>
              <span>{{ item.device_model }}</span>
            </div>
            <el-tag :type="item.status === 'approved' ? 'success' : item.status === 'rejected' ? 'info' : 'warning'">
              {{ item.status }}
            </el-tag>
          </div>
          <p><strong>故障：</strong>{{ item.symptom }}</p>
          <p><strong>方案：</strong>{{ item.solution }}</p>
          <div class="case-actions" v-if="item.status === 'pending'">
            <el-button size="small" type="success" @click="doReview(item.id, true)">通过入库</el-button>
            <el-button size="small" @click="doReview(item.id, false)">驳回</el-button>
          </div>
        </div>
      </article>
    </div>
  </section>

  <section v-if="tab === 'graph'" class="panel content-panel">
    <div class="section-title compact">
      <h2>知识图谱</h2>
      <span>{{ graph.nodes.length }} 个实体 / {{ graph.edges.length }} 条关系</span>
    </div>
    <el-empty v-if="!graph.nodes.length" description="审核通过案例后将自动生成图谱" />
    <template v-else>
      <div class="graph-summary">
        <el-tag v-for="(count, key) in graph.summary" :key="key" size="large">
          {{ typeLabel[key] || key }} {{ count }}
        </el-tag>
      </div>
      <div class="graph-grid">
        <div>
          <h3>实体</h3>
          <div class="node-list">
            <el-tag
              v-for="n in graph.nodes"
              :key="n.id"
              :type="n.entity_type === 'fault' ? 'danger' : n.entity_type === 'part' ? 'warning' : 'success'"
            >
              #{{ n.id }} [{{ typeLabel[n.entity_type] || n.entity_type }}] {{ n.name }}
            </el-tag>
          </div>
        </div>
        <div>
          <h3>关系</h3>
          <ul class="edge-list">
            <li v-for="e in graph.edges" :key="e.id">
              #{{ e.source }} — {{ relLabel[e.relation_type] || e.relation_type }} → #{{ e.target }}
            </li>
          </ul>
        </div>
      </div>
    </template>
  </section>

  <section v-if="tab === 'annotations'" class="panel content-panel">
    <div class="section-title compact">
      <h2>人工标注</h2>
      <span>{{ annotations.length }} 条</span>
    </div>
    <el-empty v-if="!annotations.length" description="暂无标注" />
    <div v-else class="annotation-list">
      <article v-for="item in annotations" :key="item.id" class="annotation-card">
        <strong>{{ item.query }}</strong>
        <el-rate :model-value="item.rating || 0" disabled />
        <p v-if="item.corrected_answer">{{ item.corrected_answer }}</p>
        <span>{{ item.source_refs || '无引用记录' }}</span>
      </article>
    </div>
  </section>
</template>

<style scoped>
.knowledge-grid {
  grid-template-columns: minmax(320px, 430px) minmax(0, 1fr);
}
.status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.status-grid div {
  border: 1px solid #e0e7ef;
  border-radius: 8px;
  padding: 12px;
}
.status-grid strong {
  display: block;
  font-size: 24px;
  color: #17324d;
}
.status-grid span {
  color: #607087;
}
.content-panel {
  margin-top: 18px;
}
.case-preview {
  width: 100%;
  max-height: 180px;
  object-fit: cover;
  border-radius: 8px;
  margin-top: 12px;
}
.case-list,
.annotation-list {
  display: grid;
  gap: 12px;
}
.case-card {
  display: grid;
  grid-template-columns: 1fr;
  border: 1px solid #dfe7f1;
  border-radius: 8px;
  overflow: hidden;
}
.case-card.has-image {
  grid-template-columns: 160px minmax(0, 1fr);
}
.case-card > img {
  width: 100%;
  height: 100%;
  min-height: 150px;
  object-fit: cover;
  background: #eef3f8;
}
.case-body {
  padding: 14px;
}
.case-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.case-head h3 {
  margin: 0;
}
.case-head span,
.annotation-card span {
  color: #607087;
}
.case-actions {
  display: flex;
  gap: 8px;
}
.graph-summary,
.node-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.graph-summary {
  margin-bottom: 16px;
}
.graph-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.edge-list {
  line-height: 1.9;
  color: #42526a;
}
.annotation-card {
  border: 1px solid #dfe7f1;
  border-radius: 8px;
  padding: 14px;
}
.annotation-card p {
  white-space: pre-wrap;
}
@media (max-width: 980px) {
  .knowledge-grid,
  .graph-grid,
  .case-card {
    grid-template-columns: 1fr;
  }
}
</style>
