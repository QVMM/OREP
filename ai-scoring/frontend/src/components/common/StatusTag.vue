<template>
  <n-tag :type="statusType" :size="size" :round="round">
    <template #icon>
      <n-icon v-if="showIcon" :component="statusIcon" />
    </template>
    {{ label }}
  </n-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NTag, NIcon } from 'naive-ui'
import {
  CheckCircleOutline,
  CloseCircleOutline,
  TimeOutline,
  SyncCircleOutline,
  AlertCircleOutline
} from '@vicons/ionicons5'

type StatusType = 'success' | 'error' | 'warning' | 'info' | 'default'

interface Props {
  status: string
  label: string
  size?: 'small' | 'medium' | 'large'
  round?: boolean
  showIcon?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'medium',
  round: true,
  showIcon: true
})

const statusType = computed<StatusType>(() => {
  const statusMap: Record<string, StatusType> = {
    success: 'success',
    completed: 'success',
    passed: 'success',
    error: 'error',
    failed: 'error',
    rejected: 'error',
    warning: 'warning',
    pending: 'warning',
    waiting: 'warning',
    processing: 'info',
    running: 'info',
    active: 'info'
  }
  return statusMap[props.status.toLowerCase()] || 'default'
})

const statusIcon = computed(() => {
  const iconMap: Record<string, typeof CheckCircleOutline> = {
    success: CheckCircleOutline,
    completed: CheckCircleOutline,
    passed: CheckCircleOutline,
    error: CloseCircleOutline,
    failed: CloseCircleOutline,
    rejected: CloseCircleOutline,
    warning: AlertCircleOutline,
    pending: TimeOutline,
    waiting: TimeOutline,
    processing: SyncCircleOutline,
    running: SyncCircleOutline,
    active: SyncCircleOutline
  }
  return iconMap[props.status.toLowerCase()] || CheckCircleOutline
})
</script>
