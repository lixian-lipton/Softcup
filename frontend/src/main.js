import { createApp } from 'vue'
import {
  ElAlert,
  ElAside,
  ElButton,
  ElCheckbox,
  ElContainer,
  ElDialog,
  ElDivider,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElHeader,
  ElIcon,
  ElInput,
  ElLoading,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElProgress,
  ElRate,
  ElResult,
  ElSegmented,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTag,
  ElUpload,
} from 'element-plus'
import 'element-plus/dist/index.css'
import {
  CircleCheck,
  Collection,
  List,
  Refresh,
  Search,
  Setting,
  UploadFilled,
} from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import './assets/style.css'

const app = createApp(App)
;[
  ElAlert,
  ElAside,
  ElButton,
  ElCheckbox,
  ElContainer,
  ElDialog,
  ElDivider,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElHeader,
  ElIcon,
  ElInput,
  ElMain,
  ElMenu,
  ElMenuItem,
  ElOption,
  ElProgress,
  ElRate,
  ElResult,
  ElSegmented,
  ElSelect,
  ElTabPane,
  ElTabs,
  ElTag,
  ElUpload,
].forEach((component) => app.use(component))

app.use(ElLoading)
;[
  CircleCheck,
  Collection,
  List,
  Refresh,
  Search,
  Setting,
  UploadFilled,
].forEach((component) => app.component(component.name, component))
app.use(router)
app.mount('#app')
