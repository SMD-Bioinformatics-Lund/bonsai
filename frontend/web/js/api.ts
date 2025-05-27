import {
  ApiJobStatus,
  ApiGetSamplesDetailsInput,
  ApiSampleDetailsResponse,
  ApiClusterInput,
  ApiJobSubmission,
  ApiFindSimilarInput,
  GroupInfo,
} from "./types";
import { JobStatusEnum, TypingMethod } from "./constants";

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

export class HttpClient {
  constructor(
    private apiUrl: string,
    private authService: AuthService,
  ) {}

  request = async <T>(
    endpoint: string,
    options: RequestInit = {},
    retry = true,
  ): Promise<T> => {
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
  };
}

function objectToQueryParams(query: Record<string, any>): string {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((v) => params.append(key, String(v)));
    } else if (value !== undefined && value !== null) {
      params.append(key, String(value));
    }
  });
  return params.toString();
}

export class ApiService {
  constructor(private http: HttpClient) {}

  getSamplesDetails = async (query: ApiGetSamplesDetailsInput) => {
    const url = `/samples/?${objectToQueryParams(query)}`;
    return this.http.request<ApiSampleDetailsResponse>(url);
  };

  deleteSamples = async (sampleIds: string[]) => {
    if (sampleIds.length === 0) {
      throw new Error("No sample IDs provided for deletion");
    }
    try {
      return await this.http.request<void>('/samples', {
        method: "DELETE",
        body: JSON.stringify(sampleIds),
      });
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  };

  checkJobStatus = async (jobId: string) => {
    try {
      return await this.http.request<ApiJobStatus>(`/job/status/${jobId}`);
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  };

  clusterSamples = async (method: TypingMethod, params: ApiClusterInput) => {
    return this.http.request<ApiJobSubmission>(`/cluster/${method}`, {
      method: "POST",
      body: JSON.stringify(params),
    });
  };

  findSimilarSamples = async (
    sampleId: string,
    params: ApiFindSimilarInput,
  ) => {
    return this.http.request<ApiJobSubmission>(`/samples/${sampleId}/similar`, {
      method: "POST",
      body: JSON.stringify(params),
    });
  };

  getGroup = async (groupId: string) => {
    return this.http.request<GroupInfo>(`/groups/${groupId}`);
  };

  addSampleToGroup = async (groupId: string, sampleId: string) => {
    return this.http.request<void>(`/groups/${groupId}/samples?${objectToQueryParams({sample_id: sampleId})}`, {
      method: "PUT",
    });
  };

  private handleError = (error: unknown) => {
    if (error instanceof ApiError) {
      console.error(`API Error [${error.status}]: ${error.message}`);
    } else {
      console.error("Unexpected error:", error);
    }
  };
}

export async function pollJob<T extends ApiJobStatus>(
  checkJobFn: () => Promise<T>,
  waitTime: number,
): Promise<T> {
  /* Generic polling function that  */
  let result = await checkJobFn();
  while (validateJobStatus(result)) {
    await wait(waitTime);
    result = await checkJobFn();
  }
  return result;
}

function wait(ms: number = 2000) {
  // wait between fetch jobs
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function validateJobStatus(job: ApiJobStatus): boolean {
  // check job status
  // returns true if run is invalid
  let isValid = false;
  if (job.status === JobStatusEnum.FINISHED) {
    // if job has finished report result
    isValid = true;
  } else if (job.status === JobStatusEnum.FAILED) {
    // if job failed raise error
    throw new Error(`Job failed: ${job.result}`);
    isValid = true;
  }
  console.log(`Job status: ${job.status}; is valid ${isValid}`);
  return !isValid;
}
