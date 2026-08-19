import { createRouter, createWebHistory } from 'vue-router'
import PptGenerator from '../views/PptGenerator.vue'
import Phase1Round1 from '../views/Phase1Round1.vue'
import Phase1Round2Confirm from '../views/Phase1Round2Confirm.vue'
import Phase1Round3Preview from '../views/Phase1Round3Preview.vue'
import Phase2Progress from '../views/Phase2Progress.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/generate',
    name: 'PptGenerator',
    component: PptGenerator
  },
  {
    path: '/ppt-editor',
    name: 'PptEditor',
    component: () => import('../views/PptEditor.vue')
  },
  {
    path: '/phase1/round1',
    name: 'Phase1Round1',
    component: Phase1Round1
  },
  {
    path: '/phase1/round2',
    name: 'Phase1Round2',
    component: Phase1Round2Confirm
  },
  {
    path: '/phase1/round3',
    name: 'Phase1Round3',
    component: Phase1Round3Preview
  },
  {
    path: '/phase2',
    name: 'Phase2',
    component: Phase2Progress
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
