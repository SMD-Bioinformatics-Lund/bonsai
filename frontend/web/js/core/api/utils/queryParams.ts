function objectToQueryParams(query: Record<string, any>): string {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((v) => params.append(key, String(v)));
    } else if (value !== undefined && value !== null) {
      params.append(key, String(value));
    }
  });
  return params.toString();
}