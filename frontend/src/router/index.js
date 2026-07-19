import { createRouter, createWebHistory } from 'vue-router'
import { getToken, isAdmin } from '../auth'

const SearchView = () => import('../views/SearchView.vue')
const WorkflowView = () => import('../views/WorkflowView.vue')
const KnowledgeView = () => import('../views/KnowledgeView.vue')
const LoginView = () => import('../views/LoginView.vue')

const routes = [
  { path: '/login', component: LoginView, meta: { title: '登录', public: true } },
  { path: '/', redirect: '/search' },
  {
    path: '/search',
    component: SearchView,
    meta: { title: '智能检索', subtitle: '多模态知识检索与智能诊断' },
  },
  {
    path: '/workflow',
    component: WorkflowView,
    meta: { title: '作业指引', subtitle: '标准化检修流程与合规提醒' },
  },
  {
    path: '/knowledge',
    component: KnowledgeView,
    meta: { title: '知识管理', subtitle: '案例沉淀、审核入库与知识图谱' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  if (to.meta.public) {
    if (getToken() && to.path === '/login') return '/search'
    return true
  }
  if (!getToken()) return '/login'
  if (to.meta.adminOnly && !isAdmin.value) return '/search'
  return true
})

export default router
