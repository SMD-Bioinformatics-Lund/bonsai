import { HttpClient } from "../http/HttpClient";
import { GroupInfo, ApiGroupInfoResponse } from "core/types";

export class GroupApi {
  constructor(private http: HttpClient) {}

  getGroup(groupId: string) {
    return this.http.request<GroupInfo>(`/groups/${groupId}`);
  }

  getGroups() {
    return this.http.request<ApiGroupInfoResponse>(`/groups/`);
  }

  addSamples(groupId: string, sampleIds: string[]) {
    return this.http.request<void>(
      `/groups/${groupId}/samples?${objectToQueryParams({ s: sampleIds })}`,
      { method: "PUT" },
    );
  }

  removeSamples(groupId: string, sampleIds: string[]) {
    return this.http.request<void>(
      `/groups/${groupId}/samples?${objectToQueryParams({ s: sampleIds })}`,
      { method: "DELETE" },
    );
  }
}