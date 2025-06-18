<script setup lang="ts">
import { getCurrentInstance } from 'vue';
import { BsBasket3, BsPerson } from 'vue-icons-plus/bs';
import { AuthService } from '../api-service.ts';
import { userStore } from '../userStore';
import Dropdown from './Dropdown.vue';

const { proxy } = getCurrentInstance();

function logout() {
  userStore.logout(proxy.$authService as AuthService)
}
</script>

<template>
  <nav class="navbar">
    <div class="container">
      <RouterLink to="/" class="navbar-brand">
        <div class="logo">
          <img class="logo-img" width="40" src="@/assets/bonsai_logo_sm.png" alt="Logo">
        </div>
      </RouterLink>
      <div>
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/">Samples</RouterLink>
        <RouterLink to="/">Groups</RouterLink>
        <RouterLink to="/">Locations</RouterLink>
        <RouterLink to="/about">About</RouterLink>
      </div>
      <div v-if="userStore.isAuthenticated">
        <!-- When logged in -->
        <Dropdown>
          <template #button><BsPerson/></template>
          <ul>
            <li><a @click="logout">Logout</a></li>
          </ul>
        </Dropdown>
        <BsBasket3 />
      </div>
      <div v-else>
        <!-- When logged out -->
        <RouterLink class="login" to="/login">
          <BsPerson size="2rem"/>
          <div class="login-message">
            <strong>Log in</strong>
          </div>
        </RouterLink>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  background-color: var(--green-soft);
  padding: 0.75rem 0;
  position: sticky;
  top: 0;
  width: 100%;
  z-index: 1000;
}

.container {
  justify-content: space-between;
}

.navbar-brand {
  display: flex;
  align-items: center;
  text-decoration: none;
  font-size: 1.5rem;
}

.logo {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  padding: 0.3rem;
  overflow: hidden;
  margin-right: 0.5rem;
  background-color: var(--brown-soft);
}

.logo img {
  width: 100%;
  height: auto;
}

nav a.router-link-exact-active {
  color: var(--color-text);
}

nav a.router-link-exact-active:hover {
  color: var(--black);
}

nav a {
  display: inline-block;
  padding: 0 1rem;
  text-decoration: none;
  font-size: 1.2rem;
  color: var(--black-soft);
}

nav a:first-of-type {
  border: 0;
}

.login {
  display: flex;
  flex-direction: row;
  align-items: center;
  margin-right: 2rem;
}

.login-message {
  display: flex;
  flex-direction: column;
  padding-left: 0.5rem;
}

stong {
  font-weight: bolder;
}
</style>