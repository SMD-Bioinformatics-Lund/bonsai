import { ApiService, GroupApi } from "../../core/api";
import createApiWithAuth from "../../core/api/factory";

export type GroupViewApi = ApiService & {
  getGroup: (groupId: string) => Promise<any>;
  getGroups: () => Promise<any>;
  addSamplesToGroup: (groupId: string, sampleIds: string[]) => Promise<void>;
  removeSamplesFromGroup: (groupId: string, sampleIds: string[]) => Promise<void>;
};

export function createGroupViewApi(
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
): GroupViewApi {
  const { api, http } = createApiWithAuth(bonsaiApiUrl, accessToken, refreshToken);
  const apiTyped = api as GroupViewApi;
  const groupApi = new GroupApi(http);
  apiTyped.getGroup = groupApi.getGroup.bind(groupApi);
  apiTyped.getGroups = groupApi.getGroups.bind(groupApi);
  apiTyped.addSamplesToGroup = groupApi.addSamples.bind(groupApi);
  apiTyped.removeSamplesFromGroup = groupApi.removeSamples.bind(groupApi);

  return apiTyped;
}
