<template>
  <Transition name="role-banner">
    <div v-if="visible" class="role-switch-banner">
      已切换到 {{ info.icon }} {{ info.label }}
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import { roleConfig } from '../roleConfig'

const STORAGE_KEY = 'chat-role-toast-seen'
const chatStore = useChatStore()
const visible = ref(false)
let hideTimer: ReturnType<typeof setTimeout> | null = null

const info = computed(() => roleConfig[chatStore.activeRole])

watch(() => chatStore.activeRole, () => {
  if (sessionStorage.getItem(STORAGE_KEY)) return
  sessionStorage.setItem(STORAGE_KEY, '1')
  visible.value = true
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = setTimeout(() => { visible.value = false }, 3200)
})
</script>

<style scoped>
.role-switch-banner {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  background: var(--chat-accent-soft);
  border: 1px solid var(--chat-accent-border);
  color: var(--chat-accent-text);
  box-shadow: 0 4px 12px rgba(0,0,0,.08);
}
.role-banner-enter-active, .role-banner-leave-active { transition: opacity .2s ease; }
.role-banner-enter-from, .role-banner-leave-to { opacity: 0; }
</style>
