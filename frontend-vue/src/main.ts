import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import apiPlugin from './plugins/api'

const app = createApp(App)

app.use(router)
app.use(apiPlugin)
app.mount('#app')
