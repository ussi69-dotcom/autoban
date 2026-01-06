"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useMemo } from "react";
import {
  useProjects,
  useCreateProject,
  type Project,
  type Task,
} from "@/hooks/use-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Plus, AlertCircle } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();

  // Fetch projects directly (backend returns user's projects)
  const {
    data: projects,
    isLoading: projectsLoading,
    error: projectsError,
  } = useProjects();

  // For now, we don't fetch tasks/agents on dashboard (simplify)
  // The project cards will show task_count from the backend response
  const allTasks: Task[] = [];
  const allAgents: { id: string; name: string; status: string; projectId: string }[] = [];

  // Get recent tasks (sorted by updatedAt)
  const recentTasks = useMemo(() => {
    return [...allTasks]
      .sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      )
      .slice(0, 5);
  }, [allTasks]);

  // Calculate stats
  const stats = useMemo(() => {
    const totalProjects = projects?.length ?? 0;
    const activeTasks = allTasks.filter(
      (t) => t.status === "in_progress" || t.status === "in_review"
    ).length;
    const activeAgents = allAgents.filter(
      (a) => a.status === "busy" || a.status === "idle"
    ).length;
    const completedTasks = allTasks.filter((t) => t.status === "done").length;
    const totalTasks = allTasks.length;
    const completionRate =
      totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

    return { totalProjects, activeTasks, activeAgents, completionRate };
  }, [projects, allTasks, allAgents]);

  // Use project data with stats from backend
  // Backend returns task_count and active_agent_count directly
  const projectsWithStats = useMemo(() => {
    if (!projects) return [];

    return projects.map((project: Project & { task_count?: number; active_agent_count?: number }) => ({
      ...project,
      tasksCount: project.task_count ?? 0,
      completedTasks: 0, // Would need to fetch tasks to get this
      agentsActive: project.active_agent_count ?? 0,
    }));
  }, [projects]);

  // Create project modal state
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDescription, setNewProjectDescription] = useState("");

  const createProject = useCreateProject();

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newProjectName.trim()) return;

    try {
      const result = await createProject.mutateAsync({
        name: newProjectName.trim(),
        description: newProjectDescription.trim() || undefined,
      });

      setIsCreateDialogOpen(false);
      setNewProjectName("");
      setNewProjectDescription("");

      // Backend returns ProjectResponse directly, not { data: ProjectResponse }
      const projectId = (result as unknown as { id: string }).id || result?.data?.id;
      if (projectId) {
        router.push(`/projects/${projectId}`);
      }
    } catch (error) {
      console.error("Failed to create project:", error);
    }
  };

  const isLoading = projectsLoading;
  const error = projectsError;

  // Show loading state
  if (isLoading) {
    return <DashboardSkeleton />;
  }

  // Show error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold mb-2">Failed to load dashboard</h2>
        <p className="text-muted-foreground mb-4">
          {error instanceof Error ? error.message : "An error occurred"}
        </p>
        <Button onClick={() => window.location.reload()}>Try Again</Button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="mt-2 text-muted-foreground">
            Welcome back! Here&apos;s an overview of your projects and agents.
          </p>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={handleCreateProject}>
              <DialogHeader>
                <DialogTitle>Create New Project</DialogTitle>
                <DialogDescription>
                  Create a new project to organize your tasks and agents.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">Project Name</Label>
                  <Input
                    id="name"
                    placeholder="My Awesome Project"
                    value={newProjectName}
                    onChange={(e) => setNewProjectName(e.target.value)}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="description">Description (optional)</Label>
                  <Textarea
                    id="description"
                    placeholder="A brief description of your project..."
                    value={newProjectDescription}
                    onChange={(e) => setNewProjectDescription(e.target.value)}
                    rows={3}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!newProjectName.trim() || createProject.isPending}
                >
                  {createProject.isPending ? "Creating..." : "Create Project"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          title="Total Projects"
          value={stats.totalProjects.toString()}
          icon={<ProjectIcon />}
        />
        <StatCard
          title="Active Tasks"
          value={stats.activeTasks.toString()}
          icon={<TaskIcon />}
        />
        <StatCard
          title="Active Agents"
          value={stats.activeAgents.toString()}
          icon={<AgentIcon />}
        />
        <StatCard
          title="Completion Rate"
          value={`${stats.completionRate}%`}
          icon={<ChartIcon />}
        />
      </div>

      {/* Projects Section */}
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Projects</h2>
          <Link href="/projects" className="text-sm text-primary hover:underline">
            View all
          </Link>
        </div>
        {projectsWithStats.length === 0 ? (
          <EmptyProjectsState onCreateClick={() => setIsCreateDialogOpen(true)} />
        ) : (
          <div className="grid gap-4 md:grid-cols-3">
            {projectsWithStats.slice(0, 3).map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </section>

      {/* Two Column Layout: Recent Tasks & Agent Status */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Tasks */}
        <section>
          <h2 className="mb-4 text-xl font-semibold">Recent Tasks</h2>
          <div className="rounded-lg border border-border/50 bg-card">
            {recentTasks.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                No tasks yet. Create a project and add some tasks!
              </div>
            ) : (
              <div className="divide-y divide-border/50">
                {recentTasks.map((task) => (
                  <TaskRow
                    key={task.id}
                    task={task}
                    projectName={
                      projects?.find((p) => p.id === task.projectId)?.name ?? ""
                    }
                  />
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Agent Status */}
        <section>
          <h2 className="mb-4 text-xl font-semibold">Agent Status</h2>
          <div className="rounded-lg border border-border/50 bg-card">
            {allAgents.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                No agents configured. Add agents to your projects!
              </div>
            ) : (
              <div className="divide-y divide-border/50">
                {allAgents.slice(0, 4).map((agent) => (
                  <AgentRow
                    key={agent.id}
                    agent={agent}
                    projectName={
                      projects?.find((p) => p.id === agent.projectId)?.name ?? ""
                    }
                  />
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

// Loading Skeleton
function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <div>
        <Skeleton className="h-9 w-48" />
        <Skeleton className="mt-2 h-5 w-96" />
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-28 rounded-lg" />
        ))}
      </div>

      <section>
        <Skeleton className="mb-4 h-7 w-24" />
        <div className="grid gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48 rounded-lg" />
          ))}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <Skeleton className="mb-4 h-7 w-32" />
          <Skeleton className="h-64 rounded-lg" />
        </section>
        <section>
          <Skeleton className="mb-4 h-7 w-32" />
          <Skeleton className="h-64 rounded-lg" />
        </section>
      </div>
    </div>
  );
}

// Empty state for no projects
function EmptyProjectsState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <div className="rounded-lg border border-dashed border-border/50 bg-card p-12 text-center">
      <ProjectIcon className="mx-auto h-12 w-12 text-muted-foreground" />
      <h3 className="mt-4 text-lg font-semibold">No projects yet</h3>
      <p className="mt-2 text-sm text-muted-foreground">
        Get started by creating your first project.
      </p>
      <Button className="mt-4" onClick={onCreateClick}>
        <Plus className="mr-2 h-4 w-4" />
        Create Project
      </Button>
    </div>
  );
}

// Components
function StatCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border/50 bg-card p-6">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <div className="text-muted-foreground">{icon}</div>
      </div>
      <p className="mt-2 text-3xl font-bold">{value}</p>
    </div>
  );
}

interface ProjectWithStats extends Project {
  tasksCount: number;
  completedTasks: number;
  agentsActive: number;
}

function ProjectCard({ project }: { project: ProjectWithStats }) {
  const progress =
    project.tasksCount > 0
      ? Math.round((project.completedTasks / project.tasksCount) * 100)
      : 0;

  return (
    <Link
      href={`/projects/${project.id}`}
      className="block rounded-lg border border-border/50 bg-card p-6 transition-shadow hover:shadow-md"
    >
      <h3 className="text-lg font-semibold">{project.name}</h3>
      <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
        {project.description || "No description"}
      </p>

      {/* Progress Bar */}
      <div className="mt-4">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Progress</span>
          <span className="font-medium">{progress}%</span>
        </div>
        <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Stats */}
      <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
        <span>
          {project.completedTasks}/{project.tasksCount} tasks
        </span>
        <span>{project.agentsActive} agents active</span>
      </div>
    </Link>
  );
}

function TaskRow({
  task,
  projectName,
}: {
  task: Task;
  projectName: string;
}) {
  const statusColors: Record<string, string> = {
    backlog: "bg-muted text-muted-foreground",
    todo: "bg-blue-500/10 text-blue-500",
    in_progress: "bg-primary/10 text-primary",
    in_review: "bg-yellow-500/10 text-yellow-500",
    done: "bg-green-500/10 text-green-500",
    cancelled: "bg-destructive/10 text-destructive",
  };

  const statusLabels: Record<string, string> = {
    backlog: "Backlog",
    todo: "Todo",
    in_progress: "In Progress",
    in_review: "In Review",
    done: "Done",
    cancelled: "Cancelled",
  };

  return (
    <div className="flex items-center justify-between p-4">
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{task.title}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {projectName}
          {task.assignedAgentId && ` - Agent assigned`}
        </p>
      </div>
      <span
        className={`ml-4 rounded-full px-2.5 py-0.5 text-xs font-medium ${
          statusColors[task.status] || statusColors.backlog
        }`}
      >
        {statusLabels[task.status] || task.status}
      </span>
    </div>
  );
}

function AgentRow({
  agent,
  projectName,
}: {
  agent: {
    id: string;
    name: string;
    status: string;
    currentTaskId?: string;
    projectId: string;
  };
  projectName: string;
}) {
  const statusColors: Record<string, string> = {
    initializing: "bg-blue-500",
    idle: "bg-muted-foreground",
    busy: "bg-green-500",
    error: "bg-destructive",
    stopping: "bg-yellow-500",
    stopped: "bg-muted-foreground",
  };

  const statusLabels: Record<string, string> = {
    initializing: "Initializing",
    idle: "Idle",
    busy: "Working",
    error: "Error",
    stopping: "Stopping",
    stopped: "Stopped",
  };

  return (
    <div className="flex items-center gap-4 p-4">
      <div
        className={`h-2.5 w-2.5 rounded-full ${
          statusColors[agent.status] || statusColors.idle
        }`}
      />
      <div className="min-w-0 flex-1">
        <p className="font-medium">{agent.name}</p>
        <p className="mt-0.5 truncate text-sm text-muted-foreground">
          {statusLabels[agent.status] || agent.status}
        </p>
      </div>
      <span className="text-sm text-muted-foreground">{projectName}</span>
    </div>
  );
}

// Icons
function ProjectIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className || "h-5 w-5"}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
      />
    </svg>
  );
}

function TaskIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
      />
    </svg>
  );
}

function AgentIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
      />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
      />
    </svg>
  );
}
