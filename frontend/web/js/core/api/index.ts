import {
  ApiJobStatus,
  ApiGetSamplesDetailsInput,
  ApiSampleDetailsResponse,
  ApiClusterInput,
  ApiJobSubmission,
  ApiFindSimilarInput,
  ApiUserInfo,
  ApiSampleQcStatus,
  MembershipEdges,
} from "../types";
import { TypingMethod } from "../types/enums";
import { ApiError } from "./http/ApiError";
import { HttpClient } from "./http/HttpClient";
import { objectToQueryParams } from "./utils/queryParams";



export class ApiService {
  constructor(private http: HttpClient) {}

  getUserInfo = async () => {
    const url = `/users/me`;
    return this.http.request<ApiUserInfo>(url);
  };

  getSamplesDetails = async (query: ApiGetSamplesDetailsInput) => {
    return this.http.request<ApiSampleDetailsResponse>(`/samples/summary`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(query),
    });
  };

  deleteSamples = async (sampleIds: string[]) => {
    if (sampleIds.length === 0) {
      throw new Error("No sample IDs provided for deletion");
    }
    try {
      return await this.http.request<void>(`/samples/`, {
        method: "DELETE",
        body: JSON.stringify(sampleIds),
      });
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  };

  setSampleQc = async (sampleId: string, params: ApiSampleQcStatus) => {
    const url = `/samples/${sampleId}/qc_status`;
    return this.http.request<ApiSampleQcStatus>(url, {
      method: "PUT",
      body: JSON.stringify(params),
    });
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

  findSimilarSamples = async (sampleId: string, params: ApiFindSimilarInput) => {
    return this.http.request<ApiJobSubmission>(`/samples/${sampleId}/similar`, {
      method: "POST",
      body: JSON.stringify(params),
    });
  };

  getMembershipByGroups = async (groupIds: string[], signal?: AbortSignal) => {
    return this.http.request<MembershipEdges>(
      `/memberships?${objectToQueryParams({ g: groupIds})}`,
      {
        method: "GET",
        signal,
      },
    );
  };

  getMembershipsBySamples = async (sampleIds: string[], signal?: AbortSignal) => {
    return this.http.request<MembershipEdges>(
      `/memberships?${objectToQueryParams({ s: sampleIds })}`,
      {
        method: "GET",
        signal,
      },
    );
  };

  private handleError = (error: unknown) => {
    if (error instanceof ApiError) {
      console.error(`API Error [${error.status}]: ${error.message}`);
    } else {
      console.error("Unexpected error:", error);
    }
  };
}

/**
 * Pauses execution for a specified duration.
 *
 * This function is primarily used in the polling mechanism to introduce
 * a delay between successive API calls. It ensures that the polling
 * does not overwhelm the server with rapid requests.
 *
 * @param ms - The duration to wait in milliseconds. Defaults to 2000ms.
 * @returns A promise that resolves after the specified duration.
 */
export function wait(ms: number = 2000) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export * from "./http/ApiError";
export * from "./http/AuthService";
export * from "./http/HttpClient";

export * from "./services/groups";
export * from "./services/samples";
//export * from "./services/jobs";
//export * from "./services/users";
//export * from "./services/memberships";

export * from "./polling/pollJob";
