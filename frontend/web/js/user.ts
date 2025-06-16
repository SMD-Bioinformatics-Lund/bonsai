import { ApiUserInfo } from "./types";

/* User information container. */
export class User {
  private id: string;
  private roles: string[];
  public username: string;
  public fullName: string;
  public email: string;

  constructor(userData: ApiUserInfo) {
    this.id = userData.id;
    this.username = userData.username;
    this.email = userData.email;
    this.fullName = `${userData.first_name} ${userData.last_name}`;
    this.roles = userData.roles || [];
  }

  get isAdmin(): boolean {
    return this.roles.includes("admin");
  }
}
