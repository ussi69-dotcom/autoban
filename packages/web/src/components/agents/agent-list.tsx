"use client"

import * as React from "react"
import { Plus, RefreshCw, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { AgentCard, StatusBadge } from "./agent-card"
import type { Agent, AgentStatus } from "@/lib/api"
import { useSpawnAgent } from "@/hooks/use-api"

interface AgentListProps {
  agents?: Agent[]
  isLoading?: boolean
  onSpawnAgent?: () => void
  onRefresh?: () => void
  onStopAgent?: (agentId: string) => void
  onRestartAgent?: (agentId: string) => void
  onViewLogs?: (agentId: string) => void
  className?: string
  projectId?: string
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

function EmptyState({ onSpawn }: { onSpawn: () => void }) {
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
      <button
        onClick={onSpawn}
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
  projectId,
}: AgentListProps) {
  const spawnAgent = useSpawnAgent()

  const handleSpawn = async () => {
    if (onSpawnAgent) {
      onSpawnAgent()
      return
    }

    if (projectId) {
      try {
        await spawnAgent.mutateAsync({
          project_id: projectId,
          name: `Agent ${agents.length + 1}`,
          type: "sisyphus", // Default type
          model: "claude-3-5-sonnet-20240620",
        })
      } catch (error) {
        console.error("Failed to spawn agent:", error)
      }
    }
  }

  const statusCounts = React.useMemo(() => {
    return agents.reduce(
      (acc, agent) => {
        const status = agent.status as AgentStatus
        acc[status] = (acc[status] || 0) + 1
        return acc
      },
      {} as Record<AgentStatus, number>
    )
  }, [agents])

  // Define statuses order
  const statuses: AgentStatus[] = ['initializing', 'idle', 'busy', 'error', 'stopping', 'stopped']

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

          <button
            onClick={handleSpawn}
            disabled={spawnAgent.isPending}
            className={cn(
              "inline-flex items-center justify-center gap-2",
              "rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
              "hover:bg-primary/90 transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
              "disabled:opacity-50 disabled:pointer-events-none"
            )}
          >
            {spawnAgent.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Spawn Agent
          </button>
        </div>
      </div>

      {/* Status summary */}
      {agents.length > 0 && (
        <div className="flex flex-wrap gap-4">
          {statuses.map(status => {
            const count = statusCounts[status] || 0
            if (count === 0 && status !== 'idle' && status !== 'busy') return null
            return (
              <div key={status} className="flex items-center gap-2">
                 <StatusBadge status={status} />
                 <span className="text-sm text-muted-foreground font-medium">x{count}</span>
              </div>
            )
          })}
        </div>
      )}

      {/* Agent grid */}
      {isLoading ? (
        <AgentListSkeleton />
      ) : agents.length === 0 ? (
        <EmptyState onSpawn={handleSpawn} />
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

