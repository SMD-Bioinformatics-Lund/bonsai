export interface PaginatedResponse<T> {
  data: T[];
  records_total: number;
  records_filtered: number;
}