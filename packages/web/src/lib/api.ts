// API Client with typed fetch wrapper

import { getApiBaseUrl } from '@/lib/api-base'

// ============================================================================
// Types
// ============================================================================

export interface ApiError {
  message: string
  code: string
  status: number
  details?: Record<string, unknown>
}

export interface ApiResponse<T> {
  data: T
  meta?: {
    total?: number
    page?: number
    limit?: number
  }
}

export interface PaginationParams {
  page?: number
  limit?: number
  [key: string]: string | number | boolean | undefined
}

// Organization types
export interface Organization {
  id: string
  name: string
  slug: string
  createdAt: string
  updatedAt: string
}

export interface CreateOrganizationInput {
  name: string
  slug?: string
}

export interface UpdateOrganizationInput {
  name?: string
  slug?: string
}

// Project types
export interface Project {
  id: string
  organizationId: string
  name: string
  slug: string
  description?: string
  repositoryUrl?: string
  status: 'active' | 'archived' | 'paused'
  createdAt: string
  updatedAt: string
}

export interface CreateProjectInput {
  organizationId?: string
  name: string
  slug?: string
  description?: string
  repositoryUrl?: string
}

export interface UpdateProjectInput {
  name?: string
  slug?: string
  description?: string
  repositoryUrl?: string
  status?: 'active' | 'archived' | 'paused'
}

// Task types
export type TaskStatus = 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'cancelled'
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface Task {
  id: string
  projectId: string
  title: string
  description?: string
  status: TaskStatus
  priority: TaskPriority
  assignedAgentId?: string
  parentTaskId?: string
  order: number
  estimatedTokens?: number
  actualTokens?: number
  createdAt: string
  updatedAt: string
  completedAt?: string
}

export interface CreateTaskInput {
  projectId: string
  title: string
  description?: string
  status?: TaskStatus
  priority?: TaskPriority
  parentTaskId?: string
  order?: number
  estimatedTokens?: number
}

export interface UpdateTaskInput {
  title?: string
  description?: string
  status?: TaskStatus
  priority?: TaskPriority
  assignedAgentId?: string | null
  parentTaskId?: string | null
  order?: number
  estimatedTokens?: number
  actualTokens?: number
}

// Agent types
export type AgentStatus = 'initializing' | 'idle' | 'busy' | 'error' | 'stopping' | 'stopped'
export type AgentType =
  | 'sisyphus'
  | 'oracle'
  | 'explore'
  | 'frontend'
  | 'implement'
  | 'fixer'
  | 'librarian'
  | 'document-writer'

export interface Agent {
  id: string
  projectId: string
  type: AgentType
  name: string
  status: AgentStatus
  currentTaskId?: string
  currentSessionId?: string
  model: string
  lastHeartbeat?: string
  createdAt: string
  updatedAt: string
}

export interface CreateAgentInput {
  projectId: string
  type: AgentType
  name: string
  model?: string
}

export interface UpdateAgentInput {
  name?: string
  status?: AgentStatus
  currentTaskId?: string | null
  currentSessionId?: string | null
  model?: string
}

// Session types
export type SessionStatus = 'active' | 'completed' | 'cancelled' | 'error'

export interface Session {
  id: string
  projectId: string
  agentId: string
  taskId?: string
  status: SessionStatus
  startedAt: string
  endedAt?: string
  tokensUsed: number
  messageCount: number
  createdAt: string
  updatedAt: string
}

export interface SessionMessage {
  id: string
  sessionId: string
  role: 'user' | 'assistant' | 'system'
  content: string
  toolCalls?: ToolCall[]
  tokensUsed?: number
  createdAt: string
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: string
  status: 'pending' | 'running' | 'completed' | 'error'
}

export interface CreateSessionInput {
  projectId: string
  agentId: string
  taskId?: string
}

export interface SendMessageInput {
  content: string
}

// User types
export interface User {
  id: string
  email: string
  name: string
  avatarUrl?: string
  createdAt: string
  updatedAt: string
}

// ============================================================================
// API Error Class
// ============================================================================

export class ApiRequestError extends Error {
  public readonly code: string
  public readonly status: number
  public readonly details?: Record<string, unknown>

  constructor(error: ApiError) {
    super(error.message)
    this.name = 'ApiRequestError'
    this.code = error.code
    this.status = error.status
    this.details = error.details
  }
}

// ============================================================================
// Fetch Wrapper
// ============================================================================

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  params?: Record<string, string | number | boolean | undefined>
}

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { body, params, headers: customHeaders, ...restOptions } = options

  // Build URL with query params
  const url = new URL(endpoint, getApiBaseUrl())
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value))
      }
    })
  }

  // Build headers
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...customHeaders,
  }

  // Make request
  const response = await fetch(url.toString(), {
    ...restOptions,
    headers,
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  })

  // Handle non-OK responses
  if (!response.ok) {
    // Handle 401 Unauthorized - redirect to login
    if (response.status === 401) {
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
      throw new ApiRequestError({
        message: 'Session expired. Please log in again.',
        code: 'UNAUTHORIZED',
        status: 401,
      })
    }

    let errorData: ApiError
    try {
      errorData = await response.json()
    } catch {
      errorData = {
        message: response.statusText || 'An unknown error occurred',
        code: 'UNKNOWN_ERROR',
        status: response.status,
      }
    }
    throw new ApiRequestError(errorData)
  }

  // Handle empty responses
  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

// HTTP method helpers
function get<T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  return request<T>(endpoint, { method: 'GET', params })
}

function post<T>(endpoint: string, body?: unknown): Promise<T> {
  return request<T>(endpoint, { method: 'POST', body })
}

function _put<T>(endpoint: string, body?: unknown): Promise<T> {
  return request<T>(endpoint, { method: 'PUT', body })
}

// Re-export for potential future use
export { _put as put }

function patch<T>(endpoint: string, body?: unknown): Promise<T> {
  return request<T>(endpoint, { method: 'PATCH', body })
}

function del<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: 'DELETE' })
}

// ============================================================================
// Organizations API
// ============================================================================

export const organizations = {
  list: (params?: PaginationParams) =>
    get<ApiResponse<Organization[]>>('/api/v1/organizations', params),

  get: (id: string) =>
    get<ApiResponse<Organization>>(`/api/v1/organizations/${id}`),

  getBySlug: (slug: string) =>
    get<ApiResponse<Organization>>(`/api/v1/organizations/slug/${slug}`),

  create: (data: CreateOrganizationInput) =>
    post<ApiResponse<Organization>>('/api/v1/organizations', data),

  update: (id: string, data: UpdateOrganizationInput) =>
    patch<ApiResponse<Organization>>(`/api/v1/organizations/${id}`, data),

  delete: (id: string) =>
    del<void>(`/api/v1/organizations/${id}`),

  getMembers: (id: string, params?: PaginationParams) =>
    get<ApiResponse<User[]>>(`/api/v1/organizations/${id}/members`, params),
}

// ============================================================================
// Projects API
// ============================================================================

export const projects = {
  list: (params?: PaginationParams) =>
    get<ApiResponse<Project[]>>('/api/v1/projects', params),

  get: (id: string) =>
    get<ApiResponse<Project>>(`/api/v1/projects/${id}`),

  getBySlug: (organizationSlug: string, projectSlug: string) =>
    get<ApiResponse<Project>>(`/api/v1/organizations/${organizationSlug}/projects/${projectSlug}`),

  create: (data: CreateProjectInput) =>
    post<ApiResponse<Project>>('/api/v1/projects', data),

  update: (id: string, data: UpdateProjectInput) =>
    patch<ApiResponse<Project>>(`/api/v1/projects/${id}`, data),

  delete: (id: string) =>
    del<void>(`/api/v1/projects/${id}`),
}

// ============================================================================
// Tasks API
// ============================================================================

export const tasks = {
  list: (projectId: string, params?: PaginationParams & { status?: TaskStatus }) =>
    get<ApiResponse<Task[]>>(`/api/v1/projects/${projectId}/tasks`, params),

  get: (id: string) =>
    get<ApiResponse<Task>>(`/api/v1/tasks/${id}`),

  create: (data: CreateTaskInput) =>
    post<ApiResponse<Task>>('/api/v1/tasks', data),

  update: (id: string, data: UpdateTaskInput) =>
    patch<ApiResponse<Task>>(`/api/v1/tasks/${id}`, data),

  delete: (id: string) =>
    del<void>(`/api/v1/tasks/${id}`),

  move: (id: string, status: TaskStatus, order?: number) =>
    post<ApiResponse<Task>>(`/api/v1/tasks/${id}/status`, { status, order }),

  assign: (id: string, agentId: string | null) =>
    patch<ApiResponse<Task>>(`/api/v1/tasks/${id}/assign`, { agentId }),

  getSubtasks: (id: string) =>
    get<ApiResponse<Task[]>>(`/api/v1/tasks/${id}/subtasks`),
}

// ============================================================================
// Agents API
// ============================================================================

export const agents = {
  list: (projectId: string, params?: PaginationParams & { status?: AgentStatus }) =>
    get<ApiResponse<Agent[]>>('/api/v1/agents', { ...params, project_id: projectId }),

  get: (id: string) =>
    get<ApiResponse<Agent>>(`/api/v1/agents/${id}`),

  create: (data: CreateAgentInput) =>
    post<ApiResponse<Agent>>('/api/v1/agents', data),

  update: (id: string, data: UpdateAgentInput) =>
    patch<ApiResponse<Agent>>(`/api/v1/agents/${id}`, data),

  delete: (id: string) =>
    del<void>(`/api/v1/agents/${id}`),

  start: (id: string) =>
    post<ApiResponse<Agent>>(`/api/v1/agents/${id}/start`),

  stop: (id: string) =>
    post<ApiResponse<Agent>>(`/api/v1/agents/${id}/stop`),

  getLogs: (id: string, params?: PaginationParams & { since?: string }) =>
    get<ApiResponse<AgentLog[]>>(`/api/v1/agents/${id}/logs`, params),
}

export interface AgentLog {
  id: string
  agentId: string
  level: 'debug' | 'info' | 'warn' | 'error'
  message: string
  metadata?: Record<string, unknown>
  createdAt: string
}

// ============================================================================
// Sessions API
// ============================================================================

export const sessions = {
  list: (params?: PaginationParams & { projectId?: string; agentId?: string; status?: SessionStatus }) =>
    get<ApiResponse<Session[]>>('/api/v1/sessions', params),

  get: (id: string) =>
    get<ApiResponse<Session>>(`/api/v1/sessions/${id}`),

  create: (data: CreateSessionInput) =>
    post<ApiResponse<Session>>('/api/v1/sessions', data),

  cancel: (id: string) =>
    post<ApiResponse<Session>>(`/api/v1/sessions/${id}/cancel`),

  getMessages: (id: string, params?: PaginationParams) =>
    get<ApiResponse<SessionMessage[]>>(`/api/v1/sessions/${id}/messages`, params),

  sendMessage: (id: string, data: SendMessageInput) =>
    post<ApiResponse<SessionMessage>>(`/api/v1/sessions/${id}/messages`, data),
}

// ============================================================================
// Auth API
// ============================================================================

export interface LoginInput {
  email: string
  password: string
}

export interface RegisterInput {
  email: string
  password: string
  name: string
}

export interface AuthResponse {
  user: User
  token: string
}

export const auth = {
  login: (data: LoginInput) =>
    post<ApiResponse<AuthResponse>>('/api/v1/auth/login', data),

  register: (data: RegisterInput) =>
    post<ApiResponse<AuthResponse>>('/api/v1/auth/register', data),

  logout: () =>
    post<void>('/api/v1/auth/logout'),

  me: () =>
    get<ApiResponse<User>>('/api/v1/auth/me'),

  refresh: () =>
    post<ApiResponse<AuthResponse>>('/api/v1/auth/refresh'),
}

// ============================================================================
// Export default API object
// ============================================================================

export const api = {
  organizations,
  projects,
  tasks,
  agents,
  sessions,
  auth,
}

export default api
