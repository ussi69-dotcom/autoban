"use client"

import * as React from "react"
import { X, Plus, Pencil, Trash2, Save, User } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { Task, TaskPriority, TaskStatus } from "./types"

interface Agent {
  id: string
  name: string
}

interface TaskDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  task: Task | null
  agents?: Agent[]
  onUpdate: (taskId: string, updates: Partial<Task>) => void
  onDelete: (taskId: string) => void
  onStatusChange: (taskId: string, newStatus: TaskStatus) => void
}

const priorityOptions: { value: TaskPriority; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "urgent", label: "Urgent" },
]

const statusOptions: { value: TaskStatus; label: string }[] = [
  { value: "backlog", label: "Backlog" },
  { value: "todo", label: "Todo" },
  { value: "in_progress", label: "In Progress" },
  { value: "in_review", label: "In Review" },
  { value: "done", label: "Done" },
  { value: "cancelled", label: "Cancelled" },
]

const priorityColors: Record<TaskPriority, string> = {
  low: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  medium: "bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300",
  high: "bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300",
  urgent: "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
}

export function TaskDetailDialog({
  open,
  onOpenChange,
  task,
  agents = [],
  onUpdate,
  onDelete,
  onStatusChange,
}: TaskDetailDialogProps) {
  const [isEditing, setIsEditing] = React.useState(false)
  const [editedTask, setEditedTask] = React.useState<Task | null>(null)
  const [newLabel, setNewLabel] = React.useState("")
  const [showDeleteConfirm, setShowDeleteConfirm] = React.useState(false)

  // Reset editing state when dialog opens or task changes
  React.useEffect(() => {
    if (open && task) {
      setEditedTask({ ...task })
      setIsEditing(false)
      setShowDeleteConfirm(false)
      setNewLabel("")
    }
  }, [open, task])

  if (!task || !editedTask) return null

  const handleSave = () => {
    onUpdate(task.id, {
      title: editedTask.title,
      description: editedTask.description,
      priority: editedTask.priority,
      labels: editedTask.labels,
      assignedAgentId: editedTask.assignedAgentId,
      assignedAgentName: editedTask.assignedAgentName,
    })
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditedTask({ ...task })
    setIsEditing(false)
  }

  const handleAddLabel = () => {
    const currentLabels = editedTask.labels || []
    if (newLabel.trim() && !currentLabels.includes(newLabel.trim())) {
      setEditedTask({
        ...editedTask,
        labels: [...currentLabels, newLabel.trim()],
      })
      setNewLabel("")
    }
  }

  const handleRemoveLabel = (labelToRemove: string) => {
    const currentLabels = editedTask.labels || []
    setEditedTask({
      ...editedTask,
      labels: currentLabels.filter((label) => label !== labelToRemove),
    })
  }

  const handleLabelKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault()
      handleAddLabel()
    }
  }

  const handleStatusChange = (newStatus: TaskStatus) => {
    onStatusChange(task.id, newStatus)
    setEditedTask({ ...editedTask, status: newStatus })
  }

  const handleAgentChange = (agentId: string) => {
    const agent = agents.find((a) => a.id === agentId)
    setEditedTask({
      ...editedTask,
      assignedAgentId: agentId || undefined,
      assignedAgentName: agent?.name,
    })
  }

  const handleDelete = () => {
    onDelete(task.id)
    onOpenChange(false)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start justify-between pr-8">
            {isEditing ? (
              <Input
                value={editedTask.title}
                onChange={(e) =>
                  setEditedTask({ ...editedTask, title: e.target.value })
                }
                className="text-lg font-semibold"
              />
            ) : (
              <DialogTitle className="text-xl">{task.title}</DialogTitle>
            )}
          </div>
          <DialogDescription className="flex items-center gap-2 text-sm">
            <span>Created {formatDate(task.createdAt)}</span>
            {task.updatedAt !== task.createdAt && (
              <>
                <span className="text-muted-foreground">|</span>
                <span>Updated {formatDate(task.updatedAt)}</span>
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* Status buttons */}
          <div className="grid gap-2">
            <Label>Status</Label>
            <div className="flex flex-wrap gap-2">
              {statusOptions.map((option) => (
                <Button
                  key={option.value}
                  variant={editedTask.status === option.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleStatusChange(option.value)}
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Priority */}
          <div className="grid gap-2">
            <Label>Priority</Label>
            {isEditing ? (
              <Select
                value={editedTask.priority}
                onValueChange={(value) =>
                  setEditedTask({ ...editedTask, priority: value as TaskPriority })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  {priorityOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Badge
                variant="outline"
                className={cn("w-fit", priorityColors[task.priority])}
              >
                {priorityOptions.find((p) => p.value === task.priority)?.label}
              </Badge>
            )}
          </div>

          {/* Description */}
          <div className="grid gap-2">
            <Label>Description</Label>
            {isEditing ? (
              <Textarea
                value={editedTask.description || ""}
                onChange={(e) =>
                  setEditedTask({ ...editedTask, description: e.target.value })
                }
                placeholder="Add a description..."
                rows={4}
              />
            ) : (
              <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                {task.description || "No description provided."}
              </p>
            )}
          </div>

          {/* Labels */}
          <div className="grid gap-2">
            <Label>Labels</Label>
            {isEditing && (
              <div className="flex gap-2 mb-2">
                <Input
                  placeholder="Add a label..."
                  value={newLabel}
                  onChange={(e) => setNewLabel(e.target.value)}
                  onKeyDown={handleLabelKeyDown}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleAddLabel}
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            )}
            <div className="flex flex-wrap gap-1">
              {(editedTask.labels || []).length > 0 ? (
                (editedTask.labels || []).map((label) => (
                  <span
                    key={label}
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
                      "bg-secondary text-secondary-foreground"
                    )}
                  >
                    {label}
                    {isEditing && (
                      <button
                        type="button"
                        onClick={() => handleRemoveLabel(label)}
                        className="hover:text-destructive focus:outline-none"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </span>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No labels</span>
              )}
            </div>
          </div>

          {/* Assigned Agent */}
          <div className="grid gap-2">
            <Label>Assigned Agent</Label>
            {isEditing ? (
              <Select
                value={editedTask.assignedAgentId || ""}
                onValueChange={handleAgentChange}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select an agent..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Unassigned</SelectItem>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : task.assignedAgentName ? (
              <div className="flex items-center gap-2 text-sm">
                <User className="h-4 w-4 text-muted-foreground" />
                <span>{task.assignedAgentName}</span>
              </div>
            ) : (
              <span className="text-sm text-muted-foreground">Unassigned</span>
            )}
          </div>
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-between">
          {/* Delete section */}
          <div className="flex gap-2">
            {showDeleteConfirm ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDeleteConfirm(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDelete}
                >
                  Confirm Delete
                </Button>
              </>
            ) : (
              <Button
                variant="outline"
                size="sm"
                className="text-destructive hover:text-destructive"
                onClick={() => setShowDeleteConfirm(true)}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
            )}
          </div>

          {/* Edit/Save section */}
          <div className="flex gap-2">
            {isEditing ? (
              <>
                <Button variant="outline" onClick={handleCancel}>
                  Cancel
                </Button>
                <Button onClick={handleSave}>
                  <Save className="h-4 w-4 mr-2" />
                  Save Changes
                </Button>
              </>
            ) : (
              <Button variant="outline" onClick={() => setIsEditing(true)}>
                <Pencil className="h-4 w-4 mr-2" />
                Edit
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
