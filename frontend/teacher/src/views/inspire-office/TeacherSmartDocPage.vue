<template>
  <SdocSplitWorkspace :document-id="documentId" />
</template>

<script setup>
import { computed, provide } from 'vue'
import { useRoute } from 'vue-router'
import SdocSplitWorkspace from '@sdoc/SdocSplitWorkspace.vue'
import { SDOC_HOST_KEY } from '@sdoc/sdocHost.js'
import { getUser } from '../../utils/auth'
import teacherWs from '../../utils/websocket'
import {
  createInspireOfficeSnapshot,
  documentHref,
  fetchInspireOfficeEditorSession,
  fetchSdocCollabSnapshot,
  fetchSmartDoc,
  joinSdocCollab,
  leaveSdocCollab,
  listInspireOfficeDocuments,
  listInspireOfficeVersions,
  renameInspireOfficeDocument,
  reportInspireOfficePresence,
  reportSdocCollabState,
  restoreInspireOfficeVersion,
  saveSmartDoc,
  syncSdocCollab,
  uploadSmartDocAsset,
} from '../../services/inspireOfficeClient'

const route = useRoute()
const documentId = computed(() => route.params.id)

provide(SDOC_HOST_KEY, {
  listPath: '/inspire-office',
  getRole: () => getUser()?.role || 'TEACHER',
  getUser: () => {
    const user = getUser() || {}
    return { id: user.id, name: user.username || user.name || '', role: user.role || 'TEACHER' }
  },
  documentHref,
  uploadAsset: uploadSmartDocAsset,
  fetchSmartDoc,
  fetchEditorSession: fetchInspireOfficeEditorSession,
  saveSmartDoc,
  renameDocument: renameInspireOfficeDocument,
  listDocuments: listInspireOfficeDocuments,
  listVersions: listInspireOfficeVersions,
  createSnapshot: createInspireOfficeSnapshot,
  restoreVersion: restoreInspireOfficeVersion,
  reportPresence: reportInspireOfficePresence,
  joinCollab: joinSdocCollab,
  reportCollabState: reportSdocCollabState,
  syncCollab: syncSdocCollab,
  fetchCollabSnapshot: fetchSdocCollabSnapshot,
  leaveCollab: leaveSdocCollab,
  subscribeCollab: (topic, cb) => teacherWs.subscribe(topic, cb),
  unsubscribeCollab: (token) => teacherWs.unsubscribe(token),
  connectCollab: () => teacherWs.connect(),
})
</script>
