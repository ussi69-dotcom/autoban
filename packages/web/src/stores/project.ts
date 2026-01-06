import { create } from 'zustand'
import { devtools, subscribeWithSelector } from 'zustand/middleware'
import { api, type Project, type Task, type TaskStatus, type Agent, ApiRequestError } from '@/lib/api'

// ============================================================================
// Types
// ============================================================================

export type TasksByStatus = {
  [K in TaskStatus]: Task[]
}

export interface ProjectState {
  // Current project
  currentProject: Project | null
  projects: Project[]

  // Tasks grouped by status
  tasks: TasksByStatus

  // Agents
  agents: Agent[]

  // Loading states
  isLoadingProject: boolean
  isLoadingTasks: boolean
  isLoadingAgents: boolean

  // Error states
  projectError: string | null
  tasksError: string | null
  agentsError: string | null
}

export interface ProjectActions {
  // Project actions
  setProject: (project: Project | null) => void
  fetchProject: (projectId: string) => Promise<void>
  fetchProjects: () => Promise<void>

  // Task actions
  fetchTasks: (projectId: string) => Promise<void>
  updateTask: (taskId: string, updates: Partial<Task>) => Promise<void>
  moveTask: (taskId: string, status: TaskStatus, order?: number) => Promise<void>
  createTask: (task: Omit<Task, 'id' | 'createdAt' | 'updatedAt' | 'order'>) => Promise<Task>
  deleteTask: (taskId: string) => Promise<void>

  // Agent actions
  fetchAgents: (projectId: string) => Promise<void>
  updateAgent: (agentId: string, updates: Partial<Agent>) => Promise<void>

  // Optimistic update helpers
  optimisticMoveTask: (taskId: string, newStatus: TaskStatus, newOrder?: number) => void
  revertTaskMove: (taskId: string, originalStatus: TaskStatus, originalOrder: number) => void

  // Utility actions
  clearErrors: () => void
  reset: () => void
}

export type ProjectStore = ProjectState & ProjectActions

// ============================================================================
// Initial State
// ============================================================================

const emptyTasksByStatus: TasksByStatus = {
  backlog: [],
  todo: [],
  in_progress: [],
  in_review: [],
  done: [],
  cancelled: [],
}

const initialState: ProjectState = {
  currentProject: null,
  projects: [],
  tasks: { ...emptyTasksByStatus },
  agents: [],
  isLoadingProject: false,
  isLoadingTasks: false,
  isLoadingAgents: false,
  projectError: null,
  tasksError: null,
  agentsError: null,
}

// ============================================================================
// Helper Functions
// ============================================================================

function groupTasksByStatus(tasks: Task[]): TasksByStatus {
  const grouped: TasksByStatus = {
    backlog: [],
    todo: [],
    in_progress: [],
    in_review: [],
    done: [],
    cancelled: [],
  }

  tasks.forEach((task) => {
    if (grouped[task.status]) {
      grouped[task.status].push(task)
    }
  })

  // Sort each group by order
  Object.keys(grouped).forEach((status) => {
    grouped[status as TaskStatus].sort((a, b) => a.order - b.order)
  })

  return grouped
}

function flattenTasks(tasksByStatus: TasksByStatus): Task[] {
  return Object.values(tasksByStatus).flat()
}

// ============================================================================
// Store
// ============================================================================

export const useProjectStore = create<ProjectStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      ...initialState,

      // ----------------------------------------------------------------------
      // Project Actions
      // ----------------------------------------------------------------------

      setProject: (project: Project | null) => {
        set({ currentProject: project })
      },

      fetchProject: async (projectId: string) => {
        set({ isLoadingProject: true, projectError: null })

        try {
          const response = await api.projects.get(projectId)
          // Backend returns ProjectResponse directly, not { data: ProjectResponse }
          const project = (response as unknown as Project).id ? (response as unknown as Project) : response.data
          set({
            currentProject: project,
            isLoadingProject: false,
          })
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to fetch project'

          set({
            isLoadingProject: false,
            projectError: message,
          })
          console.error('Failed to fetch project:', message)
        }
      },

      fetchProjects: async () => {
        set({ isLoadingProject: true, projectError: null })

        try {
          const response = await api.projects.list()
          // Backend returns { items: [], ... } or { data: [] }
          const projectList = (response as unknown as { items?: Project[] }).items ?? response.data ?? []
          set({
            projects: projectList,
            isLoadingProject: false,
          })
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to fetch projects'

          set({
            isLoadingProject: false,
            projectError: message,
          })
          console.error('Failed to fetch projects:', message)
        }
      },

      // ----------------------------------------------------------------------
      // Task Actions
      // ----------------------------------------------------------------------

      fetchTasks: async (projectId: string) => {
        set({ isLoadingTasks: true, tasksError: null })

        try {
          const response = await api.tasks.list(projectId)
          // Backend returns { items: [], ... } or { data: [] }
          const taskList = (response as unknown as { items?: Task[] }).items ?? response.data ?? []
          const groupedTasks = groupTasksByStatus(taskList)

          set({
            tasks: groupedTasks,
            isLoadingTasks: false,
          })
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to fetch tasks'

          set({
            isLoadingTasks: false,
            tasksError: message,
          })
          // Don't throw - just log
          console.error('Failed to fetch tasks:', message)
        }
      },

      updateTask: async (taskId: string, updates: Partial<Task>) => {
        const { tasks } = get()

        try {
          const response = await api.tasks.update(taskId, updates)
          // Backend returns Task directly, not { data: Task }
          const updatedTask = (response as unknown as Task).id ? (response as unknown as Task) : response.data

          // Update the task in the correct status group
          const newTasks = { ...tasks }
          Object.keys(newTasks).forEach((status) => {
            newTasks[status as TaskStatus] = newTasks[status as TaskStatus].map((task) =>
              task.id === taskId ? updatedTask : task
            )
          })

          // If status changed, move to new group
          if (updates.status) {
            const oldTasks = flattenTasks(tasks)
            const oldTask = oldTasks.find((t) => t.id === taskId)

            if (oldTask && oldTask.status !== updates.status) {
              // Remove from old status
              newTasks[oldTask.status] = newTasks[oldTask.status].filter(
                (t) => t.id !== taskId
              )
              // Add to new status
              newTasks[updates.status].push(updatedTask)
              newTasks[updates.status].sort((a, b) => a.order - b.order)
            }
          }

          set({ tasks: newTasks })
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to update task'

          set({ tasksError: message })
          throw error
        }
      },

      moveTask: async (taskId: string, status: TaskStatus, order?: number) => {
        const { tasks } = get()

        // Find original task for potential revert
        const allTasks = flattenTasks(tasks)
        const originalTask = allTasks.find((t) => t.id === taskId)

        if (!originalTask) {
          throw new Error('Task not found')
        }

        const originalStatus = originalTask.status
        const originalOrder = originalTask.order

        // Optimistic update
        get().optimisticMoveTask(taskId, status, order)

        try {
          await api.tasks.move(taskId, status, order)
        } catch (error) {
          // Revert on failure
          get().revertTaskMove(taskId, originalStatus, originalOrder)

          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to move task'

          set({ tasksError: message })
          throw error
        }
      },

      createTask: async (taskData) => {
        try {
          const response = await api.tasks.create({
            projectId: taskData.projectId,
            title: taskData.title,
            description: taskData.description,
            status: taskData.status,
            priority: taskData.priority,
            parentTaskId: taskData.parentTaskId,
            estimatedTokens: taskData.estimatedTokens,
          })

          // Backend returns Task directly, not { data: Task }
          const newTask = (response as unknown as Task).id ? (response as unknown as Task) : response.data
          const { tasks } = get()

          // Add to appropriate status group
          const newTasks = { ...tasks }
          const taskStatus = newTask.status || 'backlog'
          newTasks[taskStatus] = [...(newTasks[taskStatus] || []), newTask]
          newTasks[taskStatus].sort((a, b) => a.order - b.order)

          set({ tasks: newTasks })
          return newTask
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to create task'

          set({ tasksError: message })
          throw error
        }
      },

      deleteTask: async (taskId: string) => {
        const { tasks } = get()

        try {
          await api.tasks.delete(taskId)

          // Remove from all status groups
          const newTasks = { ...tasks }
          Object.keys(newTasks).forEach((status) => {
            newTasks[status as TaskStatus] = newTasks[status as TaskStatus].filter(
              (t) => t.id !== taskId
            )
          })

          set({ tasks: newTasks })
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to delete task'

          set({ tasksError: message })
          throw error
        }
      },

      // ----------------------------------------------------------------------
      // Optimistic Update Helpers
      // ----------------------------------------------------------------------

      optimisticMoveTask: (taskId: string, newStatus: TaskStatus, newOrder?: number) => {
        const { tasks } = get()
        const allTasks = flattenTasks(tasks)
        const task = allTasks.find((t) => t.id === taskId)

        if (!task) return

        const newTasks = { ...tasks }

        // Remove from old status
        newTasks[task.status] = newTasks[task.status].filter((t) => t.id !== taskId)

        // Add to new status with updated order
        const updatedTask = {
          ...task,
          status: newStatus,
          order: newOrder ?? newTasks[newStatus].length,
        }

        newTasks[newStatus] = [...newTasks[newStatus], updatedTask]
        newTasks[newStatus].sort((a, b) => a.order - b.order)

        set({ tasks: newTasks })
      },

      revertTaskMove: (taskId: string, originalStatus: TaskStatus, originalOrder: number) => {
        const { tasks } = get()
        const allTasks = flattenTasks(tasks)
        const task = allTasks.find((t) => t.id === taskId)

        if (!task) return

        const newTasks = { ...tasks }

        // Remove from current status
        newTasks[task.status] = newTasks[task.status].filter((t) => t.id !== taskId)

        // Add back to original status
        const revertedTask = {
          ...task,
          status: originalStatus,
          order: originalOrder,
        }

        newTasks[originalStatus] = [...newTasks[originalStatus], revertedTask]
        newTasks[originalStatus].sort((a, b) => a.order - b.order)

        set({ tasks: newTasks })
      },

      // ----------------------------------------------------------------------
      // Agent Actions
      // ----------------------------------------------------------------------

      fetchAgents: async (projectId: string) => {
        set({ isLoadingAgents: true, agentsError: null })

        try {
          const response = await api.agents.list(projectId)
          // Backend returns { items: [], ... } or { data: [] }
          const agents = (response as unknown as { items?: Agent[] }).items ?? response.data ?? []
          set({
            agents,
            isLoadingAgents: false,
          })
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to fetch agents'

          set({
            isLoadingAgents: false,
            agentsError: message,
          })
          // Don't throw - just log
          console.error('Failed to fetch agents:', message)
        }
      },

      updateAgent: async (agentId: string, updates: Partial<Agent>) => {
        const { agents } = get()

        try {
          const response = await api.agents.update(agentId, updates)
          // Backend returns Agent directly, not { data: Agent }
          const updatedAgent = (response as unknown as Agent).id ? (response as unknown as Agent) : response.data

          set({
            agents: agents.map((agent) =>
              agent.id === agentId ? updatedAgent : agent
            ),
          })
        } catch (error) {
          const message = error instanceof ApiRequestError
            ? error.message
            : 'Failed to update agent'

          set({ agentsError: message })
          console.error('Failed to update agent:', message)
        }
      },

      // ----------------------------------------------------------------------
      // Utility Actions
      // ----------------------------------------------------------------------

      clearErrors: () => {
        set({
          projectError: null,
          tasksError: null,
          agentsError: null,
        })
      },

      reset: () => {
        set(initialState)
      },
    })),
    { name: 'project-store' }
  )
)

// ============================================================================
// Selectors
// ============================================================================

export const selectCurrentProject = (state: ProjectStore) => state.currentProject
export const selectProjects = (state: ProjectStore) => state.projects
export const selectTasks = (state: ProjectStore) => state.tasks
export const selectAgents = (state: ProjectStore) => state.agents
export const selectIsLoading = (state: ProjectStore) =>
  state.isLoadingProject || state.isLoadingTasks || state.isLoadingAgents

export const selectTasksByStatus = (status: TaskStatus) => (state: ProjectStore) =>
  state.tasks[status]

export const selectTaskById = (taskId: string) => (state: ProjectStore) =>
  flattenTasks(state.tasks).find((t) => t.id === taskId)

export const selectAgentById = (agentId: string) => (state: ProjectStore) =>
  state.agents.find((a) => a.id === agentId)

export const selectActiveAgents = (state: ProjectStore) =>
  state.agents.filter((a) => a.status === 'idle' || a.status === 'busy')

// ============================================================================
// Hooks
// ============================================================================

export function useProject() {
  const currentProject = useProjectStore(selectCurrentProject)
  const projects = useProjectStore(selectProjects)
  const tasks = useProjectStore(selectTasks)
  const agents = useProjectStore(selectAgents)
  const isLoading = useProjectStore(selectIsLoading)

  const setProject = useProjectStore((state) => state.setProject)
  const fetchProject = useProjectStore((state) => state.fetchProject)
  const fetchProjects = useProjectStore((state) => state.fetchProjects)
  const fetchTasks = useProjectStore((state) => state.fetchTasks)
  const updateTask = useProjectStore((state) => state.updateTask)
  const moveTask = useProjectStore((state) => state.moveTask)
  const createTask = useProjectStore((state) => state.createTask)
  const deleteTask = useProjectStore((state) => state.deleteTask)
  const fetchAgents = useProjectStore((state) => state.fetchAgents)
  const updateAgent = useProjectStore((state) => state.updateAgent)
  const clearErrors = useProjectStore((state) => state.clearErrors)
  const reset = useProjectStore((state) => state.reset)

  return {
    currentProject,
    projects,
    tasks,
    agents,
    isLoading,
    setProject,
    fetchProject,
    fetchProjects,
    fetchTasks,
    updateTask,
    moveTask,
    createTask,
    deleteTask,
    fetchAgents,
    updateAgent,
    clearErrors,
    reset,
  }
}

export default useProjectStore
