export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
    if (message) {
      try {
        this.data = JSON.parse(message);
      } catch {
        /* leave as-is */
      }
    }
  }
}