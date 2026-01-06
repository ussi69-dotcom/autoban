"use client"

import * as React from "react"
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
} from "@dnd-kit/core"
import { arrayMove, sortableKeyboardCoordinates } from "@dnd-kit/sortable"

import { cn } from "@/lib/utils"
import { KanbanColumn } from "./kanban-column"
import { KanbanCard } from "./kanban-card"
import type { Task, TaskStatus } from "./types"

export type TasksByStatus = {
  [K in TaskStatus]: Task[]
}

const DEFAULT_COLUMNS: { id: TaskStatus; title: string }[] = [
  { id: "backlog", title: "BACKLOG" },
  { id: "todo", title: "TODO" },
  { id: "in_progress", title: "IN PROGRESS" },
  { id: "in_review", title: "IN REVIEW" },
  { id: "done", title: "DONE" },
  { id: "cancelled", title: "CANCELLED" },
]

interface KanbanBoardProps {
  tasks: Task[] | TasksByStatus
  columns?: { id: TaskStatus; title: string }[]
  onTaskMove?: (taskId: string, newStatus: TaskStatus, newIndex: number) => void
  onTaskClick?: (task: Task) => void
  onAddTask?: (status: TaskStatus) => void
  className?: string
}

export function KanbanBoard({
  tasks,
  columns = DEFAULT_COLUMNS,
  onTaskMove,
  onTaskClick,
  onAddTask,
  className,
}: KanbanBoardProps) {
  const [activeTask, setActiveTask] = React.useState<Task | null>(null)
  // Normalize tasks to array format
  const normalizedTasks = React.useMemo(() => {
    if (Array.isArray(tasks)) {
      return tasks
    }
    // Convert TasksByStatus to Task[]
    return Object.values(tasks).flat()
  }, [tasks])

  const [localTasks, setLocalTasks] = React.useState<Task[]>(normalizedTasks)

  // Sync local tasks when props change
  React.useEffect(() => {
    setLocalTasks(normalizedTasks)
  }, [normalizedTasks])

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Group tasks by column
  const columnTasks = React.useMemo(() => {
    const grouped: Record<TaskStatus, Task[]> = {
      backlog: [],
      todo: [],
      in_progress: [],
      in_review: [],
      done: [],
      cancelled: [],
    }

    localTasks.forEach((task) => {
      if (grouped[task.status]) {
        grouped[task.status].push(task)
      }
    })

    return grouped
  }, [localTasks])

  const findTaskById = (id: string): Task | undefined => {
    return localTasks.find((task) => task.id === id)
  }

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event
    const task = findTaskById(active.id as string)
    if (task) {
      setActiveTask(task)
    }
  }

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event
    if (!over) return

    const activeId = active.id as string
    const overId = over.id as string

    const activeTask = findTaskById(activeId)
    if (!activeTask) return

    // Check if we're over a column
    const overData = over.data.current
    const isOverColumn = overData?.type === "column"
    const isOverTask = overData?.type === "task"

    if (isOverColumn) {
      const newStatus = overId as TaskStatus
      if (activeTask.status !== newStatus) {
        setLocalTasks((prev) => {
          return prev.map((task) => {
            if (task.id === activeId) {
              return { ...task, status: newStatus }
            }
            return task
          })
        })
      }
    } else if (isOverTask) {
      const overTask = findTaskById(overId)
      if (overTask && activeTask.status !== overTask.status) {
        setLocalTasks((prev) => {
          return prev.map((task) => {
            if (task.id === activeId) {
              return { ...task, status: overTask.status }
            }
            return task
          })
        })
      }
    }
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveTask(null)

    if (!over) return

    const activeId = active.id as string
    const overId = over.id as string

    const activeTask = findTaskById(activeId)
    if (!activeTask) return

    const overData = over.data.current
    const isOverColumn = overData?.type === "column"
    const isOverTask = overData?.type === "task"

    let newStatus: TaskStatus = activeTask.status
    let newIndex = 0

    if (isOverColumn) {
      newStatus = overId as TaskStatus
      newIndex = columnTasks[newStatus].length
    } else if (isOverTask) {
      const overTask = findTaskById(overId)
      if (overTask) {
        newStatus = overTask.status
        const tasksInColumn = columnTasks[newStatus]
        newIndex = tasksInColumn.findIndex((t) => t.id === overId)

        // Reorder within the same column
        if (activeTask.status === newStatus) {
          const oldIndex = tasksInColumn.findIndex((t) => t.id === activeId)
          if (oldIndex !== newIndex) {
            const reorderedTasks = arrayMove(tasksInColumn, oldIndex, newIndex)
            setLocalTasks((prev) => {
              const otherTasks = prev.filter((t) => t.status !== newStatus)
              return [...otherTasks, ...reorderedTasks]
            })
          }
        }
      }
    }

    // Notify parent of the move
    onTaskMove?.(activeId, newStatus, newIndex)
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div
        className={cn(
          "flex h-full gap-4 overflow-x-auto p-4",
          className
        )}
      >
        {columns.map((column) => (
          <KanbanColumn
            key={column.id}
            id={column.id}
            title={column.title}
            tasks={columnTasks[column.id] || []}
            onTaskClick={onTaskClick}
            onAddTask={onAddTask}
          />
        ))}
      </div>

      {/* Drag overlay for smooth animations */}
      <DragOverlay>
        {activeTask ? (
          <div className="rotate-3 scale-105">
            <KanbanCard task={activeTask} />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
