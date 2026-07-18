import { createRouter, createWebHistory } from 'vue-router'

const SearchView = () => import('../views/SearchView.vue')
const WorkflowView = () => import('../views/WorkflowView.vue')
const KnowledgeView = () => import('../views/KnowledgeView.vue')

const routes = [
  { path: '/', redirect: '/search' },
  { path: '/search', component: SearchView, meta: { title: '智能检索' } },
  { path: '/workflow', component: WorkflowView, meta: { title: '作业指引' } },
  { path: '/knowledge', component: KnowledgeView, meta: { title: '知识管理' } },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
