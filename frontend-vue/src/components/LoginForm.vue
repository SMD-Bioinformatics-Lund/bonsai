<script setup lang="ts">
import { ref, getCurrentInstance } from 'vue';
import { userStore } from '../userStore.ts';

const username = ref('');
const password = ref('');

const { proxy } = getCurrentInstance();

const handleSubmit = () => {
  userStore.login(username.value, password.value, proxy.$apiService, proxy.$authService)
  .then( () => {
    if ( userStore.isAuthenticated ) {
      console.log('Login worked!')
    } else {
      console.log('Not authenticated!')
    }
  });
};
</script>

<template>
  <form @submit.prevent="handleSubmit">
    <div class="row">
      <h1>Welcome! Log in</h1>
    </div>
    <div class="row">
      <input type="text" placeholder="User name" v-model="username" data-test-id="username-input" required>
    </div>
    <div class="row">
      <input type="password" placeholder="Password" v-model="password" data-test-id="password-input" required>
    </div>
    <div class="row">
      <button class="btn" type="submit" data-test-id="login-btn">Login</button>
    </div>
  </form>
</template>

<style scoped>
.conteiner {
  flex-direction: column;
}

.btn {
  font-size: 1rem;
  padding: 0.4rem 0.7rem;
  border-radius: 4%;
  border: none;
}

.btn:hover {
  box-shadow: 0 0.3rem 0.5rem 0 rgba(0,0,0,0.24);
}
</style>