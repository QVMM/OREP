<template>
  <section class="resource-center" :class="{ 'has-preview': Boolean(previewFile) }">
    <header class="resource-center__header">
      <div class="resource-center__heading">
        <h1 class="workspace-page-title">资源中心</h1>
        <p>管理 {{ teamName || '当前团队' }} 的训练、项目交付与路演资料。</p>
      </div>
      <div class="resource-center__actions">
        <button type="button" class="rc-button" :disabled="!teamId" @click="openFolderDialog">
          <span aria-hidden="true">＋</span>
          新建文件夹
        </button>
        <button type="button" class="rc-button is-primary" :disabled="!teamId" @click="openUploadDialog">
          <span aria-hidden="true">↑</span>
          上传文件
        </button>
      </div>
    </header>

    <div v-if="!teamId" class="resource-center__no-team">
      <span aria-hidden="true">⌁</span>
      <strong>请先选择项目团队</strong>
      <p>资源会按团队隔离保存，选择团队后即可进入对应资料空间。</p>
    </div>

    <div v-else class="resource-center__window">
      <section class="resource-browser" aria-label="资源浏览区">
        <header class="resource-browser__toolbar">
          <nav class="resource-breadcrumb" aria-label="当前位置">
            <button
              type="button"
              :class="{ active: currentFolderKey === null }"
              @click="goRoot"
              @dragover.prevent="draggedFile && (rootDropActive = true)"
              @dragleave="rootDropActive = false"
              @drop.prevent="dropToRoot"
            >
              <span aria-hidden="true">⌂</span>
              资源中心
            </button>
            <template v-if="currentFolder">
              <i aria-hidden="true">/</i>
              <strong>{{ currentFolder.label }}</strong>
            </template>
            <span v-if="rootDropActive" class="resource-breadcrumb__drop">移动到根目录</span>
          </nav>

          <label class="resource-search">
            <span aria-hidden="true">⌕</span>
            <input
              v-model="searchQuery"
              type="search"
              placeholder="搜索当前目录中的文件"
              aria-label="搜索当前目录中的文件"
            >
            <button v-if="searchQuery" type="button" aria-label="清除搜索" @click="searchQuery = ''">×</button>
          </label>
        </header>

        <div v-if="loadError" class="resource-state is-error" role="alert">
          <span aria-hidden="true">!</span>
          <strong>资源暂时无法加载</strong>
          <p>{{ loadError }}</p>
          <button type="button" @click="loadWorkspace">重新加载</button>
        </div>

        <!-- 与其它业务页一致：不整屏浅灰骨架，只在内容区轻提示 -->
        <div
          v-else-if="showQuietLoading"
          class="resource-quiet-loading"
          aria-label="资源加载中"
          aria-live="polite"
        >
          <span class="resource-quiet-loading__dot" aria-hidden="true" />
          <span>加载中…</span>
        </div>

        <div
          v-else
          class="resource-browser__content"
        >
          <section v-if="currentFolderKey === null" class="resource-folders" aria-labelledby="resource-folders-title">
            <div class="resource-section-heading">
              <div>
                <span>文件夹</span>
                <strong id="resource-folders-title">按项目阶段整理</strong>
              </div>
              <small>{{ folders.length + 1 }} 个空间</small>
            </div>
            <div class="resource-folder-grid">
              <ResourceFolderBadge
                v-for="folder in folders"
                :key="folder.key"
                :folder="folder"
                :can-drop="Boolean(draggedFile)"
                @open="openFolder"
                @drop-file="dropFileToFolder"
                @manage="openFolderManageDialog"
              />
              <ResourceFolderBadge
                :folder="publicFolder"
                readonly
                @open="openFolder"
              />
            </div>
          </section>

          <section class="resource-files" :aria-labelledby="'resource-file-list-title'">
            <div class="resource-section-heading is-files">
              <div>
                <span>{{ currentFolderKey === null ? '当前位置' : '目录内容' }}</span>
                <strong id="resource-file-list-title">{{ fileSectionTitle }}</strong>
              </div>
              <small>{{ filteredFiles.length }} 份资料 · 按最近更新排序</small>
            </div>

            <div v-if="!filteredFiles.length" class="resource-empty">
              <span class="resource-empty__icon" aria-hidden="true">{{ searchQuery ? '⌕' : '↥' }}</span>
              <strong>{{ searchQuery ? '没有匹配的文件' : emptyTitle }}</strong>
              <p>{{ searchQuery ? '换一个关键词，或清除搜索后查看全部资料。' : emptyDescription }}</p>
              <button v-if="searchQuery" type="button" @click="searchQuery = ''">清除搜索</button>
              <button v-else-if="currentFolderKey !== 'public'" type="button" @click="openUploadDialog">上传文件</button>
            </div>

            <div v-else class="resource-file-table" role="list">
              <div class="resource-file-table__head" aria-hidden="true">
                <span>文件</span>
                <span>大小</span>
                <span>更新时间</span>
                <span>操作</span>
              </div>
              <article
                v-for="file in filteredFiles"
                :key="file.id"
                class="resource-file-row"
                :class="{
                  'is-active': previewFile?.id === file.id,
                  'is-selected': selectedFile?.id === file.id,
                  'is-public': file.public
                }"
                role="listitem"
                tabindex="0"
                :draggable="!file.public"
                @click="selectFile(file)"
                @dblclick="openImmersivePreview(file)"
                @keydown.enter.prevent="selectFile(file)"
                @keydown.space.prevent="selectFile(file)"
                @dragstart="startFileDrag($event, file)"
                @dragend="endFileDrag"
              >
                <span class="resource-file-row__name">
                  <i :class="`is-${fileTone(file)}`" aria-hidden="true">{{ fileLabel(file) }}</i>
                  <span>
                    <strong>{{ file.name }}</strong>
                    <small>{{ fileKind(file) }}{{ file.public ? ' · 公共只读' : '' }}</small>
                  </span>
                </span>
                <span class="resource-file-row__size">{{ file.size || formatSize(file.fileSize) }}</span>
                <span class="resource-file-row__date">{{ formatDate(file.updatedAt || file.createdAt) }}</span>
                <span class="resource-file-row__actions" @click.stop>
                  <a
                    class="rc-icon-btn"
                    :href="securedUrl(file.downloadUrl)"
                    :download="file.name"
                    title="下载"
                    aria-label="下载"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M12 3v12m0 0 4.5-4.5M12 15l-4.5-4.5M5 19h14" />
                    </svg>
                  </a>
                  <label
                    v-if="!file.public"
                    class="rc-icon-btn is-select"
                    :title="`移动 ${file.name}`"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M3.5 8.5V7a2 2 0 0 1 2-2h4.2l1.6 1.8H18.5a2 2 0 0 1 2 2v1.2M3.5 10.5h17v6a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2v-6Z" />
                      <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M12 12.2v4.2m0 0 2-2m-2 2-2-2" />
                    </svg>
                    <select
                      :aria-label="`移动 ${file.name}`"
                      :value="file.folderKey"
                      @change="moveFromSelect(file, $event)"
                    >
                      <option disabled :value="file.folderKey">移动到</option>
                      <option v-if="file.folderKey !== rootFolderKey" :value="rootFolderKey">根目录</option>
                      <option
                        v-for="folder in movableFolders(file)"
                        :key="folder.key"
                        :value="folder.key"
                      >
                        {{ folder.label }}
                      </option>
                    </select>
                  </label>
                  <button
                    v-if="canDeleteFile(file)"
                    type="button"
                    class="rc-icon-btn is-danger"
                    :disabled="deletingId === file.id"
                    :title="deletingId === file.id ? '删除中…' : `删除 ${file.name}`"
                    :aria-label="deletingId === file.id ? '删除中' : '删除'"
                    @click="deleteFile(file)"
                  >
                    <svg v-if="deletingId !== file.id" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M5 7h14M9.5 7V5.8A1.3 1.3 0 0 1 10.8 4.5h2.4a1.3 1.3 0 0 1 1.3 1.3V7m-7.5 0 1 11.2A1.5 1.5 0 0 0 9.2 19.5h5.6a1.5 1.5 0 0 0 1.5-1.3L17.2 7M10 10.5v6m4-6v6" />
                    </svg>
                    <svg v-else class="is-spin" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                      <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-dasharray="36 20" stroke-linecap="round" />
                    </svg>
                  </button>
                </span>
              </article>
            </div>
          </section>
        </div>
      </section>

      <aside class="resource-preview" :class="{ 'is-open': Boolean(previewFile) }" aria-label="文件预览">
        <header class="resource-preview__bar">
          <div>
            <span class="resource-preview__pulse" aria-hidden="true" />
            <strong>文件预览</strong>
            <small>{{ previewFile ? '点击文件切换预览' : '点击文件开始预览' }}</small>
          </div>
          <div v-if="previewFile" class="resource-preview__actions">
            <a
              class="rc-icon-btn"
              :href="securedUrl(previewFile.downloadUrl)"
              :download="previewFile.name"
              title="下载"
              aria-label="下载"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M12 3v12m0 0 4.5-4.5M12 15l-4.5-4.5M5 19h14" />
              </svg>
            </a>
            <button
              type="button"
              class="rc-icon-btn"
              title="展开预览"
              aria-label="展开预览"
              @click="openImmersivePreview(previewFile)"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M9 4.5H5.5A1 1 0 0 0 4.5 5.5V9M15 4.5h3.5a1 1 0 0 1 1 1V9M9 19.5H5.5a1 1 0 0 1-1-1V15M15 19.5h3.5a1 1 0 0 0 1-1V15" />
              </svg>
            </button>
            <button
              v-if="canDeleteFile(previewFile)"
              type="button"
              class="rc-icon-btn is-danger"
              :disabled="deletingId === previewFile.id"
              :title="deletingId === previewFile.id ? '删除中…' : '删除'"
              :aria-label="deletingId === previewFile.id ? '删除中' : '删除'"
              @click="deleteFile(previewFile)"
            >
              <svg v-if="deletingId !== previewFile.id" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" d="M5 7h14M9.5 7V5.8A1.3 1.3 0 0 1 10.8 4.5h2.4a1.3 1.3 0 0 1 1.3 1.3V7m-7.5 0 1 11.2A1.5 1.5 0 0 0 9.2 19.5h5.6a1.5 1.5 0 0 0 1.5-1.3L17.2 7M10 10.5v6m4-6v6" />
              </svg>
              <svg v-else class="is-spin" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-dasharray="36 20" stroke-linecap="round" />
              </svg>
            </button>
            <button type="button" class="rc-icon-btn resource-preview__mobile-close" aria-label="关闭预览" @click="closeMobilePreview">
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" d="M7 7l10 10M17 7 7 17" />
              </svg>
            </button>
          </div>
        </header>

        <div v-if="!previewFile" class="resource-preview__empty">
          <span class="resource-preview__empty-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <strong>快速查看文件内容</strong>
          <p>点击文件即可在这里预览 PDF、Word、Excel、PPT、图片和音视频，无需反复打开弹窗。</p>
          <small>支持 Enter 或 Space 预览，双击展开</small>
        </div>

        <FilePreview
          v-else
          :key="`inline-${previewFile.id}`"
          visible
          inline
          :file-url="previewFile.previewUrl"
          :file-name="previewFile.name"
          :file-type="previewFile.mimeType"
          @download="downloadFile(previewFile)"
        />
      </aside>
    </div>

    <FilePreview
      v-if="immersiveFile"
      :key="`immersive-${immersiveFile.id}`"
      :visible="immersiveVisible"
      :file-url="immersiveFile.previewUrl"
      :file-name="immersiveFile.name"
      :file-type="immersiveFile.mimeType"
      @update:visible="closeImmersivePreview"
      @download="downloadFile(immersiveFile)"
    />

    <div v-if="folderDialogVisible" class="resource-dialog-backdrop" @click.self="closeFolderDialog">
      <section class="resource-dialog resource-dialog--compact" role="dialog" aria-modal="true" aria-labelledby="resource-folder-dialog-title">
        <header>
          <div>
            <span>ORGANIZE</span>
            <strong id="resource-folder-dialog-title">新建文件夹</strong>
          </div>
          <button type="button" aria-label="关闭" @click="closeFolderDialog">×</button>
        </header>
        <label>
          <span>文件夹名称</span>
          <input
            ref="folderNameInput"
            v-model="folderName"
            maxlength="30"
            placeholder="例如：答辩素材、竞品资料"
            @keydown.enter.prevent="submitFolder"
          >
        </label>
        <p>文件夹仅属于 {{ teamName || '当前团队' }}，不会与其他团队共享。</p>
        <footer>
          <button type="button" @click="closeFolderDialog">取消</button>
          <button type="button" class="is-primary" :disabled="folderBusy || !folderName.trim()" @click="submitFolder">
            {{ folderBusy ? '创建中…' : '创建文件夹' }}
          </button>
        </footer>
      </section>
    </div>

    <div v-if="folderManageVisible" class="resource-dialog-backdrop" @click.self="closeFolderManageDialog">
      <section class="resource-dialog resource-dialog--compact" role="dialog" aria-modal="true" aria-labelledby="resource-folder-manage-title">
        <header>
          <div>
            <span>FOLDER SETTINGS</span>
            <strong id="resource-folder-manage-title">管理文件夹</strong>
          </div>
          <button type="button" aria-label="关闭" @click="closeFolderManageDialog">×</button>
        </header>
        <label>
          <span>文件夹名称</span>
          <input v-model="managedFolderName" maxlength="30" @keydown.enter.prevent="renameManagedFolder">
        </label>
        <p>{{ managedFolder?.count ? `文件夹内有 ${managedFolder.count} 份资料，移空后才能删除。` : '当前为空文件夹，可重命名或删除。' }}</p>
        <footer class="is-spread">
          <button type="button" class="is-danger" :disabled="Boolean(managedFolder?.count) || folderBusy" @click="deleteManagedFolder">删除文件夹</button>
          <span>
            <button type="button" @click="closeFolderManageDialog">取消</button>
            <button type="button" class="is-primary" :disabled="folderBusy || !managedFolderName.trim()" @click="renameManagedFolder">
              {{ folderBusy ? '保存中…' : '保存名称' }}
            </button>
          </span>
        </footer>
      </section>
    </div>

    <div v-if="uploadDialogVisible" class="resource-dialog-backdrop" @click.self="closeUploadDialog">
      <section class="resource-dialog" role="dialog" aria-modal="true" aria-labelledby="resource-upload-dialog-title">
        <header>
          <div>
            <span>UPLOAD TO TEAM SPACE</span>
            <strong id="resource-upload-dialog-title">上传文件</strong>
          </div>
          <button type="button" aria-label="关闭" @click="closeUploadDialog">×</button>
        </header>
        <label>
          <span>保存位置</span>
          <select v-model="uploadFolderKey">
            <option :value="rootFolderKey">根目录</option>
            <option v-for="folder in folders" :key="folder.key" :value="folder.key">{{ folder.label }}</option>
          </select>
        </label>
        <DropFileUpload
          v-model="uploadFile"
          size="md"
          :accept="acceptedFileTypes"
          :disabled="uploadBusy"
          title="拖拽资料到此处，或点击选择"
          hint="支持 PDF、Word、Excel、PPT、图片、音视频和文本"
          accept-hint="松开鼠标即可添加"
          @error="onUploadDropError"
        />
        <div v-if="uploadBusy" class="resource-upload-progress" aria-live="polite">
          <span :style="{ width: `${uploadProgress}%` }" />
          <strong>{{ uploadProgress }}%</strong>
        </div>
        <footer>
          <button type="button" :disabled="uploadBusy" @click="closeUploadDialog">取消</button>
          <button type="button" class="is-primary" :disabled="uploadBusy || !uploadFile" @click="submitUpload">
            {{ uploadBusy ? '正在上传…' : '上传到团队空间' }}
          </button>
        </footer>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FilePreview from '../FilePreview.vue'
import DropFileUpload from '../base/DropFileUpload.vue'
import ResourceFolderBadge from './ResourceFolderBadge.vue'
import { withAuthMediaUrl } from '../../utils/mediaUrl'
import {
  createResourceFolder,
  deleteResourceFile,
  deleteResourceFolder,
  getResourceCenterWorkspace,
  moveResourceFile,
  renameResourceFolder,
  uploadResourceFile
} from '../../services/resourceCenterClient'

const props = defineProps({
  teamId: { type: [Number, String], default: null },
  teamName: { type: String, default: '' }
})

const loading = ref(false)
const hasLoadedOnce = ref(false)
const loadError = ref('')
const folders = ref([])
const teamFiles = ref([])
const publicFiles = ref([])
const rootFolderKey = ref('root')
const currentFolderKey = ref(null)
const searchQuery = ref('')
const selectedFile = ref(null)
const immersiveFile = ref(null)
const immersiveVisible = ref(false)
const draggedFile = ref(null)
const rootDropActive = ref(false)
const folderDialogVisible = ref(false)
const folderName = ref('')
const folderBusy = ref(false)
const folderNameInput = ref(null)
const folderManageVisible = ref(false)
const managedFolder = ref(null)
const managedFolderName = ref('')
const uploadDialogVisible = ref(false)
const uploadFile = ref(null)
const uploadFolderKey = ref('root')
const uploadBusy = ref(false)
const uploadProgress = ref(0)
const deletingId = ref(null)
let loadSequence = 0

/** 冷启动仅一行轻提示；有缓存数据后刷新不再挡内容 */
const showQuietLoading = computed(() => loading.value && !hasLoadedOnce.value)

const acceptedFileTypes = [
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.ppt', '.pptx',
  '.sdoc',
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
  '.mp4', '.webm', '.mov', '.mkv', '.avi',
  '.mp3', '.wav', '.m4a', '.aac', '.ogg',
  '.txt', '.md'
].join(',')

const currentFolder = computed(() => {
  if (!currentFolderKey.value) return null
  if (currentFolderKey.value === 'public') return publicFolder.value
  return folders.value.find(folder => folder.key === currentFolderKey.value) || null
})

const publicFolder = computed(() => ({
  id: null,
  key: 'public',
  label: '公共资源',
  tone: 'public',
  count: publicFiles.value.length,
  covers: publicFiles.value.slice(0, 3),
  system: true
}))

const directoryFiles = computed(() => {
  if (currentFolderKey.value === 'public') return publicFiles.value
  const target = currentFolderKey.value || rootFolderKey.value
  return teamFiles.value.filter(file => file.folderKey === target)
})

const filteredFiles = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return directoryFiles.value
  return directoryFiles.value.filter(file => [
    file.name,
    file.ext,
    file.uploaderName,
    fileKind(file)
  ].some(value => String(value || '').toLowerCase().includes(query)))
})

const previewFile = computed(() => selectedFile.value)
const fileSectionTitle = computed(() => {
  if (currentFolderKey.value === null) return '未归类文件'
  return currentFolder.value?.label || '当前目录'
})
const emptyTitle = computed(() => currentFolderKey.value === null ? '根目录还没有散落文件' : '这个文件夹还是空的')
const emptyDescription = computed(() => currentFolderKey.value === 'public'
  ? '公共资料由平台统一维护。'
  : '把文件拖进这里，或上传第一份团队资料。')

watch(
  () => props.teamId,
  async (next, prev) => {
    if (String(next || '') !== String(prev || '')) {
      currentFolderKey.value = null
      selectedFile.value = null
      searchQuery.value = ''
      hasLoadedOnce.value = false
    }
    await loadWorkspace()
  },
  { immediate: true }
)

async function loadWorkspace() {
  const teamId = Number(props.teamId)
  if (!teamId) {
    loading.value = false
    return
  }
  const sequence = ++loadSequence
  if (!hasLoadedOnce.value) loading.value = true
  loadError.value = ''
  try {
    const response = await getResourceCenterWorkspace(teamId)
    if (sequence !== loadSequence) return
    const data = response?.data || {}
    folders.value = Array.isArray(data.folders) ? data.folders : []
    teamFiles.value = Array.isArray(data.teamFiles) ? data.teamFiles : []
    publicFiles.value = Array.isArray(data.publicFiles) ? data.publicFiles : []
    rootFolderKey.value = data.rootFolderKey || 'root'
    if (currentFolderKey.value && currentFolderKey.value !== 'public'
      && !folders.value.some(folder => folder.key === currentFolderKey.value)) {
      currentFolderKey.value = null
    }
    syncCurrentFile()
    hasLoadedOnce.value = true
  } catch (error) {
    if (sequence !== loadSequence) return
    loadError.value = error?.response?.data?.message || error?.message || '请检查网络后重试'
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

function syncCurrentFile() {
  if (selectedFile.value) {
    selectedFile.value = [...teamFiles.value, ...publicFiles.value]
      .find(file => file.id === selectedFile.value.id) || null
  }
}

function goRoot() {
  currentFolderKey.value = null
  searchQuery.value = ''
  selectedFile.value = null
}

function openFolder(folder) {
  currentFolderKey.value = folder.key
  searchQuery.value = ''
  selectedFile.value = null
}

function selectFile(file) {
  selectedFile.value = file
}

function openImmersivePreview(file) {
  immersiveFile.value = file
  immersiveVisible.value = true
}

function closeImmersivePreview(visible) {
  immersiveVisible.value = visible
  if (!visible) immersiveFile.value = null
}

function closeMobilePreview() {
  selectedFile.value = null
}

function startFileDrag(event, file) {
  draggedFile.value = file
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(file.id))
}

function endFileDrag() {
  draggedFile.value = null
  rootDropActive.value = false
}

async function dropFileToFolder(folder) {
  if (!draggedFile.value) return
  await moveFile(draggedFile.value, folder.key, folder.label)
  endFileDrag()
}

async function dropToRoot() {
  rootDropActive.value = false
  if (!draggedFile.value) return
  await moveFile(draggedFile.value, rootFolderKey.value, '根目录')
  endFileDrag()
}

function moveFromSelect(file, event) {
  const folderKey = event.target.value
  const folderLabel = folderKey === rootFolderKey.value
    ? '根目录'
    : folders.value.find(folder => folder.key === folderKey)?.label || '目标文件夹'
  event.target.value = file.folderKey
  moveFile(file, folderKey, folderLabel)
}

async function moveFile(file, folderKey, folderLabel) {
  if (!file || file.public || file.folderKey === folderKey) return
  const previousKey = file.folderKey
  const previousFiles = teamFiles.value
  teamFiles.value = teamFiles.value.map(item => item.id === file.id
    ? { ...item, folderKey, updatedAt: new Date().toISOString() }
    : item)
  refreshFolderSummaries()
  if (currentFolderKey.value && currentFolderKey.value !== folderKey) {
    selectedFile.value = null
  }
  try {
    const response = await moveResourceFile(Number(props.teamId), file.id, folderKey)
    const updated = response?.data
    if (updated?.id) {
      teamFiles.value = teamFiles.value.map(item => item.id === updated.id ? updated : item)
    }
    refreshFolderSummaries()
    ElMessage.success(`已移动到${folderLabel}`)
  } catch (error) {
    teamFiles.value = previousFiles
    refreshFolderSummaries()
    if (file.id === selectedFile.value?.id) selectedFile.value = { ...file, folderKey: previousKey }
    ElMessage.error(error?.response?.data?.message || error?.message || '移动失败，文件已恢复原位置')
  }
}

function refreshFolderSummaries() {
  folders.value = folders.value.map(folder => {
    const files = teamFiles.value.filter(file => file.folderKey === folder.key)
    return { ...folder, count: files.length, covers: files.slice(0, 3) }
  })
}

function movableFolders(file) {
  return folders.value.filter(folder => folder.key !== file.folderKey)
}

/** 团队资料可删（含未归类/根目录）；公共只读不可删 */
function canDeleteFile(file) {
  return Boolean(file && !file.public && file.id)
}

async function deleteFile(file) {
  if (!canDeleteFile(file) || deletingId.value) return
  try {
    await ElMessageBox.confirm(
      `确定删除「${file.name}」？删除后不可恢复。`,
      '删除文件',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  deletingId.value = file.id
  try {
    await deleteResourceFile(Number(props.teamId), file.id)
    teamFiles.value = teamFiles.value.filter(item => item.id !== file.id)
    refreshFolderSummaries()
    if (selectedFile.value?.id === file.id) selectedFile.value = null
    if (immersiveFile.value?.id === file.id) {
      immersiveVisible.value = false
      immersiveFile.value = null
    }
    ElMessage.success('文件已删除')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '删除失败，请重试')
  } finally {
    deletingId.value = null
  }
}

function openFolderDialog() {
  folderName.value = ''
  folderDialogVisible.value = true
  nextTick(() => folderNameInput.value?.focus())
}

function closeFolderDialog() {
  if (folderBusy.value) return
  folderDialogVisible.value = false
}

async function submitFolder() {
  const label = folderName.value.trim()
  if (!label || folderBusy.value) return
  folderBusy.value = true
  try {
    const response = await createResourceFolder(Number(props.teamId), label)
    if (response?.data) folders.value = [response.data, ...folders.value]
    folderDialogVisible.value = false
    ElMessage.success('文件夹已创建')
  } finally {
    folderBusy.value = false
  }
}

function openFolderManageDialog(folder) {
  managedFolder.value = folder
  managedFolderName.value = folder.label
  folderManageVisible.value = true
}

function closeFolderManageDialog() {
  if (folderBusy.value) return
  folderManageVisible.value = false
  managedFolder.value = null
}

async function renameManagedFolder() {
  const label = managedFolderName.value.trim()
  if (!managedFolder.value?.id || !label || folderBusy.value) return
  folderBusy.value = true
  try {
    await renameResourceFolder(Number(props.teamId), managedFolder.value.id, label)
    folders.value = folders.value.map(folder => folder.id === managedFolder.value.id
      ? { ...folder, label }
      : folder)
    folderManageVisible.value = false
    ElMessage.success('文件夹名称已更新')
  } finally {
    folderBusy.value = false
  }
}

async function deleteManagedFolder() {
  if (!managedFolder.value?.id || managedFolder.value.count || folderBusy.value) return
  try {
    await ElMessageBox.confirm(
      `删除空文件夹“${managedFolder.value.label}”？`,
      '删除文件夹',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  folderBusy.value = true
  try {
    await deleteResourceFolder(Number(props.teamId), managedFolder.value.id)
    folders.value = folders.value.filter(folder => folder.id !== managedFolder.value.id)
    folderManageVisible.value = false
    ElMessage.success('空文件夹已删除')
  } finally {
    folderBusy.value = false
  }
}

function openUploadDialog() {
  uploadFile.value = null
  uploadProgress.value = 0
  uploadFolderKey.value = currentFolderKey.value && currentFolderKey.value !== 'public'
    ? currentFolderKey.value
    : rootFolderKey.value
  uploadDialogVisible.value = true
}

function closeUploadDialog() {
  if (uploadBusy.value) return
  uploadDialogVisible.value = false
}

function onUploadDropError(err) {
  ElMessage.warning(err?.message || '文件不符合要求')
}

async function submitUpload() {
  if (!uploadFile.value || uploadBusy.value) return
  uploadBusy.value = true
  uploadProgress.value = 0
  try {
    const response = await uploadResourceFile(
      Number(props.teamId),
      uploadFolderKey.value,
      uploadFile.value,
      event => {
        if (!event.total) return
        uploadProgress.value = Math.min(99, Math.round((event.loaded / event.total) * 100))
      }
    )
    uploadProgress.value = 100
    if (response?.data) teamFiles.value = [response.data, ...teamFiles.value]
    refreshFolderSummaries()
    uploadDialogVisible.value = false
    ElMessage.success('文件上传成功')
    if (currentFolderKey.value === uploadFolderKey.value
      || (currentFolderKey.value === null && uploadFolderKey.value === rootFolderKey.value)) {
      selectedFile.value = response?.data || null
    }
  } finally {
    uploadBusy.value = false
  }
}

function downloadFile(file) {
  if (!file?.downloadUrl) return
  const link = document.createElement('a')
  link.href = securedUrl(file.downloadUrl)
  link.download = file.name || 'resource'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

function securedUrl(url) {
  return withAuthMediaUrl(url)
}

function fileLabel(file) {
  const ext = String(file?.ext || file?.name?.split('.').pop() || 'FILE').toUpperCase()
  return ext.length > 5 ? 'FILE' : ext
}

function fileTone(file) {
  const ext = String(file?.ext || file?.name?.split('.').pop() || '').toLowerCase()
  if (['xls', 'xlsx', 'csv'].includes(ext)) return 'sheet'
  if (['ppt', 'pptx'].includes(ext)) return 'slides'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'image'
  if (['mp4', 'webm', 'mov', 'mkv', 'avi'].includes(ext)) return 'video'
  if (['mp3', 'wav', 'm4a', 'aac', 'ogg'].includes(ext)) return 'audio'
  if (ext === 'pdf') return 'pdf'
  if (ext === 'sdoc') return 'sdoc'
  return 'document'
}

function fileKind(file) {
  const tone = fileTone(file)
  return {
    sheet: '数据表格',
    slides: '演示文稿',
    image: '图片素材',
    video: '视频',
    audio: '音频',
    pdf: 'PDF 文档',
    sdoc: '智能文档',
    document: '文档'
  }[tone]
}

function formatSize(bytes) {
  const value = Number(bytes || 0)
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`
  return `${(value / 1024 / 1024 / 1024).toFixed(2)} GB`
}

function formatDate(value) {
  if (!value) return '最近更新'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  const now = new Date()
  if (date.toDateString() === now.toDateString()) {
    return `今天 ${date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
  }
  return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', year: 'numeric' })
}

onBeforeUnmount(() => {
  loadSequence += 1
})
</script>

<style scoped>
.resource-center {
  --rc-accent: var(--ds-orange-600, #ed4b20);
  --rc-accent-dark: #c93613;
  --rc-ink: var(--ds-ink, #151820);
  --rc-copy: #343944;
  --rc-muted: #7b8290;
  --rc-border: #e5e8ee;
  --rc-surface: #fff;
  --rc-canvas: #f6f7f9;
  width: 100%;
  min-width: 0;
  display: grid;
  gap: 18px;
  color: var(--rc-copy);
}

.resource-center__header {
  min-width: 0;
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
}

.resource-center__heading {
  min-width: 0;
}

.resource-center__heading h1 {
  color: var(--rc-ink);
}

.resource-center__heading p {
  margin: 7px 0 0;
  color: var(--rc-muted);
  font-size: 13px;
}

.resource-center__actions {
  display: flex;
  gap: 10px;
}

.rc-button {
  min-height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 16px;
  border: 1px solid #d9dde5;
  border-radius: 999px;
  background: #fff;
  color: #343944;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.rc-button:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: #c6cbd4;
  background: #f8f9fa;
}

.rc-button.is-primary {
  border-color: var(--rc-accent);
  background: var(--rc-accent);
  color: #fff;
  box-shadow: 0 8px 18px rgba(237, 75, 32, .18);
}

.rc-button.is-primary:hover:not(:disabled) {
  border-color: var(--rc-accent-dark);
  background: var(--rc-accent-dark);
}

.rc-button:disabled {
  cursor: not-allowed;
  opacity: .5;
}

.resource-center__window {
  min-height: min(720px, calc(100vh - 152px));
  display: grid;
  grid-template-columns: minmax(520px, 1fr) clamp(360px, 38vw, 560px);
  overflow: hidden;
  border: 1px solid var(--rc-border);
  border-radius: 22px;
  background: var(--rc-surface);
  box-shadow: 0 18px 50px rgba(31, 38, 51, .08);
}

.resource-browser {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  border-right: 1px solid var(--rc-border);
}

.resource-browser__toolbar {
  min-width: 0;
  min-height: 62px;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(220px, 360px);
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--rc-border);
  background: rgba(255,255,255,.96);
}

.resource-breadcrumb {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow: hidden;
}

.resource-breadcrumb button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: #616977;
  cursor: pointer;
  font-size: 13px;
  font-weight: 760;
}

.resource-breadcrumb button:hover,
.resource-breadcrumb button.active {
  background: #f3f4f6;
  color: #20252e;
}

.resource-breadcrumb i {
  color: #b0b5be;
  font-style: normal;
}

.resource-breadcrumb strong {
  min-width: 0;
  overflow: hidden;
  color: #20252e;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-breadcrumb__drop {
  padding: 5px 8px;
  border-radius: 8px;
  background: #fff0e8;
  color: var(--rc-accent);
  font-size: 11px;
  font-weight: 850;
}

.resource-search {
  height: 38px;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr) auto;
  align-items: center;
  gap: 4px;
  padding: 0 10px;
  border: 1px solid #dfe3e9;
  border-radius: 12px;
  background: #f8f9fb;
  color: #9aa0aa;
}

.resource-search:focus-within {
  border-color: rgba(237, 75, 32, .55);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(237, 75, 32, .09);
}

.resource-search input {
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--rc-copy);
  font-size: 12px;
}

.resource-search button {
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: #8a919d;
  cursor: pointer;
}

.resource-browser__content {
  min-height: 0;
  overflow: auto;
  padding: 20px;
  background:
    linear-gradient(rgba(255,255,255,.9), rgba(255,255,255,.9)),
    radial-gradient(circle at 14% 4%, rgba(237,75,32,.08), transparent 28%);
}

/* 与其它页一致的轻加载：无灰块骨架 */
.resource-quiet-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 280px;
  color: #8b919c;
  font-size: 13px;
  font-weight: 600;
}

.resource-quiet-loading__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ds-orange-action, #e84a1c);
  opacity: 0.75;
  animation: resource-quiet-pulse 1s ease-in-out infinite;
}

@keyframes resource-quiet-pulse {
  0%, 100% { opacity: 0.35; transform: scale(0.9); }
  50% { opacity: 0.9; transform: scale(1); }
}

.resource-folders,
.resource-files {
  min-width: 0;
}

.resource-files {
  margin-top: 24px;
}

.resource-browser__content > .resource-files:first-child {
  margin-top: 0;
}

.resource-section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.resource-section-heading div,
.resource-section-heading span,
.resource-section-heading strong {
  display: block;
}

.resource-section-heading span {
  color: #9a5b42;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .09em;
  text-transform: uppercase;
}

.resource-section-heading strong {
  margin-top: 3px;
  color: var(--rc-ink);
  font-size: 15px;
  font-weight: 820;
}

.resource-section-heading small {
  color: #9299a5;
  font-size: 11px;
}

.resource-folder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(198px, 1fr));
  gap: 12px;
}

.resource-file-table {
  overflow: hidden;
  border: 1px solid #eaecf0;
  border-radius: 16px;
  background: #fff;
}

.resource-file-table__head,
.resource-file-row {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(240px, 1fr) 80px 116px 138px;
  align-items: center;
  gap: 12px;
  padding: 0 14px;
}

.resource-file-table__head {
  min-height: 34px;
  border-bottom: 1px solid #eceef2;
  background: #f8f9fa;
  color: #949aa4;
  font-size: 10px;
  font-weight: 850;
}

.resource-file-table__head span:last-child {
  justify-self: end;
  padding-right: 10px;
}

.resource-file-row {
  min-height: 66px;
  border-bottom: 1px solid #eff1f4;
  outline: none;
  cursor: default;
  transition: background 140ms ease, box-shadow 140ms ease;
}

.resource-file-row:last-child {
  border-bottom: 0;
}

.resource-file-row:hover,
.resource-file-row:focus-visible,
.resource-file-row.is-active {
  background: #fff8f4;
}

.resource-file-row.is-selected {
  box-shadow: inset 3px 0 var(--rc-accent);
}

.resource-file-row:focus-visible {
  box-shadow: inset 0 0 0 2px rgba(237,75,32,.45);
}

.resource-file-row__name {
  min-width: 0;
  display: grid;
  grid-template-columns: 38px minmax(0, 1fr);
  align-items: center;
  gap: 10px;
}

.resource-file-row__name > i {
  width: 38px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 9px;
  background: #5c83df;
  color: #fff;
  font-size: 8px;
  font-style: normal;
  font-weight: 900;
  letter-spacing: .04em;
  box-shadow: 0 5px 12px rgba(42,61,100,.13);
}

.resource-file-row__name > i.is-pdf { background: #e2573d; }
.resource-file-row__name > i.is-sheet { background: #218a67; }
.resource-file-row__name > i.is-slides { background: #e56a2f; }
.resource-file-row__name > i.is-image { background: #5f70d8; }
.resource-file-row__name > i.is-video { background: #704ebd; }
.resource-file-row__name > i.is-audio { background: #8a4ead; }

.resource-file-row__name span,
.resource-file-row__name strong,
.resource-file-row__name small {
  min-width: 0;
  display: block;
}

.resource-file-row__name strong {
  overflow: hidden;
  color: #262b34;
  font-size: 12px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-file-row__name small {
  margin-top: 4px;
  color: #9298a3;
  font-size: 10px;
}

.resource-file-row__size,
.resource-file-row__date {
  color: #858c98;
  font-size: 10px;
}

.resource-file-row__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
}

/* 纯 SVG 操作：无边框、无底色字按钮 */
.rc-icon-btn {
  box-sizing: border-box;
  position: relative;
  width: 32px;
  height: 32px;
  margin: 0;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #6b7280;
  text-decoration: none;
  cursor: pointer;
  appearance: none;
  font: inherit;
  transition: color .15s ease, background-color .15s ease;
}

.rc-icon-btn svg {
  width: 18px;
  height: 18px;
  display: block;
  flex: none;
}

.rc-icon-btn:hover:not(:disabled) {
  color: #111827;
  background: rgba(15, 23, 42, 0.05);
}

.rc-icon-btn:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--rc-accent, #e5481d) 55%, transparent);
  outline-offset: 1px;
}

.rc-icon-btn.is-danger {
  color: #b4533a;
}

.rc-icon-btn.is-danger:hover:not(:disabled) {
  color: #c43d20;
  background: rgba(196, 61, 32, 0.08);
}

.rc-icon-btn:disabled {
  opacity: .45;
  cursor: not-allowed;
}

.rc-icon-btn.is-select {
  overflow: hidden;
}

.rc-icon-btn.is-select select {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  opacity: 0;
  border: 0;
  cursor: pointer;
  font-size: 16px; /* 避免 iOS 缩放 */
}

.rc-icon-btn svg.is-spin {
  animation: rc-icon-spin .7s linear infinite;
}

@keyframes rc-icon-spin {
  to { transform: rotate(360deg); }
}

.resource-preview {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  background: #f5f6f8;
}

.resource-preview__bar {
  min-height: 62px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--rc-border);
  background: #fff;
}

.resource-preview__bar > div:first-child {
  min-width: 0;
  display: grid;
  grid-template-columns: 9px minmax(0, 1fr);
  align-items: center;
  column-gap: 8px;
}

.resource-preview__bar strong,
.resource-preview__bar small {
  min-width: 0;
  display: block;
  grid-column: 2;
}

.resource-preview__bar strong {
  color: #252a33;
  font-size: 12px;
  font-weight: 850;
}

.resource-preview__bar small {
  margin-top: 2px;
  overflow: hidden;
  color: #969ca6;
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-preview__pulse {
  grid-row: 1 / span 2;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #28a978;
  box-shadow: 0 0 0 4px rgba(40,169,120,.11);
}

.resource-preview__actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.resource-preview__mobile-close {
  display: none !important;
}

.resource-preview__empty {
  min-height: 0;
  display: grid;
  align-content: center;
  justify-items: center;
  padding: 34px;
  text-align: center;
}

.resource-preview__empty-mark {
  position: relative;
  width: 120px;
  height: 104px;
  margin-bottom: 24px;
}

.resource-preview__empty-mark i {
  position: absolute;
  inset: 8px 22px 20px;
  border: 1px solid #dfe3e8;
  border-radius: 13px;
  background: #fff;
  box-shadow: 0 12px 28px rgba(37,44,58,.08);
}

.resource-preview__empty-mark i:nth-child(1) { transform: translateX(-17px) rotate(-7deg); }
.resource-preview__empty-mark i:nth-child(2) { transform: translateX(17px) rotate(7deg); }
.resource-preview__empty-mark i:nth-child(3) {
  background:
    linear-gradient(#f0f2f5 0 0) 16px 18px / 45px 4px no-repeat,
    linear-gradient(#f0f2f5 0 0) 16px 30px / 36px 4px no-repeat,
    linear-gradient(145deg, #fff, #fff6f1);
}

.resource-preview__empty strong {
  color: #303640;
  font-size: 15px;
  font-weight: 850;
}

.resource-preview__empty p {
  max-width: 330px;
  margin: 10px 0 0;
  color: #858c98;
  font-size: 11px;
  line-height: 1.75;
}

.resource-preview__empty small {
  margin-top: 14px;
  color: #a0a6b0;
  font-size: 9px;
}

.resource-state,
.resource-center__no-team,
.resource-empty {
  display: grid;
  justify-items: center;
  align-content: center;
  min-height: 320px;
  padding: 30px;
  text-align: center;
}

.resource-state > span,
.resource-center__no-team > span,
.resource-empty__icon {
  width: 50px;
  height: 50px;
  display: grid;
  place-items: center;
  margin-bottom: 14px;
  border-radius: 16px;
  background: #fff0e8;
  color: var(--rc-accent);
  font-size: 22px;
  font-weight: 900;
}

.resource-state strong,
.resource-center__no-team strong,
.resource-empty strong {
  color: #2c313a;
  font-size: 15px;
}

.resource-state p,
.resource-center__no-team p,
.resource-empty p {
  max-width: 420px;
  margin: 8px 0 16px;
  color: #858c98;
  font-size: 11px;
  line-height: 1.7;
}

.resource-state button,
.resource-empty button {
  min-height: 34px;
  padding: 0 13px;
  border: 1px solid #dce0e6;
  border-radius: 10px;
  background: #fff;
  color: #3f4652;
  cursor: pointer;
  font-size: 11px;
  font-weight: 800;
}

.resource-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal, 1050);
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(29,33,41,.46);
  backdrop-filter: blur(5px);
}

.resource-dialog {
  width: min(520px, 100%);
  display: grid;
  gap: 18px;
  padding: 22px;
  border: 1px solid rgba(255,255,255,.75);
  border-radius: 20px;
  background: #fff;
  box-shadow: 0 28px 80px rgba(21,27,38,.2);
}

.resource-dialog--compact {
  width: min(440px, 100%);
}

.resource-dialog > header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}

.resource-dialog > header span,
.resource-dialog > header strong {
  display: block;
}

.resource-dialog > header span {
  margin-bottom: 4px;
  color: var(--rc-accent);
  font-size: 9px;
  font-weight: 900;
  letter-spacing: .11em;
}

.resource-dialog > header strong {
  color: #20252e;
  font-size: 18px;
  font-weight: 850;
}

.resource-dialog > header button {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 10px;
  background: #f3f4f6;
  color: #747b87;
  cursor: pointer;
  font-size: 20px;
}

.resource-dialog > label:not(.resource-upload-drop) {
  display: grid;
  gap: 7px;
}

.resource-dialog > label > span {
  color: #4f5662;
  font-size: 11px;
  font-weight: 800;
}

.resource-dialog input,
.resource-dialog select {
  min-width: 0;
  min-height: 42px;
  padding: 0 12px;
  border: 1px solid #dce0e6;
  border-radius: 11px;
  outline: none;
  background: #fff;
  color: #2f3540;
  font-size: 12px;
}

.resource-dialog input:focus,
.resource-dialog select:focus {
  border-color: rgba(237,75,32,.55);
  box-shadow: 0 0 0 3px rgba(237,75,32,.09);
}

.resource-dialog > p {
  margin: -6px 0 0;
  color: #8b929e;
  font-size: 10px;
  line-height: 1.65;
}

.resource-dialog > footer {
  display: flex;
  justify-content: flex-end;
  gap: 9px;
}

.resource-dialog > footer.is-spread {
  justify-content: space-between;
}

.resource-dialog > footer span {
  display: flex;
  gap: 9px;
}

.resource-dialog > footer button {
  min-height: 38px;
  padding: 0 15px;
  border: 1px solid #dce0e6;
  border-radius: 999px;
  background: #fff;
  color: #4d5561;
  cursor: pointer;
  font-size: 11px;
  font-weight: 820;
}

.resource-dialog > footer button.is-primary {
  border-color: var(--rc-accent);
  background: var(--rc-accent);
  color: #fff;
}

.resource-dialog > footer button.is-danger {
  border-color: #f3c5ba;
  background: #fff6f3;
  color: #c43d20;
}

.resource-dialog > footer button:disabled {
  cursor: not-allowed;
  opacity: .48;
}

.resource-upload-drop {
  min-height: 170px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 7px;
  padding: 22px;
  border: 1.5px dashed #d8dde5;
  border-radius: 16px;
  background: #fafbfc;
  cursor: pointer;
  text-align: center;
}

.resource-upload-drop:hover,
.resource-upload-drop.has-file {
  border-color: rgba(237,75,32,.45);
  background: #fff8f4;
}

.resource-upload-drop input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.resource-upload-drop > span {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 15px;
  background: #fff0e8;
  color: var(--rc-accent);
  font-size: 14px;
  font-weight: 900;
}

.resource-upload-drop strong {
  color: #333944;
  font-size: 13px;
}

.resource-upload-drop small {
  color: #8d949f;
  font-size: 10px;
}

.resource-upload-progress {
  position: relative;
  height: 7px;
  overflow: visible;
  border-radius: 999px;
  background: #eceef2;
}

.resource-upload-progress > span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ef4c23, #ff8a4c);
  transition: width 180ms ease;
}

.resource-upload-progress strong {
  position: absolute;
  right: 0;
  top: 10px;
  color: #777e8a;
  font-size: 9px;
}

@media (max-width: 1180px) {
  .resource-center__window {
    grid-template-columns: minmax(480px, 1fr) minmax(330px, 42%);
  }

  .resource-file-table__head,
  .resource-file-row {
    grid-template-columns: minmax(220px, 1fr) 92px 128px;
  }

  .resource-file-table__head span:nth-child(2),
  .resource-file-row__size {
    display: none;
  }
}

@media (max-width: 900px) {
  .resource-center__window {
    position: relative;
    display: block;
    min-height: 650px;
  }

  .resource-browser {
    min-height: 650px;
    border-right: 0;
  }

  .resource-preview {
    position: absolute;
    inset: 0;
    z-index: 4;
    visibility: hidden;
    opacity: 0;
    transform: translateX(24px);
    pointer-events: none;
    transition: opacity 180ms ease, transform 180ms cubic-bezier(.2,.8,.2,1), visibility 180ms;
  }

  .resource-preview.is-open {
    visibility: visible;
    opacity: 1;
    transform: translateX(0);
    pointer-events: auto;
  }

  .resource-preview__mobile-close {
    display: inline-flex !important;
    width: 30px;
    justify-content: center;
    font-size: 17px !important;
  }
}

@media (max-width: 680px) {
  .resource-center__header {
    align-items: stretch;
    flex-direction: column;
    gap: 14px;
  }

  .resource-center__actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }

  .resource-browser__toolbar {
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 10px 12px;
  }

  .resource-browser__content {
    padding: 14px 12px 20px;
  }

  .resource-folder-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .resource-file-table__head {
    display: none;
  }

  .resource-file-row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    min-height: 72px;
    padding: 8px 10px;
  }

  .resource-file-row__size,
  .resource-file-row__date {
    display: none;
  }

  .resource-section-heading {
    align-items: start;
  }

  .resource-section-heading small {
    max-width: 130px;
    text-align: right;
  }

  .resource-dialog > footer.is-spread {
    align-items: stretch;
    flex-direction: column-reverse;
  }

  .resource-dialog > footer.is-spread > button,
  .resource-dialog > footer.is-spread > span,
  .resource-dialog > footer.is-spread > span button {
    flex: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .rc-button,
  .resource-preview,
  .resource-file-row,
  .resource-upload-progress > span {
    transition-duration: 1ms;
  }

  .resource-quiet-loading__dot,
  .rc-icon-btn svg.is-spin {
    animation: none !important;
  }
}
</style>
