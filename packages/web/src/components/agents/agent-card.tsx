"use client"

import * as React from "react"
import Link from "next/link"
import {
  Bot,
  Cpu,
  ExternalLink,
  MemoryStick,
  MoreVertical,
  Power,
  RefreshCw,
  ScrollText,
  Square,
} from "lucide-react"
import { cn } from "@/lib/utils"

export type AgentStatus = "initializing" | "idle" | "busy" | "error" | "stopping" | "stopped"

export interface Agent {
  id: string
  name: string
  type: string
  model: string
  status: AgentStatus
  currentSessionId?: string
  currentTask?: {
    id: string
    title: string
    href?: string
  }
  metrics?: {
    cpuPercent: number
    memoryMB: number
  }
  startedAt?: Date
}

interface AgentCardProps {
  agent: Agent
  onStop?: () => void
  onRestart?: () => void
  onViewLogs?: () => void
  className?: string
}

function StatusBadge({ status }: { status: AgentStatus }) {
  const statusConfig: Record<AgentStatus, { label: string; className: string; dotClassName: string }> = {
    initializing: {
      label: "Initializing",
      className: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
      dotClassName: "bg-blue-500 animate-pulse",
    },
    idle: {
      label: "Idle",
      className: "bg-green-500/10 text-green-600 dark:text-green-400",
      dotClassName: "bg-green-500",
    },
    busy: {
      label: "Busy",
      className: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400",
      dotClassName: "bg-yellow-500 animate-pulse",
    },
    error: {
      label: "Error",
      className: "bg-red-500/10 text-red-600 dark:text-red-400",
      dotClassName: "bg-red-500",
    },
    stopping: {
      label: "Stopping",
      className: "bg-orange-500/10 text-orange-600 dark:text-orange-400",
      dotClassName: "bg-orange-500 animate-pulse",
    },
    stopped: {
      label: "Stopped",
      className: "bg-slate-500/10 text-slate-600 dark:text-slate-400",
      dotClassName: "bg-slate-500",
    },
  }

  const config = statusConfig[status]

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium",
        config.className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dotClassName)} />
      {config.label}
    </span>
  )
}

function MetricBar({
  label,
  value,
  max,
  unit,
  icon: Icon,
}: {
  label: string
  value: number
  max: number
  unit: string
  icon: React.ElementType
}) {
  const percent = Math.min((value / max) * 100, 100)
  const isHigh = percent > 80

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1 text-muted-foreground">
          <Icon className="h-3 w-3" />
          {label}
        </span>
        <span className={cn("font-medium", isHigh && "text-yellow-600 dark:text-yellow-400")}>
          {value.toFixed(1)}{unit}
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            isHigh ? "bg-yellow-500" : "bg-primary"
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}

export function AgentCard({
  agent,
  onStop,
  onRestart,
  onViewLogs,
  className,
}: AgentCardProps) {
  const [menuOpen, setMenuOpen] = React.useState(false)
  const menuRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const uptime = React.useMemo(() => {
    if (!agent.startedAt) return null
    const diff = Date.now() - new Date(agent.startedAt).getTime()
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }, [agent.startedAt])

  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-4 transition-colors",
        "hover:border-primary/50 hover:shadow-sm",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-lg",
              agent.status === "error"
                ? "bg-red-500/10"
                : agent.status === "busy"
                ? "bg-yellow-500/10"
                : "bg-primary/10"
            )}
          >
            <Bot
              className={cn(
                "h-5 w-5",
                agent.status === "error"
                  ? "text-red-500"
                  : agent.status === "busy"
                  ? "text-yellow-500"
                  : "text-primary"
              )}
            />
          </div>
          <div>
            <h3 className="font-medium leading-none mb-1">{agent.name}</h3>
            <p className="text-xs text-muted-foreground">{agent.type}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge status={agent.status} />

          {/* Actions dropdown */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="p-1.5 hover:bg-accent rounded-lg transition-colors"
              aria-label="Agent actions"
            >
              <MoreVertical className="h-4 w-4 text-muted-foreground" />
            </button>

            {menuOpen && (
              <div className="absolute right-0 top-full mt-1 w-40 rounded-lg border bg-popover p-1 shadow-lg z-50">
                {onStop && (
                  <button
                    onClick={() => {
                      onStop()
                      setMenuOpen(false)
                    }}
                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
                  >
                    <Square className="h-4 w-4" />
                    Stop
                  </button>
                )}
                {onRestart && (
                  <button
                    onClick={() => {
                      onRestart()
                      setMenuOpen(false)
                    }}
                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Restart
                  </button>
                )}
                {onViewLogs && (
                  <button
                    onClick={() => {
                      onViewLogs()
                      setMenuOpen(false)
                    }}
                    className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
                  >
                    <ScrollText className="h-4 w-4" />
                    View Logs
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Model info */}
      <div className="mb-4 rounded-lg bg-muted/50 px-3 py-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Model</span>
          <span className="font-mono text-xs">{agent.model}</span>
        </div>
        {uptime && (
          <div className="flex items-center justify-between text-sm mt-1">
            <span className="text-muted-foreground">Uptime</span>
            <span className="text-xs">{uptime}</span>
          </div>
        )}
      </div>

      {/* Current task */}
      {agent.currentTask && (
        <div className="mb-4">
          <p className="text-xs text-muted-foreground mb-1">Current Task</p>
          {agent.currentTask.href ? (
            <Link
              href={agent.currentTask.href}
              className="group flex items-center gap-1 text-sm font-medium hover:text-primary transition-colors"
            >
              <span className="truncate">{agent.currentTask.title}</span>
              <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
          ) : (
            <p className="text-sm font-medium truncate">
              {agent.currentTask.title}
            </p>
          )}
        </div>
      )}

      {/* Metrics */}
      {agent.metrics && (
        <div className="space-y-3">
          <MetricBar
            label="CPU"
            value={agent.metrics.cpuPercent}
            max={100}
            unit="%"
            icon={Cpu}
          />
          <MetricBar
            label="Memory"
            value={agent.metrics.memoryMB}
            max={1024}
            unit="MB"
            icon={MemoryStick}
          />
        </div>
      )}

      {/* Quick actions */}
      <div className="mt-4 flex gap-2 border-t pt-4">
        {onStop && (
          <button
            onClick={onStop}
            disabled={agent.status === "idle"}
            className={cn(
              "flex-1 inline-flex items-center justify-center gap-1.5",
              "rounded-lg border px-3 py-1.5 text-xs font-medium",
              "hover:bg-accent transition-colors",
              "disabled:opacity-50 disabled:pointer-events-none"
            )}
          >
            <Power className="h-3 w-3" />
            Stop
          </button>
        )}
        {onRestart && (
          <button
            onClick={onRestart}
            className={cn(
              "flex-1 inline-flex items-center justify-center gap-1.5",
              "rounded-lg border px-3 py-1.5 text-xs font-medium",
              "hover:bg-accent transition-colors"
            )}
          >
            <RefreshCw className="h-3 w-3" />
            Restart
          </button>
        )}
        {onViewLogs && (
          <button
            onClick={onViewLogs}
            className={cn(
              "flex-1 inline-flex items-center justify-center gap-1.5",
              "rounded-lg border px-3 py-1.5 text-xs font-medium",
              "hover:bg-accent transition-colors"
            )}
          >
            <ScrollText className="h-3 w-3" />
            Logs
          </button>
        )}
      </div>
    </div>
  )
}
