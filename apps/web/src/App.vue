<template>
  <RouterView />
  <Search />
  <Login />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import Search from './components/Search/index.vue'
import Login from './components/Login/index.vue'
import { provide, watch } from 'vue'
import { IS_SHOW_LOGIN } from './components/Login/type'
import { isShowLogin } from './components/Login/loginState'
provide(IS_SHOW_LOGIN, isShowLogin)
import { useSocket } from './hooks/useSocket'
import { useUserStore } from './stores/user'
import { useTracker } from './hooks/useTracker'
const tracker = useTracker()
const userStore = useUserStore()
const { connect, disconnect } = useSocket()
watch(() => userStore.user?.id, (newVal) => {
  if (newVal) {
    tracker.setUserId(newVal)
    void connect()
  } else {
    disconnect()
  }
}, { immediate: true })
</script>
