export type TaskStatus = 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'cancelled'
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent'

export interface Task {
  id: string
  projectId: string
  title: string
  description?: string
  status: TaskStatus
  priority: TaskPriority
  labels?: string[]
  assignedAgentId?: string
  assignedAgentName?: string
  parentTaskId?: string
  order: number
  estimatedTokens?: number
  actualTokens?: number
  createdAt: string
  updatedAt: string
  completedAt?: string
}

export interface KanbanColumn {
  id: TaskStatus
  title: string
  tasks: Task[]
}
