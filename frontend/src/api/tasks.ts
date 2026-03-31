const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export type TaskStatus = 'todo' | 'in-progress' | 'done';
export type TaskPriority = 'low' | 'medium' | 'high';

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  created_at: string;
  updated_at: string;
}

export interface TaskStats {
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface TaskCreate {
  title: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  status?: TaskStatus;
  priority?: TaskPriority;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body?.detail ?? body?.message ?? message;
    } catch {
      message = await res.text().catch(() => message);
    }
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listTasks: (status?: TaskStatus | null, priority?: TaskPriority | null) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (priority) params.set('priority', priority);
    const qs = params.toString();
    return request<Task[]>(`/api/tasks/${qs ? `?${qs}` : ''}`);
  },
  getTask: (id: string) => request<Task>(`/api/tasks/${id}`),
  createTask: (data: TaskCreate) =>
    request<Task>('/api/tasks/', { method: 'POST', body: JSON.stringify(data) }),
  updateTask: (id: string, data: TaskUpdate) =>
    request<Task>(`/api/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTask: (id: string) => request<void>(`/api/tasks/${id}`, { method: 'DELETE' }),
  completeTask: (id: string) =>
    request<Task>(`/api/tasks/${id}/complete`, { method: 'POST' }),
  getStats: () => request<TaskStats>('/api/tasks/stats'),
};
