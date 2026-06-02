import { ApiService, AuthService, HttpClient } from "./index";

export function createApiWithAuth(
  bonsaiApiUrl: string,
  accessToken?: string,
  refreshToken?: string,
) {
  const auth = new AuthService(bonsaiApiUrl);
  if (accessToken || refreshToken) {
    auth.setTokens(accessToken || "", refreshToken || "");
  }
  const http = new HttpClient(bonsaiApiUrl, auth);
  const api = new ApiService(http);

  return { auth, http, api };
}

export default createApiWithAuth;
