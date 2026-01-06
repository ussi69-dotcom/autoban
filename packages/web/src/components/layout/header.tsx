"use client"

import * as React from "react"
import Link from "next/link"
import {
  Bell,
  ChevronDown,
  ChevronRight,
  LogOut,
  Search,
  Settings,
  User,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { SidebarTrigger } from "./sidebar"

interface Project {
  id: string
  name: string
}

interface BreadcrumbItem {
  label: string
  href?: string
}

interface HeaderProps {
  breadcrumbs?: BreadcrumbItem[]
  projects?: Project[]
  currentProject?: Project | null
  onProjectChange?: (project: Project) => void
  user?: {
    name: string
    email: string
    avatar?: string
  }
  notificationCount?: number
  onSidebarToggle?: () => void
}

function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav className="flex items-center space-x-1 text-sm">
      {items.map((item, index) => (
        <React.Fragment key={index}>
          {index > 0 && (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
          {item.href ? (
            <Link
              href={item.href}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {item.label}
            </Link>
          ) : (
            <span className="font-medium text-foreground">{item.label}</span>
          )}
        </React.Fragment>
      ))}
    </nav>
  )
}

function ProjectSelector({
  projects,
  currentProject,
  onProjectChange,
}: {
  projects: Project[]
  currentProject: Project | null
  onProjectChange?: (project: Project) => void
}) {
  const [isOpen, setIsOpen] = React.useState(false)
  const dropdownRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  if (!currentProject) return null

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm",
          "hover:bg-accent transition-colors"
        )}
      >
        <span className="max-w-[150px] truncate">{currentProject.name}</span>
        <ChevronDown className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-56 rounded-lg border bg-popover p-1 shadow-lg z-50">
          {projects.map((project) => (
            <button
              key={project.id}
              onClick={() => {
                onProjectChange?.(project)
                setIsOpen(false)
              }}
              className={cn(
                "flex w-full items-center rounded-md px-3 py-2 text-sm transition-colors",
                "hover:bg-accent",
                project.id === currentProject.id && "bg-accent"
              )}
            >
              {project.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function SearchInput() {
  const [value, setValue] = React.useState("")

  return (
    <div className="relative hidden md:block">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <input
        type="text"
        placeholder="Search..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className={cn(
          "h-9 w-64 rounded-lg border bg-background pl-9 pr-4 text-sm",
          "placeholder:text-muted-foreground",
          "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
          "dark:bg-muted/50"
        )}
      />
      <kbd className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
        <span className="text-xs">Ctrl</span>K
      </kbd>
    </div>
  )
}

function NotificationBell({ count = 0 }: { count?: number }) {
  return (
    <button
      className="relative p-2 hover:bg-accent rounded-lg transition-colors"
      aria-label="Notifications"
    >
      <Bell className="h-5 w-5" />
      {count > 0 && (
        <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
          {count > 9 ? "9+" : count}
        </span>
      )}
    </button>
  )
}

function UserMenu({
  user,
}: {
  user: { name: string; email: string; avatar?: string }
}) {
  const [isOpen, setIsOpen] = React.useState(false)
  const dropdownRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-lg p-1.5 hover:bg-accent transition-colors"
      >
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
          {user.avatar ? (
            <img
              src={user.avatar}
              alt={user.name}
              className="h-8 w-8 rounded-full object-cover"
            />
          ) : (
            <User className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
        <ChevronDown className={cn("h-4 w-4 hidden sm:block transition-transform", isOpen && "rotate-180")} />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-1 w-56 rounded-lg border bg-popover p-1 shadow-lg z-50">
          <div className="border-b px-3 py-2 mb-1">
            <p className="text-sm font-medium">{user.name}</p>
            <p className="text-xs text-muted-foreground">{user.email}</p>
          </div>

          <Link
            href="/profile"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            <User className="h-4 w-4" />
            Profile
          </Link>

          <Link
            href="/settings"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            <Settings className="h-4 w-4" />
            Settings
          </Link>

          <div className="border-t mt-1 pt-1">
            <button
              className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors"
              onClick={() => {
                // Handle logout
                setIsOpen(false)
              }}
            >
              <LogOut className="h-4 w-4" />
              Logout
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export function Header({
  breadcrumbs = [],
  projects = [],
  currentProject = null,
  onProjectChange,
  user,
  notificationCount = 0,
  onSidebarToggle,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 lg:px-6">
      <div className="flex items-center gap-4">
        {onSidebarToggle && <SidebarTrigger onClick={onSidebarToggle} />}

        {breadcrumbs.length > 0 && <Breadcrumbs items={breadcrumbs} />}

        {projects.length > 0 && currentProject && (
          <ProjectSelector
            projects={projects}
            currentProject={currentProject}
            onProjectChange={onProjectChange}
          />
        )}
      </div>

      <div className="flex items-center gap-2">
        <SearchInput />
        <NotificationBell count={notificationCount} />
        {user && <UserMenu user={user} />}
      </div>
    </header>
  )
}
