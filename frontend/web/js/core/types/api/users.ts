export interface ApiUserInfo {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  disabled: boolean;
  roles: string[];
  authentication_method: string;
}
