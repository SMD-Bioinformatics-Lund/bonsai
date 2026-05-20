import { HttpClient } from "../http/HttpClient";
import { GroupInfo, ApiGroupInfoResponse, InputCoreGroupInfo } from "../../types";

export class GroupApi {
  constructor(private http: HttpClient) {}

  createGroup(data: InputCoreGroupInfo): Promise<string> {
    return Promise.resolve("mock-group-id");
  }

  updateGroup(groupId: string, data: InputCoreGroupInfo): Promise<void> {
    return Promise.resolve();
  }

  updateAllowedColumns(groupId: string, columnIds: string[]): Promise<void> {
    return Promise.resolve();
  }

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