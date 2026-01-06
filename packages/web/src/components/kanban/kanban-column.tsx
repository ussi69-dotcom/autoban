"use client"

import * as React from "react"
import { useDroppable } from "@dnd-kit/core"
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { Plus } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { KanbanCard } from "./kanban-card"
import type { Task, TaskStatus } from "./types"

interface KanbanColumnProps {
  id: TaskStatus
  title: string
  tasks: Task[]
  onTaskClick?: (task: Task) => void
  onAddTask?: (status: TaskStatus) => void
}

const columnColors: Record<TaskStatus, string> = {
  backlog: "border-t-slate-400",
  todo: "border-t-blue-400",
  in_progress: "border-t-yellow-400",
  in_review: "border-t-purple-400",
  done: "border-t-green-400",
  cancelled: "border-t-red-400",
}

export function KanbanColumn({
  id,
  title,
  tasks,
  onTaskClick,
  onAddTask,
}: KanbanColumnProps) {
  const { isOver, setNodeRef } = useDroppable({
    id,
    data: {
      type: "column",
      status: id,
    },
  })

  const taskIds = React.useMemo(() => tasks.map((task) => task.id), [tasks])

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex h-full w-72 flex-shrink-0 flex-col rounded-lg border-t-4 bg-muted/30",
        columnColors[id],
        isOver && "ring-2 ring-primary ring-offset-2 ring-offset-background"
      )}
    >
      {/* Column header */}
      <div className="flex items-center justify-between p-3 pb-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          <span className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-muted px-1.5 text-xs font-medium text-muted-foreground">
            {tasks.length}
          </span>
        </div>
        {onAddTask && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => onAddTask(id)}
          >
            <Plus className="h-4 w-4" />
            <span className="sr-only">Add task to {title}</span>
          </Button>
        )}
      </div>

      {/* Tasks container */}
      <div className="flex-1 overflow-y-auto p-3">
        <SortableContext items={taskIds} strategy={verticalListSortingStrategy}>
          <div className="flex flex-col gap-2">
            {tasks.map((task) => (
              <KanbanCard key={task.id} task={task} onClick={onTaskClick} />
            ))}
          </div>
        </SortableContext>

        {/* Empty state */}
        {tasks.length === 0 && (
          <div
            className={cn(
              "flex h-24 items-center justify-center rounded-lg border-2 border-dashed",
              "text-sm text-muted-foreground",
              isOver && "border-primary bg-primary/5"
            )}
          >
            {isOver ? "Drop here" : "No tasks"}
          </div>
        )}
      </div>
    </div>
  )
}
