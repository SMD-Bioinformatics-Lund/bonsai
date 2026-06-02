import { ApiService, GroupApi } from "../../core/api";
import createApiWithAuth from "../../core/api/factory";

export type SampleViewApi = ApiService & {
  getGroup: (groupId: string) => Promise<any>;
};

export function createSampleViewApi(
  bonsaiApiUrl: string,
  accessToken: string,
  refreshToken: string,
): SampleViewApi {
  const { api, http } = createApiWithAuth(bonsaiApiUrl, accessToken, refreshToken);
  const apiTyped = api as SampleViewApi;
  const groupApi = new GroupApi(http);

  apiTyped.getGroup = groupApi.getGroup.bind(groupApi);

  return apiTyped;
}
