<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import Navbar from './components/Navbar.vue'
</script>

<template>
  <header>
    <div class="wrapper">
      <Navbar/>
    </div>
  </header>
  <RouterView />
</template>

<style scoped>
</style>
