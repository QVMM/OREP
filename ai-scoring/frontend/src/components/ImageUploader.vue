<template>
  <div class="image-uploader">
    <h3>图片上传</h3>
    <div
      class="upload-area"
      :class="{ dragging: isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <input
        type="file"
        ref="fileInput"
        accept="image/*"
        @change="handleFileSelect"
        style="display: none"
      />
      <div class="upload-hint" @click="triggerUpload">
        <span class="icon">+</span>
        <p>点击或拖拽图片到此处上传</p>
      </div>
    </div>
    <div v-if="previewUrl" class="preview">
      <img :src="previewUrl" alt="Preview" />
      <button class="remove-btn" @click="removeImage">移除</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const fileInput = ref(null)
const isDragging = ref(false)
const previewUrl = ref(props.modelValue)

function triggerUpload() {
  fileInput.value?.click()
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    processFile(file)
  }
}

function handleDrop(event) {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) {
    processFile(file)
  }
}

function processFile(file) {
  const reader = new FileReader()
  reader.onload = (e) => {
    previewUrl.value = e.target.result
    emit('update:modelValue', e.target.result)
  }
  reader.readAsDataURL(file)
}

function removeImage() {
  previewUrl.value = ''
  emit('update:modelValue', '')
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}
</script>

<style scoped>
.image-uploader {
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.3s, background 0.3s;
}

.upload-area.dragging {
  border-color: #42b983;
  background: #f0f9f4;
}

.upload-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.icon {
  font-size: 2rem;
  color: #999;
}

.preview {
  margin-top: 1rem;
  text-align: center;
}

.preview img {
  max-width: 100%;
  max-height: 200px;
  border-radius: 4px;
}

.remove-btn {
  margin-top: 0.5rem;
  padding: 0.25rem 1rem;
  background: #dc3545;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.remove-btn:hover {
  background: #c82333;
}
</style>
