import { HttpClient } from "../http/HttpClient";
import { ApiSummaryManifestResponse } from "core/types";

export class SampleApi {
  constructor(private http: HttpClient) {}

  getSummaryManifest(): Promise<ApiSummaryManifestResponse> {
    return this.http.request<ApiSummaryManifestResponse>(`/samples/summary/manifest`);
  }
}