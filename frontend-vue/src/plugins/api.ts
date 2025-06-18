import type { App } from 'vue';
import { AuthService, HttpClient, ApiService } from '@/api-service';

export default {
  install(app: App) {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001'; // get API URL from environment variables
    const authService = new AuthService(apiUrl);
    const httpClient = new HttpClient(apiUrl, authService);
    const apiService = new ApiService(httpClient);

    app.config.globalProperties.$apiService = apiService;
    app.config.globalProperties.$authService = authService;
  }
};