<template>
  <slot />
</template>

<script setup>
import { provide } from 'vue'
import { useAuthStore } from '../../../stores/auth'
import {
  createInspireOfficeSnapshot,
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
} from '../../../services/inspireOfficeClient'
import { cloudDocHref, uploadSmartDocAsset } from './upload/uploadSmartDocAsset'
import { SDOC_HOST_KEY } from './sdocHost'
import studentWs from '../../../utils/websocket'

const auth = useAuthStore()

provide(SDOC_HOST_KEY, {
  listPath: '/inspire-office',
  getRole: () => auth.user?.role || '',
  getUser: () => ({
    id: auth.user?.id,
    name: auth.user?.username || auth.user?.name || '',
    role: auth.user?.role || '',
  }),
  documentHref: cloudDocHref,
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
  subscribeCollab: (topic, cb) => studentWs.subscribe(topic, cb),
  unsubscribeCollab: (token) => studentWs.unsubscribe(token),
  connectCollab: () => studentWs.connect(),
})
</script>
