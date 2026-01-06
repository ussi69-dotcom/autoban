"use client"

import * as React from "react"
import { Plus, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import { AgentCard, type Agent } from "./agent-card"

interface AgentListProps {
  agents?: Agent[]
  isLoading?: boolean
  onSpawnAgent?: () => void
  onRefresh?: () => void
  onStopAgent?: (agentId: string) => void
  onRestartAgent?: (agentId: string) => void
  onViewLogs?: (agentId: string) => void
  className?: string
}

function AgentListSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="rounded-lg border bg-card p-4 animate-pulse"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-lg bg-muted" />
            <div className="flex-1">
              <div className="h-4 w-24 bg-muted rounded mb-2" />
              <div className="h-3 w-16 bg-muted rounded" />
            </div>
            <div className="h-6 w-16 bg-muted rounded-full" />
          </div>
          <div className="space-y-3">
            <div className="h-3 w-full bg-muted rounded" />
            <div className="h-3 w-3/4 bg-muted rounded" />
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyState({ onSpawnAgent }: { onSpawnAgent?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed bg-muted/30 px-6 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
        <Plus className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-1">No agents running</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-sm">
        Spawn a new agent to start processing tasks. Agents can work on code,
        run tests, and more.
      </p>
      {onSpawnAgent && (
        <button
          onClick={onSpawnAgent}
          className={cn(
            "inline-flex items-center justify-center gap-2",
            "rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
            "hover:bg-primary/90 transition-colors",
            "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          )}
        >
          <Plus className="h-4 w-4" />
          Spawn Agent
        </button>
      )}
    </div>
  )
}

export function AgentList({
  agents = [],
  isLoading = false,
  onSpawnAgent,
  onRefresh,
  onStopAgent,
  onRestartAgent,
  onViewLogs,
  className,
}: AgentListProps) {
  const statusCounts = React.useMemo(() => {
    return agents.reduce(
      (acc, agent) => {
        acc[agent.status] = (acc[agent.status] || 0) + 1
        return acc
      },
      {} as Record<string, number>
    )
  }, [agents])

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">Agent Instances</h2>
          <p className="text-sm text-muted-foreground">
            {agents.length === 0
              ? "No agents are currently running"
              : `${agents.length} agent${agents.length === 1 ? "" : "s"} running`}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className={cn(
                "inline-flex items-center justify-center gap-2",
                "rounded-lg border px-3 py-2 text-sm font-medium",
                "hover:bg-accent transition-colors",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
                "disabled:opacity-50 disabled:pointer-events-none"
              )}
            >
              <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
              Refresh
            </button>
          )}

          {onSpawnAgent && (
            <button
              onClick={onSpawnAgent}
              className={cn(
                "inline-flex items-center justify-center gap-2",
                "rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
                "hover:bg-primary/90 transition-colors",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              )}
            >
              <Plus className="h-4 w-4" />
              Spawn Agent
            </button>
          )}
        </div>
      </div>

      {/* Status summary */}
      {agents.length > 0 && (
        <div className="flex flex-wrap gap-4">
          <StatusBadge
            status="idle"
            count={statusCounts.idle || 0}
            label="Idle"
          />
          <StatusBadge
            status="busy"
            count={statusCounts.busy || 0}
            label="Busy"
          />
          <StatusBadge
            status="error"
            count={statusCounts.error || 0}
            label="Error"
          />
        </div>
      )}

      {/* Agent grid */}
      {isLoading ? (
        <AgentListSkeleton />
      ) : agents.length === 0 ? (
        <EmptyState onSpawnAgent={onSpawnAgent} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onStop={() => onStopAgent?.(agent.id)}
              onRestart={() => onRestartAgent?.(agent.id)}
              onViewLogs={() => onViewLogs?.(agent.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function StatusBadge({
  status,
  count,
  label,
}: {
  status: "idle" | "busy" | "error"
  count: number
  label: string
}) {
  const colors = {
    idle: "bg-green-500/10 text-green-600 dark:text-green-400",
    busy: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400",
    error: "bg-red-500/10 text-red-600 dark:text-red-400",
  }

  const dotColors = {
    idle: "bg-green-500",
    busy: "bg-yellow-500",
    error: "bg-red-500",
  }

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-medium",
        colors[status]
      )}
    >
      <span className={cn("h-2 w-2 rounded-full", dotColors[status])} />
      <span>
        {count} {label}
      </span>
    </div>
  )
}
