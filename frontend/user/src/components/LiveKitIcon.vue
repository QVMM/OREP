<template>
  <svg
    class="lk-icon"
    :class="`lk-icon-${name}`"
    :viewBox="viewBox"
    aria-hidden="true"
    focusable="false"
  >
    <path v-if="name === 'mic'" fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M2.975 8.002a.5.5 0 0 1 .547.449 4.5 4.5 0 0 0 8.956 0 .5.5 0 1 1 .995.098A5.502 5.502 0 0 1 8.5 13.478V15h2a.5.5 0 0 1 0 1h-5a.5.5 0 0 1 0-1h2v-1.522a5.502 5.502 0 0 1-4.973-4.929.5.5 0 0 1 .448-.547z" />
    <path v-if="name === 'mic'" fill="currentColor" d="M5 3a3 3 0 1 1 6 0v5a3 3 0 0 1-6 0z" />

    <path v-else-if="name === 'mic-off'" fill="currentColor" d="M12.227 11.52a5.477 5.477 0 0 0 1.246-2.97.5.5 0 0 0-.995-.1 4.478 4.478 0 0 1-.962 2.359l-1.07-1.07C10.794 9.247 11 8.647 11 8V3a3 3 0 0 0-6 0v1.293L1.354.646a.5.5 0 1 0-.708.708l14 14a.5.5 0 0 0 .708-.708zM8 12.5c.683 0 1.33-.152 1.911-.425l.743.743c-.649.359-1.378.59-2.154.66V15h2a.5.5 0 0 1 0 1h-5a.5.5 0 0 1 0-1h2v-1.522a5.502 5.502 0 0 1-4.973-4.929.5.5 0 0 1 .995-.098A4.5 4.5 0 0 0 8 12.5z" />
    <path v-if="name === 'mic-off'" fill="currentColor" d="M8.743 10.907 5 7.164V8a3 3 0 0 0 3.743 2.907z" />

    <path v-else-if="name === 'camera'" fill="currentColor" d="M0 4.5A1.5 1.5 0 0 1 1.5 3h8A1.5 1.5 0 0 1 11 4.5v7A1.5 1.5 0 0 1 9.5 13h-8A1.5 1.5 0 0 1 0 11.5zM15.2 3.6l-2.8 2.1a1 1 0 0 0-.4.8v3a1 1 0 0 0 .4.8l2.8 2.1a.5.5 0 0 0 .8-.4V4a.5.5 0 0 0-.8-.4z" />

    <g v-else-if="name === 'camera-off'" fill="currentColor">
      <path d="M0 4.5A1.5 1.5 0 0 1 1.5 3h1.086l10 10H1.5A1.5 1.5 0 0 1 0 11.5zM4.414 3H9.5A1.5 1.5 0 0 1 11 4.5v5.086zM15.2 3.6l-2.8 2.1a1 1 0 0 0-.4.8v1.172l3.18 3.18A.5.5 0 0 0 16 10.5V4a.5.5 0 0 0-.8-.4z" />
      <path d="M.646.646a.5.5 0 0 1 .708 0l14 14a.5.5 0 0 1-.708.708l-14-14a.5.5 0 0 1 0-.708z" />
    </g>

    <path v-else-if="name === 'screen'" fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M0 2.75A2.75 2.75 0 0 1 2.75 0h14.5A2.75 2.75 0 0 1 20 2.75v10.5A2.75 2.75 0 0 1 17.25 16H2.75A2.75 2.75 0 0 1 0 13.25V2.75ZM2.75 1.5c-.69 0-1.25.56-1.25 1.25v10.5c0 .69.56 1.25 1.25 1.25h14.5c.69 0 1.25-.56 1.25-1.25V2.75c0-.69-.56-1.25-1.25-1.25H2.75Z" />
    <path v-if="name === 'screen'" fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M9.47 4.22a.75.75 0 0 1 1.06 0l2.25 2.25a.75.75 0 0 1-1.06 1.06l-.97-.97v4.69a.75.75 0 0 1-1.5 0V6.56l-.97.97a.75.75 0 0 1-1.06-1.06l2.25-2.25Z" />

    <g v-else-if="name === 'screen-stop'" fill="currentColor">
      <path d="M7.28 4.22a.75.75 0 0 0-1.06 1.06L8.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L10 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L11.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L10 6.94z" />
      <path fill-rule="evenodd" clip-rule="evenodd" d="M2.75 0A2.75 2.75 0 0 0 0 2.75v10.5A2.75 2.75 0 0 0 2.75 16h14.5A2.75 2.75 0 0 0 20 13.25V2.75A2.75 2.75 0 0 0 17.25 0zM1.5 2.75c0-.69.56-1.25 1.25-1.25h14.5c.69 0 1.25.56 1.25 1.25v10.5c0 .69-.56 1.25-1.25 1.25H2.75c-.69 0-1.25-.56-1.25-1.25z" />
    </g>

    <path v-else-if="name === 'chat'" fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M0 2.75A2.75 2.75 0 0 1 2.75 0h10.5A2.75 2.75 0 0 1 16 2.75v13.594a.75.75 0 0 1-1.234.572l-3.691-3.12a1.25 1.25 0 0 0-.807-.296H2.75A2.75 2.75 0 0 1 0 10.75v-8ZM2.75 1.5c-.69 0-1.25.56-1.25 1.25v8c0 .69.56 1.25 1.25 1.25h7.518c.65 0 1.279.23 1.775.65l2.457 2.077V2.75c0-.69-.56-1.25-1.25-1.25H2.75Z" />
    <path v-if="name === 'chat'" fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M3 4.5a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5Zm0 2a.5.5 0 0 1 .5-.5h9a.5.5 0 0 1 0 1h-9a.5.5 0 0 1-.5-.5Zm0 2a.5.5 0 0 1 .5-.5h5a.5.5 0 0 1 0 1h-5a.5.5 0 0 1-.5-.5Z" />

    <path v-else-if="name === 'leave'" fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M2 2.75A2.75 2.75 0 0 1 4.75 0h6.5A2.75 2.75 0 0 1 14 2.75v10.5A2.75 2.75 0 0 1 11.25 16h-6.5A2.75 2.75 0 0 1 2 13.25v-.5a.75.75 0 0 1 1.5 0v.5c0 .69.56 1.25 1.25 1.25h6.5c.69 0 1.25-.56 1.25-1.25V2.75c0-.69-.56-1.25-1.25-1.25h-6.5c-.69 0-1.25.56-1.25 1.25v.5a.75.75 0 0 1-1.5 0v-.5Z" />
    <path v-if="name === 'leave'" fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="M8.78 7.47a.75.75 0 0 1 0 1.06l-2.25 2.25a.75.75 0 1 1-1.06-1.06l.97-.97H1.75a.75.75 0 0 1 0-1.5h4.69l-.97-.97a.75.75 0 0 1 1.06-1.06l2.25 2.25Z" />

    <g v-else fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
      <path v-if="name === 'settings'" d="M12 8.2a3.8 3.8 0 1 0 0 7.6 3.8 3.8 0 0 0 0-7.6Z" />
      <path v-if="name === 'settings'" d="M19.4 13.5v-3l-2.1-.7a6.3 6.3 0 0 0-.7-1.7l1-2-2.1-2.1-2 .98a6.2 6.2 0 0 0-1.8-.72L11 2H8l-.7 2.1a6.2 6.2 0 0 0-1.7.72l-2-.98-2.1 2.1 1 2a6.3 6.3 0 0 0-.7 1.7L0 10.5v3l2.1.7a6.3 6.3 0 0 0 .7 1.7l-1 2 2.1 2.1 2-.98a6.2 6.2 0 0 0 1.8.72L8 22h3l.7-2.1a6.2 6.2 0 0 0 1.7-.72l2 .98 2.1-2.1-1-2a6.3 6.3 0 0 0 .7-1.7Z" transform="translate(2 0)" />
      <path v-if="name === 'fullscreen'" d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" />
      <path v-if="name === 'record'" fill="currentColor" stroke="none" d="M12 6.25a5.75 5.75 0 1 0 0 11.5 5.75 5.75 0 0 0 0-11.5Z" />
      <path v-if="name === 'record-stop'" fill="currentColor" stroke="none" d="M8.25 8.25h7.5v7.5h-7.5z" />
      <path v-if="name === 'layout'" d="M4 5h16v11H4zM8 20h8M12 16v4" />
      <path v-if="name === 'score'" d="M5 18 15.8 7.2l3 3L8 21H5zM14 9l3 3M16.6 4.4l3 3" />
      <path v-if="name === 'issues'" d="M8 4h8M9 2h6M7 6h10v15H7zM10 10h4M10 14h4M10 18h3" />
      <path v-if="name === 'grid'" d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" />
    </g>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true }
})

const viewBox = computed(() => {
  if (props.name === 'screen' || props.name === 'screen-stop') return '0 0 20 16'
  if (props.name === 'chat') return '0 0 16 18'
  if (props.name === 'mic' || props.name === 'mic-off' || props.name === 'camera' || props.name === 'camera-off' || props.name === 'leave') return '0 0 16 16'
  return '0 0 24 24'
})
</script>

<style scoped>
.lk-icon {
  width: 18px;
  height: 18px;
  display: block;
}

.lk-icon-screen,
.lk-icon-screen-stop {
  width: 20px;
}
</style>
