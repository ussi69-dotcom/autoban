"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  FolderKanban,
  Bot,
  Settings,
  ChevronDown,
  ChevronRight,
  LogOut,
  User,
  Menu,
  X,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface Project {
  id: string
  name: string
}

interface SidebarProps {
  projects?: Project[]
  user?: {
    name: string
    email: string
    avatar?: string
  }
  isOpen?: boolean
  onToggle?: () => void
}

interface NavItemProps {
  href: string
  icon: React.ReactNode
  label: string
  isActive?: boolean
  children?: React.ReactNode
  isExpanded?: boolean
  onToggle?: () => void
}

function NavItem({
  href,
  icon,
  label,
  isActive,
  children,
  isExpanded,
  onToggle,
}: NavItemProps) {
  const hasChildren = Boolean(children)

  return (
    <div>
      <div className="flex items-center">
        <Link
          href={href}
          className={cn(
            "flex flex-1 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
            "hover:bg-accent hover:text-accent-foreground",
            isActive
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground"
          )}
        >
          {icon}
          <span>{label}</span>
        </Link>
        {hasChildren && (
          <button
            onClick={onToggle}
            className="p-2 hover:bg-accent rounded-lg transition-colors"
            aria-label={isExpanded ? "Collapse" : "Expand"}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
          </button>
        )}
      </div>
      {hasChildren && isExpanded && (
        <div className="ml-6 mt-1 space-y-1">{children}</div>
      )}
    </div>
  )
}

export function Sidebar({ projects = [], user, isOpen = true, onToggle }: SidebarProps) {
  const pathname = usePathname()
  const [projectsExpanded, setProjectsExpanded] = React.useState(true)

  const navItems = [
    {
      href: "/dashboard",
      icon: <LayoutDashboard className="h-5 w-5" />,
      label: "Dashboard",
    },
    {
      href: "/projects",
      icon: <FolderKanban className="h-5 w-5" />,
      label: "Projects",
      hasChildren: true,
    },
    {
      href: "/agents",
      icon: <Bot className="h-5 w-5" />,
      label: "Agents",
    },
    {
      href: "/settings",
      icon: <Settings className="h-5 w-5" />,
      label: "Settings",
    },
  ]

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm lg:hidden"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r bg-background transition-transform duration-300 lg:static lg:translate-x-0",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Bot className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-bold">AutoBan</span>
          </Link>
          <button
            onClick={onToggle}
            className="p-2 hover:bg-accent rounded-lg transition-colors lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto p-4">
          {navItems.map((item) => (
            <NavItem
              key={item.href}
              href={item.href}
              icon={item.icon}
              label={item.label}
              isActive={pathname === item.href || pathname.startsWith(item.href + "/")}
              isExpanded={item.hasChildren ? projectsExpanded : undefined}
              onToggle={item.hasChildren ? () => setProjectsExpanded(!projectsExpanded) : undefined}
            >
              {item.hasChildren && projects.length > 0 && (
                <>
                  {projects.map((project) => (
                    <Link
                      key={project.id}
                      href={`/projects/${project.id}`}
                      className={cn(
                        "block rounded-lg px-3 py-2 text-sm transition-colors",
                        "hover:bg-accent hover:text-accent-foreground",
                        pathname === `/projects/${project.id}`
                          ? "bg-accent/50 text-accent-foreground"
                          : "text-muted-foreground"
                      )}
                    >
                      {project.name}
                    </Link>
                  ))}
                </>
              )}
            </NavItem>
          ))}
        </nav>

        {/* User info */}
        {user && (
          <div className="border-t p-4">
            <div className="flex items-center gap-3 rounded-lg p-2 hover:bg-accent transition-colors cursor-pointer">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-muted">
                {user.avatar ? (
                  <img
                    src={user.avatar}
                    alt={user.name}
                    className="h-9 w-9 rounded-full object-cover"
                  />
                ) : (
                  <User className="h-5 w-5 text-muted-foreground" />
                )}
              </div>
              <div className="flex-1 overflow-hidden">
                <p className="truncate text-sm font-medium">{user.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {user.email}
                </p>
              </div>
              <button
                className="p-1.5 hover:bg-background rounded transition-colors"
                aria-label="Logout"
              >
                <LogOut className="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
          </div>
        )}
      </aside>
    </>
  )
}

export function SidebarTrigger({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="p-2 hover:bg-accent rounded-lg transition-colors lg:hidden"
      aria-label="Open sidebar"
    >
      <Menu className="h-5 w-5" />
    </button>
  )
}
