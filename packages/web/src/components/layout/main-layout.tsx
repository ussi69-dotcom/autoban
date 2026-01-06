"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Sidebar } from "./sidebar"
import { Header } from "./header"

interface Project {
  id: string
  name: string
}

interface BreadcrumbItem {
  label: string
  href?: string
}

interface MainLayoutProps {
  children: React.ReactNode
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
  className?: string
}

export function MainLayout({
  children,
  breadcrumbs = [],
  projects = [],
  currentProject = null,
  onProjectChange,
  user,
  notificationCount = 0,
  className,
}: MainLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = React.useState(false)

  // Close sidebar on route change (mobile)
  React.useEffect(() => {
    setSidebarOpen(false)
  }, [])

  // Handle escape key to close sidebar
  React.useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && sidebarOpen) {
        setSidebarOpen(false)
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [sidebarOpen])

  // Prevent body scroll when sidebar is open on mobile
  React.useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
    return () => {
      document.body.style.overflow = ""
    }
  }, [sidebarOpen])

  const toggleSidebar = () => setSidebarOpen((prev) => !prev)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <Sidebar
        projects={projects}
        user={user}
        isOpen={sidebarOpen}
        onToggle={toggleSidebar}
      />

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <Header
          breadcrumbs={breadcrumbs}
          projects={projects}
          currentProject={currentProject}
          onProjectChange={onProjectChange}
          user={user}
          notificationCount={notificationCount}
          onSidebarToggle={toggleSidebar}
        />

        {/* Page content */}
        <main
          className={cn(
            "flex-1 overflow-y-auto",
            "p-4 md:p-6 lg:p-8",
            className
          )}
        >
          {children}
        </main>
      </div>
    </div>
  )
}

// Convenience wrapper for page content with max-width
export function PageContainer({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("mx-auto w-full max-w-7xl", className)}>{children}</div>
  )
}

// Page header component for consistent page titles
export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: string
  description?: string
  actions?: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between",
        className
      )}
    >
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">
          {title}
        </h1>
        {description && (
          <p className="mt-1 text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
