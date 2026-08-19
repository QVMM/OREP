import { h } from 'vue'
import {
  create,
  NButton,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NSwitch,
  NProgress,
  NSpin,
  NModal,
  NMessageProvider,
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NDataTable,
  NTag,
  NAvatar,
  NNotificationProvider,
  NGrid,
  NGi,
  NDivider,
  NSteps,
  NStep,
  NList,
  NListItem,
  NThing,
  NCollapse,
  NCollapseItem,
  NResult,
  NAlert,
  NStatistic,
  NInputNumber,
  NDescriptions,
  NDescriptionsItem,
  NSpace,
  NButtonGroup,
  NIcon,
  NEmpty
} from 'naive-ui'

export default {
  install(app) {
    const naive = create({
      setup() {
        return () =>
          h(NMessageProvider, null, {
            default: () =>
              h(NNotificationProvider, null, {
                default: () => null
              })
          })
      }
    })

    app.use(naive)

    // 注册常用组件
    const components = [
      NButton,
      NCard,
      NForm,
      NFormItem,
      NInput,
      NSelect,
      NSwitch,
      NProgress,
      NSpin,
      NModal,
      NLayout,
      NLayoutSider,
      NLayoutContent,
      NDataTable,
      NTag,
      NAvatar,
      NGrid,
      NGi,
      NDivider,
      NSteps,
      NStep,
      NList,
      NListItem,
      NThing,
      NCollapse,
      NCollapseItem,
      NResult,
      NAlert,
      NStatistic,
      NInputNumber,
      NDescriptions,
      NDescriptionsItem,
      NSpace,
      NButtonGroup,
      NIcon,
      NEmpty
    ]

    components.forEach((component) => {
      if (component.name) {
        app.component(component.name, component)
      }
    })

    // 提供全局方法
    app.config.globalProperties.$message = NMessageProvider
    app.provide('message', NMessageProvider)
  }
}
