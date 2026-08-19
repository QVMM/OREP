import { inject } from 'vue'

export const SDOC_HOST_KEY = 'sdocHost'

export function useSdocHost() {
  const host = inject(SDOC_HOST_KEY, null)
  if (!host) {
    throw new Error('sdocHost 未注入：请通过 SmartDocPage 或教师页打开编辑器')
  }
  return host
}
