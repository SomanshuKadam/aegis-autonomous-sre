export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const response = await fetch(`/api/v1${path}`, { ...init, signal: init?.signal ?? controller.signal });
  if (!response.ok) throw new Error(`API request failed: ${response.status}`);
  return response.json() as Promise<T>;
}
