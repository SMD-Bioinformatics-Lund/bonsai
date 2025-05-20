export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class AuthService {
  private authToken: string | null = localStorage.getItem("authToken");
  private refreshToken: string | null = localStorage.getItem("refreshToken");
  private isRefreshing = false;

  constructor(private apiUrl: string) {}

  setTokens(accessToken: string, refreshToken: string) {
    this.authToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem("authToken", accessToken);
    localStorage.setItem("refreshToken", refreshToken);
  }

  clearTokens() {
    this.authToken = null;
    this.refreshToken = null;
    localStorage.removeItem("authToken");
    localStorage.removeItem("refreshToken");
  }

  isAuthenticated(): boolean {
    if (!this.authToken) return false;
    try {
      const payload = JSON.parse(atob(this.authToken.split(".")[1]));
      const now = Math.floor(Date.now() / 1000);
      return payload.exp > now;
    } catch {
      return false;
    }
  }

  async refreshAuthToken(): Promise<void> {
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
  }

  getAuthHeader(): HeadersInit {
    return this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {};
  }
}

export class HttpClient {
  constructor(
    private apiUrl: string,
    private authService: AuthService,
  ) {}

  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    retry = true,
  ): Promise<T> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...this.authService.getAuthHeader(),
      ...options.headers,
    };

    const response = await fetch(`${this.apiUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (response.status === 401 && retry) {
      await this.authService.refreshAuthToken();
      return this.request<T>(endpoint, options, false);
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError(
        response.status,
        errorText || `Http error: ${response.status}`,
      );
    }
    return await response.json();
  }
}

export class ApiService {
  constructor(private http: HttpClient) {}

  async checkJobStatus(jobId: string) {
    try {
      return this.http.request<JobStatus>(`/job/status/${jobId}`);
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  }

  async clusterSamples(method: typingMethod, params: ApiClusterInput) {
    return this.http.request<ApiJobSubmission>(`/cluster/${method}`, {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async findSimilarSamples(sampleId: string, params: ApiFindSimilarInput) {
    return this.http.request<ApiJobSubmission>(`/samples/${sampleId}/similar`, {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async getGroup(groupId: string) {
    return this.http.request<GroupInfo>(`/groups/${groupId}`);
  }

  private handleError(error: unknown) {
    if (error instanceof ApiError) {
      console.error(`API Error [${error.status}]: ${error.message}`);
      // FIXME if error.status == 401, possible redirect to some flask page
    } else {
      console.error("Unexpected error:", error);
    }
  }
}
