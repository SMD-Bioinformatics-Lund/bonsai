import { HttpClient } from "../http/HttpClient";
import { GroupInfo, ApiGroupInfoResponse, InputCoreGroupInfo } from "../../types";

export class GroupApi {
  constructor(private http: HttpClient) {}

  createGroup(data: InputCoreGroupInfo): Promise<GroupInfo> {
    return this.http.request<GroupInfo>(`/groups/`, {
      method: 'POST', 
      body: JSON.stringify(data)
    });
  }

  updateGroup(groupId: string, data: InputCoreGroupInfo): Promise<GroupInfo> {
    return this.http.request<GroupInfo>(`/groups/${groupId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  updateAllowedColumns(groupId: string, columnIds: string[]): Promise<GroupInfo> {
    return this.http.request<GroupInfo>(`/groups/${groupId}/allowed_columns`, {
      method: 'PUT',
      body: JSON.stringify({ column_ids: columnIds })
    });
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