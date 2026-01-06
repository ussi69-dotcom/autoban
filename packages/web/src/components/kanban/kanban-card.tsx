"use client"

import * as React from "react"
import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { GripVertical, User } from "lucide-react"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import type { Task, TaskPriority } from "./types"

interface KanbanCardProps {
  task: Task
  onClick?: (task: Task) => void
}

const priorityConfig: Record<TaskPriority, { label: string; className: string }> = {
  low: {
    label: "Low",
    className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
  medium: {
    label: "Medium",
    className: "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300",
  },
  high: {
    label: "High",
    className: "bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300",
  },
  urgent: {
    label: "Urgent",
    className: "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
  },
}

const labelColors = [
  "bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300",
  "bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300",
  "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300",
  "bg-pink-100 text-pink-700 dark:bg-pink-900/50 dark:text-pink-300",
  "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/50 dark:text-cyan-300",
]

function getLabelColor(label: string): string {
  const hash = label.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0)
  return labelColors[hash % labelColors.length]
}

export function KanbanCard({ task, onClick }: KanbanCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: task.id,
    data: {
      type: "task",
      task,
    },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  const priority = priorityConfig[task.priority]

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "group relative rounded-lg border bg-card p-3 shadow-sm transition-all",
        "hover:border-primary/50 hover:shadow-md",
        isDragging && "opacity-50 shadow-lg ring-2 ring-primary",
        "cursor-pointer"
      )}
      onClick={() => onClick?.(task)}
    >
      {/* Drag handle */}
      <button
        {...attributes}
        {...listeners}
        className={cn(
          "absolute left-1 top-1/2 -translate-y-1/2 p-1 rounded",
          "opacity-0 group-hover:opacity-100 transition-opacity",
          "hover:bg-muted cursor-grab active:cursor-grabbing",
          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <GripVertical className="h-4 w-4 text-muted-foreground" />
      </button>

      <div className="pl-5">
        {/* Priority badge */}
        <div className="mb-2 flex items-center gap-2">
          <Badge variant="outline" className={cn("text-xs", priority.className)}>
            {priority.label}
          </Badge>
        </div>

        {/* Task title */}
        <h4 className="mb-2 text-sm font-medium leading-tight text-foreground">
          {task.title}
        </h4>

        {/* Labels */}
        {task.labels && task.labels.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1">
            {task.labels.slice(0, 3).map((label) => (
              <span
                key={label}
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  getLabelColor(label)
                )}
              >
                {label}
              </span>
            ))}
            {task.labels.length > 3 && (
              <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground">
                +{task.labels.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Assigned agent */}
        {task.assignedAgentName && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <User className="h-3 w-3" />
            <span className="truncate">{task.assignedAgentName}</span>
          </div>
        )}
      </div>
    </div>
  )
}
