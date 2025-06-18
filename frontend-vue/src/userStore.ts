import { reactive } from 'vue'
import type { ApiUserInfo } from './types'
import type { ApiService, AuthService } from './api-service';

export const userStore = reactive({
  user: null as ApiUserInfo | null,
  isAuthenticated: false,

  async login(username: string, password: string, apiService: ApiService, authService: AuthService) {
    try {
      const tokens = await apiService.login(username, password)
      authService.setTokens(tokens.access_token, tokens.access_token)
      const user = await apiService.getUserInfo()
      this.user = user
      this.isAuthenticated = true
    } catch (error) {
      console.error("Login failed", error);
      throw new Error("Login failed")
    }
  },

  logout(authService: AuthService) {
    authService.clearTokens();
    this.user = null;
    this.isAuthenticated = false;
  }
})
