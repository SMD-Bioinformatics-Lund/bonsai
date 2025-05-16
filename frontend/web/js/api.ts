export class AuthService {
    private authToken: string | null = localStorage.getItem('authToken');
    private refreshToken: string | null = localStorage.getItem('refreshToken');
    private isRefreshing = false;

    constructor(private apiUrl: string) {}

    setTokens(accessToken: string, refreshToken: string) {
        this.authToken = accessToken;
        this.refreshToken = refreshToken;
        localStorage.setItem('authToken', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
    }

    clearTokens() {
        this.authToken = null;
        this.refreshToken = null;
        localStorage.removeItem('authToken');
        localStorage.removeItem('refreshToken');
    }

    isAuthenticated(): boolean {
        if (!this.authToken) return false;
        try {
            const payload = JSON.parse(atob(this.authToken.split('.')[1]));
            const now = Math.floor(Date.now() / 1000);
            return payload.exp > now;
        } catch {
            return false;
        }
    }

    async refreshAuthToken(): Promise<void> {
        if (!this.refreshToken) throw new Error('No refresh token available');
        if (this.isRefreshing) return;

        this.isRefreshing = true;
        try {
            const response = await fetch(`${this.apiUrl}/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refreshToken: this.refreshToken }),
            });

            if (!response.ok) throw new Error('Failed to refresh token');
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
    constructor(private apiUrl: string, private authService: AuthService) {}

    async request<T>(endpoint: string, options: RequestInit = {}, retry = true): Promise<T> {
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
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

        if (!response.ok) throw new Error(`Http error: ${response.status}`);
        return await response.json();
    }
}


export class ApiService { 

    constructor(private http: HttpClient) {}

    async checkJobStatus(jobId: string) {
        return this.http.request<JobStatus>(`/job/status/${jobId}`);
    }

    async clusterSamples(method: typingMethod, data: ApiClusterInput) {
        return this.http.request<{ id: string, task: string }>(`/cluster/${method}`, {
            method: 'POST',
            body: JSON.stringify(data)
        });

    }

    async getGroup(groupId: string) {
        return this.http.request<GroupInfo>(`/groups/${groupId}`);
    }
}
