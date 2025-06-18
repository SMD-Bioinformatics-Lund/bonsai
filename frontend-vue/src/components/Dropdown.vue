<script setup lang="ts">
import { ref } from 'vue';

const isOpen = ref(false)

function toggle() {
  isOpen.value =! isOpen.value;
}

function onClickOutside(event: MouseEvent) {
  if (!(event.target as HTMLElement).closest('.dropdown')) close();
}
</script>

<template>
  <div class="dropdown" @click.outside="onClickOutside">
    <button class="dropdown-toggle" type="button" @click="toggle">
      <slot name="button">Dropdown</slot>
    </button>
    <div class="dropdown-menu" v-show="isOpen">
      <slot>
        <!-- Default content-->
        <ul>
          <li>Default item 1</li>
          <li>Default item 2</li>
        </ul>
      </slot>
    </div>
  </div>
</template>

<style scoped>
.dropdown {
  position: relative;
  display: inline-block
}

.dropdown-menu {
  position: absolute;
  min-width: 10rem;
  z-index: 1000;
}
</style>