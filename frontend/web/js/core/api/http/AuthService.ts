export class AuthService {
  private authToken: string | null = localStorage.getItem("authToken");
  private refreshToken: string | null = localStorage.getItem("refreshToken");
  private isRefreshing = false;

  constructor(private apiUrl: string) {}

  setTokens = (accessToken: string, refreshToken: string) => {
    this.authToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem("authToken", accessToken);
    localStorage.setItem("refreshToken", refreshToken);
  };

  clearTokens = () => {
    this.authToken = null;
    this.refreshToken = null;
    localStorage.removeItem("authToken");
    localStorage.removeItem("refreshToken");
  };

  isAuthenticated = (): boolean => {
    if (!this.authToken) return false;
    try {
      const payload = JSON.parse(atob(this.authToken.split(".")[1]));
      return payload.exp > Math.floor(Date.now() / 1000);
    } catch {
      return false;
    }
  };

  refreshAuthToken = async (): Promise<void> => {
    if (!this.refreshToken) throw new Error("No refresh token available");
    if (this.isRefreshing) return;

    this.isRefreshing = true;
    try {
      const response = await fetch(`${this.apiUrl}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken: this.refreshToken }),
      });

      if (!response.ok) throw new Error("Failed to refresh token");
      const data = await response.json();
      this.setTokens(data.accessToken, data.refreshToken);
    } finally {
      this.isRefreshing = false;
    }
  };

  getAuthHeader = (): HeadersInit => {
    return this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {};
  };
}