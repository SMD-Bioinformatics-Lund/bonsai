export class API { 
    constructor(private apiUrl: string) {}

    private async request<T>(endpoint: string, options?: RequestInit): Promise<T> { 
        const response = await fetch(`${this.apiUrl}${endpoint}`, options);
        if (!response.ok) throw new Error(`API error: ${response.status}`);
            return await response.json();
    }

    async checkJobStatus(jobId: string) {
        return this.request<JobStatus>(`/job/status/${jobId}`);
    }

    async clusterSamples(method: typingMethod, data: ApiClusterInput) {
        return this.request<{ id: string, task: string }>(`/cluster/${method}`);

    }
}
