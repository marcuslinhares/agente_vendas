const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4000/api/v1';

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiClient<T = any>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  let token: string | null = null;
  if (typeof window !== 'undefined') {
    token = localStorage.getItem('token');
  }

  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ message: res.statusText }));
    throw new ApiError(body.message || `HTTP ${res.status}`, res.status);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
