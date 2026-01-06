import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  api,
  type Project,
  type Task,
  type CreateProjectInput,
  type UpdateProjectInput,
  type CreateTaskInput,
  type UpdateTaskInput,
  type TaskStatus,
  type Agent,
  type SpawnAgentInput,
  type PaginationParams,
} from '@/lib/api'

// ============================================================================
// Query Keys
// ============================================================================

export const queryKeys = {
  projects: {
    all: ['projects'] as const,
    list: () => [...queryKeys.projects.all, 'list'] as const,
    detail: (id: string) => [...queryKeys.projects.all, 'detail', id] as const,
  },
  tasks: {
    all: ['tasks'] as const,
    list: (projectId: string, params?: { status?: TaskStatus }) =>
      [...queryKeys.tasks.all, 'list', projectId, params] as const,
    detail: (id: string) => [...queryKeys.tasks.all, 'detail', id] as const,
  },
  agents: {
    all: ['agents'] as const,
    list: (projectId: string) => [...queryKeys.agents.all, 'list', projectId] as const,
    detail: (id: string) => [...queryKeys.agents.all, 'detail', id] as const,
  },
  organizations: {
    all: ['organizations'] as const,
    list: () => [...queryKeys.organizations.all, 'list'] as const,
    detail: (id: string) => [...queryKeys.organizations.all, 'detail', id] as const,
  },
  user: {
    me: ['user', 'me'] as const,
  },
}

// ============================================================================
// Organization Hooks
// ============================================================================

export function useOrganizations(params?: PaginationParams) {
  return useQuery({
    queryKey: queryKeys.organizations.list(),
    queryFn: () => api.organizations.list(params),
    select: (response) => response.data,
  })
}

// ============================================================================
// Project Hooks
// ============================================================================

export function useProjects(params?: PaginationParams) {
  return useQuery({
    queryKey: queryKeys.projects.list(),
    queryFn: () => api.projects.list(params),
    // Backend returns { items: [], total, page, ... } not { data: [] }
    select: (response) => (response as unknown as { items: Project[] }).items ?? response.data,
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: queryKeys.projects.detail(id),
    queryFn: () => api.projects.get(id),
    select: (response) => response.data,
    enabled: !!id,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateProjectInput) => api.projects.create(data),
    onSuccess: (response) => {
      // Backend returns ProjectResponse directly, not { data: ProjectResponse }
      const project = (response as unknown as Project).id ? (response as unknown as Project) : response.data
      // Invalidate the projects list
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.list(),
      })
      // Also set the project detail in cache
      if (project?.id) {
        queryClient.setQueryData(queryKeys.projects.detail(project.id), response)
      }
    },
  })
}

export function useUpdateProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateProjectInput }) =>
      api.projects.update(id, data),
    onSuccess: (response) => {
      const project = response.data
      // Update the project in cache
      queryClient.setQueryData(queryKeys.projects.detail(project.id), response)
      // Invalidate the projects list
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.list(),
      })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.projects.delete(id),
    onSuccess: (_data, id) => {
      // Remove from cache
      queryClient.removeQueries({
        queryKey: queryKeys.projects.detail(id),
      })
      // Invalidate all project lists (we don't know the orgId here)
      queryClient.invalidateQueries({
        queryKey: queryKeys.projects.all,
      })
    },
  })
}

// ============================================================================
// Task Hooks
// ============================================================================

export function useTasks(
  projectId: string,
  params?: PaginationParams & { status?: TaskStatus }
) {
  return useQuery({
    queryKey: queryKeys.tasks.list(projectId, params),
    queryFn: () => api.tasks.list(projectId, params),
    select: (response) => response.data,
    enabled: !!projectId,
  })
}

export function useTask(id: string) {
  return useQuery({
    queryKey: queryKeys.tasks.detail(id),
    queryFn: () => api.tasks.get(id),
    select: (response) => response.data,
    enabled: !!id,
  })
}

export function useCreateTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateTaskInput) => api.tasks.create(data),
    onSuccess: (response) => {
      const task = response.data
      // Invalidate the tasks list for the project
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.list(task.projectId),
      })
      // Set the task detail in cache
      queryClient.setQueryData(queryKeys.tasks.detail(task.id), response)
    },
  })
}

export function useUpdateTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTaskInput }) =>
      api.tasks.update(id, data),
    onSuccess: (response) => {
      const task = response.data
      // Update the task in cache
      queryClient.setQueryData(queryKeys.tasks.detail(task.id), response)
      // Invalidate the tasks list
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.list(task.projectId),
      })
    },
  })
}

export function useDeleteTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.tasks.delete(id),
    onSuccess: (_data, id) => {
      // Remove from cache
      queryClient.removeQueries({
        queryKey: queryKeys.tasks.detail(id),
      })
      // Invalidate all task lists (we don't know the projectId here)
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.all,
      })
    },
  })
}

export function useMoveTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      id,
      status,
      order,
    }: {
      id: string
      status: TaskStatus
      order?: number
    }) => api.tasks.move(id, status, order),
    onSuccess: (response) => {
      const task = response.data
      queryClient.setQueryData(queryKeys.tasks.detail(task.id), response)
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.list(task.projectId),
      })
    },
  })
}

export function useAssignTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, agentId }: { id: string; agentId: string | null }) =>
      api.tasks.assign(id, agentId),
    onSuccess: (response) => {
      const task = response.data
      queryClient.setQueryData(queryKeys.tasks.detail(task.id), response)
      queryClient.invalidateQueries({
        queryKey: queryKeys.tasks.list(task.projectId),
      })
    },
  })
}

// ============================================================================
// Agent Hooks
// ============================================================================

export function useAgents(projectId: string, params?: PaginationParams) {
  return useQuery({
    queryKey: queryKeys.agents.list(projectId),
    queryFn: () => api.agents.list(projectId, params),
    select: (response) => response.data,
    enabled: !!projectId,
  })
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: queryKeys.agents.detail(id),
    queryFn: () => api.agents.get(id),
    select: (response) => response.data,
    enabled: !!id,
  })
}

export function useSpawnAgent() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: SpawnAgentInput) => api.agents.spawn(data),
    onSuccess: (response) => {
      const agent = response.data
      queryClient.setQueryData(queryKeys.agents.detail(agent.id), response)
      queryClient.invalidateQueries({
        queryKey: queryKeys.agents.list(agent.projectId),
      })
    },
  })
}

// ============================================================================
// User Hooks
// ============================================================================

export function useCurrentUser() {
  return useQuery({
    queryKey: queryKeys.user.me,
    queryFn: () => api.auth.me(),
    select: (response) => response.data,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// ============================================================================
// Type exports for convenience
// ============================================================================

export type { Project, Task, Agent, TaskStatus }
