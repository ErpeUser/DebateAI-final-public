export function createDesktopSession(fetcher: typeof fetch, enabled?: boolean): {
  getToken(): string;
  fetch(input: RequestInfo | URL, options?: RequestInit): Promise<Response>;
};
