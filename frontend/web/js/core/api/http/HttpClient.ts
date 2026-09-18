import { ApiError } from "./ApiError";
import { AuthService } from "./AuthService";

export class HttpClient {
  constructor(
    private apiUrl: string,
    private authService: AuthService,
  ) {}

  request = async <T>(endpoint: string, options: RequestInit = {}, retry = true): Promise<T> => {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...this.authService.getAuthHeader(),
      ...options.headers,
    };

    const response = await fetch(`${this.apiUrl}${endpoint}`, {
      ...options,
      headers,
      signal: options.signal,
    });

    if (response.status === 401 && retry) {
      await this.authService.refreshAuthToken();
      return this.request<T>(endpoint, options, false);
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError(response.status, errorText || `Http error: ${response.status}`);
    }

    return await response.json();
  };
}