<script setup lang="ts">
import LoginForm from '../components/LoginForm.vue'
</script>

<template>
  <main>
    <div class="container">
        <div class="login-card">
            <LoginForm />
        </div>
    </div>
  </main>
</template>

<style scoped>
html, body {
    overflow: hidden;
}

.container {
    justify-content: center;
}

.login-card {
    width: auto;
    justify-content: center;
    background-color: var(--color-background-mute);
    margin-top: 1rem;
    padding: 2rem;
}

.sidebar {
    height: 100%;
}

.login-gradient-upper {
    background-color: var(--green-soft);
    z-index: -2;
}

.login-gradient-lower {
    display: block;
    width: 700px;
    height: 30vh;
    position: absolute;
    bottom: -30px;
    left: -300px;
    transform: perspective(300px) rotateY(-45deg);
    background-color: var(--green);
}
</style>