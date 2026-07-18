<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { askImage, askText, createAnnotation, searchText } from '../api'

const deviceModel = ref('摩托车发动机')
const query = ref('火花塞怎么检查')
const loading = ref(false)
const searchLoading = ref(false)
const result = ref(null)
const searchResult = ref(null)
const imageFile = ref(null)
const imagePreview = ref('')
const rating = ref(0)
const correction = ref('')

const quickQueries = ['火花塞怎么检查', '机油渗漏怎么排查', '怠速不稳', '压缩压力测量', '气门间隙调整']

const riskType = computed(() => {
  const risk = result.value?.risk_level
  if (risk === 'high') return 'danger'
  if (risk === 'medium') return 'warning'
  if (risk === 'low') return 'success'
  return 'info'
})

const visibleHits = computed(() => result.value?.hits || searchResult.value?.hits || [])

function ensureQuery() {
  if (!query.value.trim()) {
    ElMessage.warning('请输入故障描述或检索关键词')
    return false
  }
  return true
}

async function doSearch() {
  if (!ensureQuery()) return
  searchLoading.value = true
  try {
    const { data } = await searchText({
      query: query.value,
      device_model: deviceModel.value,
      top_k: 8,
    })
    searchResult.value = data
    result.value = null
  } catch {
    ElMessage.error('检索失败，请确认后端已启动')
  } finally {
    searchLoading.value = false
  }
}

async function doAsk() {
  if (!ensureQuery()) return
  loading.value = true
  result.value = null
  try {
    if (imageFile.value) {
      const fd = new FormData()
      fd.append('query', query.value)
      fd.append('device_model', deviceModel.value)
      fd.append('top_k', '6')
      fd.append('image', imageFile.value)
      const { data } = await askImage(fd)
      result.value = data
    } else {
      const { data } = await askText({
        query: query.value,
        device_model: deviceModel.value,
        top_k: 6,
      })
      result.value = data
    }
    searchResult.value = null
  } catch (e) {
    const msg = e?.response?.data?.detail || '请求失败，请确认后端已启动'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function applyQuickQuery(text) {
  query.value = text
}

function onFileChange(uploadFile) {
  imageFile.value = uploadFile.raw
  imagePreview.value = URL.createObjectURL(uploadFile.raw)
}

function clearFile() {
  imageFile.value = null
  imagePreview.value = ''
}

async function submitFeedback() {
  if (!result.value) return
  await createAnnotation({
    query: query.value,
    original_answer: result.value.answer,
    corrected_answer: correction.value || null,
    rating: rating.value || null,
    source_refs: result.value.citations?.join(',') || result.value.hits.map((h) => h.source).join(','),
  })
  ElMessage.success('反馈已提交')
  correction.value = ''
  rating.value = 0
}
</script>

<template>
  <div class="work-grid search-grid">
    <section class="panel input-panel">
      <div class="section-title">
        <div>
          <h2>多模态检索</h2>
          <p>文本、图片和设备型号联合召回维修手册与案例。</p>
        </div>
        <el-tag type="info">FTS + RAG</el-tag>
      </div>

      <el-form label-position="top">
        <el-form-item label="设备型号">
          <el-input v-model="deviceModel" placeholder="摩托车发动机" />
        </el-form-item>
        <el-form-item label="故障描述">
          <el-input v-model="query" type="textarea" :rows="4" maxlength="300" show-word-limit />
        </el-form-item>
        <div class="quick-row">
          <el-button v-for="item in quickQueries" :key="item" size="small" @click="applyQuickQuery(item)">
            {{ item }}
          </el-button>
        </div>
        <el-form-item label="现场图片">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            accept="image/jpeg,image/png,image/webp"
            :on-change="onFileChange"
            :on-remove="clearFile"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div>选择故障图片</div>
          </el-upload>
          <img v-if="imagePreview" :src="imagePreview" class="preview" alt="故障图片预览" />
        </el-form-item>
        <div class="button-row">
          <el-button :loading="searchLoading" @click="doSearch">仅检索</el-button>
          <el-button type="primary" :loading="loading" @click="doAsk">智能诊断</el-button>
        </div>
      </el-form>
    </section>

    <section class="panel result-panel">
      <template v-if="result">
        <div class="result-head">
          <div>
            <h2>诊断建议</h2>
            <div class="tag-row">
              <el-tag :type="riskType">风险 {{ result.risk_level }}</el-tag>
              <el-tag type="success">置信度 {{ Math.round(result.confidence * 100) }}%</el-tag>
              <el-tag>{{ result.llm_mode }}</el-tag>
            </div>
          </div>
          <el-progress type="dashboard" :percentage="Math.round(result.confidence * 100)" :width="92" />
        </div>

        <el-alert
          v-if="result.fallback_reason"
          :title="'降级提示：' + result.fallback_reason"
          type="warning"
          show-icon
          :closable="false"
        />
        <el-alert
          v-if="result.image_description"
          :title="'图像分析：' + result.image_description"
          type="info"
          show-icon
          :closable="false"
        />

        <div class="answer">{{ result.answer }}</div>

        <div class="action-list">
          <span v-for="action in result.suggested_actions" :key="action">
            <el-icon><CircleCheck /></el-icon>{{ action }}
          </span>
        </div>

        <el-divider />
        <h3>人工标注</h3>
        <el-rate v-model="rating" show-text />
        <el-input
          v-model="correction"
          type="textarea"
          :rows="3"
          maxlength="4000"
          show-word-limit
          placeholder="可选：填写更准确的答案"
        />
        <el-button class="feedback-btn" @click="submitFeedback">提交反馈</el-button>
      </template>

      <template v-else-if="searchResult">
        <div class="section-title">
          <div>
            <h2>检索结果</h2>
            <p>命中 {{ searchResult.hits.length }} 条 / 索引 {{ searchResult.total_in_store }} 条</p>
          </div>
        </div>
        <div class="tag-row">
          <el-tag v-for="term in searchResult.query_terms" :key="term" size="small">{{ term }}</el-tag>
        </div>
      </template>

      <el-empty v-else description="输入故障现象后开始检索或诊断" />
    </section>
  </div>

  <section class="panel source-panel">
    <div class="section-title compact">
      <h2>引用证据</h2>
      <span>{{ visibleHits.length }} 条</span>
    </div>
    <el-empty v-if="!visibleHits.length" description="暂无引用" />
    <div v-else class="hit-list">
      <article v-for="hit in visibleHits" :key="hit.id" class="hit-item">
        <div class="hit-meta">
          <strong>{{ hit.source }}</strong>
          <span>页码 {{ hit.page ?? '案例' }}</span>
          <span>{{ hit.doc_type }}</span>
          <el-tag size="small" type="success">{{ hit.score }}</el-tag>
        </div>
        <p>{{ hit.content }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.search-grid {
  grid-template-columns: minmax(320px, 430px) minmax(0, 1fr);
}
.quick-row,
.button-row,
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.button-row {
  justify-content: flex-end;
}
.preview {
  width: 100%;
  max-height: 180px;
  object-fit: cover;
  border-radius: 8px;
  margin-top: 12px;
  border: 1px solid #dbe3ee;
}
.result-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.answer {
  white-space: pre-wrap;
  line-height: 1.75;
  padding: 16px;
  background: #f7fbf8;
  border: 1px solid #d8eadc;
  border-radius: 8px;
  margin: 14px 0;
}
.action-list {
  display: grid;
  gap: 8px;
}
.action-list span {
  display: flex;
  gap: 8px;
  align-items: center;
  color: #245b38;
}
.feedback-btn {
  margin-top: 10px;
}
.source-panel {
  margin-top: 18px;
}
.hit-list {
  display: grid;
  gap: 12px;
}
.hit-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  color: #5b677a;
}
@media (max-width: 980px) {
  .search-grid {
    grid-template-columns: 1fr;
  }
}
</style>
