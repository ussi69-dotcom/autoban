'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import { KanbanBoard } from '@/components/kanban/kanban-board';
import { TaskDetailDialog } from '@/components/kanban/task-detail-dialog';
import { TaskCreateDialog } from '@/components/kanban/task-create-dialog';
import { AgentList } from '@/components/agents/agent-list';
import { IntegratedTerminal } from '@/components/terminal';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Plus,
  Settings,
  Users,
  Bot,
  Terminal,
  LayoutGrid,
  RefreshCw,
} from 'lucide-react';
import { useProject } from '@/stores/project';
import { cn } from '@/lib/utils';
import type { TaskStatus, TaskPriority } from '@/lib/api';
import type { Task } from '@/components/kanban/types';
import type { Agent } from '@/components/agents/agent-card';

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.projectId as string;

  const {
    currentProject,
    tasks,
    agents,
    isLoading,
    fetchProject,
    fetchTasks,
    fetchAgents,
    moveTask,
    createTask,
    updateTask,
    deleteTask,
  } = useProject();

  const [activeTab, setActiveTab] = useState('board');
  const [showTerminal, setShowTerminal] = useState(false);
  const [selectedAgent] = useState<Agent | null>(null);

  // Task dialog state
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isTaskDetailOpen, setIsTaskDetailOpen] = useState(false);
  const [isCreateTaskOpen, setIsCreateTaskOpen] = useState(false);
  const [createTaskInitialStatus, setCreateTaskInitialStatus] = useState<TaskStatus>('backlog');

  // Fetch project data on mount
  useEffect(() => {
    if (projectId) {
      fetchProject(projectId);
      fetchTasks(projectId);
      fetchAgents(projectId);
    }
  }, [projectId, fetchProject, fetchTasks, fetchAgents]);

  const handleTaskMove = useCallback(
    async (taskId: string, newStatus: TaskStatus, newIndex: number) => {
      await moveTask(taskId, newStatus, newIndex);
    },
    [moveTask]
  );

  // Open create dialog when clicking add button on column
  const handleAddTask = useCallback(
    (status: TaskStatus) => {
      setCreateTaskInitialStatus(status);
      setIsCreateTaskOpen(true);
    },
    []
  );

  // Handle task creation from dialog
  const handleCreateTask = useCallback(
    async (taskData: {
      title: string;
      description?: string;
      priority: TaskPriority;
      labels: string[];
      status: TaskStatus;
    }) => {
      if (!currentProject) return;

      try {
        await createTask({
          projectId: currentProject.id,
          title: taskData.title,
          description: taskData.description,
          status: taskData.status,
          priority: taskData.priority,
        });
      } catch (error) {
        console.error('Failed to create task:', error);
      }
    },
    [currentProject, createTask]
  );

  // Open task detail dialog
  const handleTaskClick = useCallback((task: Task) => {
    setSelectedTask(task);
    setIsTaskDetailOpen(true);
  }, []);

  // Handle task update from detail dialog
  const handleTaskUpdate = useCallback(
    async (taskId: string, updates: Partial<Task>) => {
      try {
        await updateTask(taskId, updates);
        // Update selectedTask if it's the one being edited
        if (selectedTask?.id === taskId) {
          setSelectedTask((prev) => prev ? { ...prev, ...updates } : null);
        }
      } catch (error) {
        console.error('Failed to update task:', error);
      }
    },
    [updateTask, selectedTask]
  );

  // Handle task delete from detail dialog
  const handleTaskDelete = useCallback(
    async (taskId: string) => {
      try {
        await deleteTask(taskId);
        setIsTaskDetailOpen(false);
        setSelectedTask(null);
      } catch (error) {
        console.error('Failed to delete task:', error);
      }
    },
    [deleteTask]
  );

  // Handle status change from detail dialog (immediate update)
  const handleTaskStatusChange = useCallback(
    async (taskId: string, newStatus: TaskStatus) => {
      try {
        await moveTask(taskId, newStatus);
        // Update selected task status
        if (selectedTask?.id === taskId) {
          setSelectedTask((prev) => prev ? { ...prev, status: newStatus } : null);
        }
      } catch (error) {
        console.error('Failed to change task status:', error);
      }
    },
    [moveTask, selectedTask]
  );

  const handleRefresh = useCallback(() => {
    if (projectId) {
      fetchTasks(projectId);
      fetchAgents(projectId);
    }
  }, [projectId, fetchTasks, fetchAgents]);

  if (isLoading && !currentProject) {
    return <ProjectPageSkeleton />;
  }

  if (!currentProject) {
    return (
      <div className="flex items-center justify-center h-full">
        <Card className="w-96">
          <CardContent className="pt-6 text-center">
            <h2 className="text-lg font-semibold mb-2">Project not found</h2>
            <p className="text-muted-foreground">
              The project you&apos;re looking for doesn&apos;t exist or you don&apos;t have access.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const totalTasks = Object.values(tasks).flat().length;
  const completedTasks = tasks.done?.length || 0;
  const activeAgents = agents.filter((a) => a.status === 'busy').length;

  return (
    <div className="flex flex-col h-full">
      {/* Project Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold">{currentProject.name}</h1>
            {currentProject.description && (
              <p className="text-sm text-muted-foreground mt-1">
                {currentProject.description}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="outline" className="flex items-center gap-1">
              <LayoutGrid className="w-3 h-3" />
              {totalTasks} tasks
            </Badge>
            <Badge variant="outline" className="flex items-center gap-1">
              <Bot className="w-3 h-3" />
              {activeAgents} active
            </Badge>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRefresh}
            title="Refresh"
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowTerminal(!showTerminal)}
          >
            <Terminal className="w-4 h-4 mr-2" />
            {showTerminal ? 'Hide' : 'Show'} Terminal
          </Button>

          <Button
            variant="default"
            size="sm"
            onClick={() => {
              setCreateTaskInitialStatus('backlog');
              setIsCreateTaskOpen(true);
            }}
          >
            <Plus className="w-4 h-4 mr-2" />
            New Task
          </Button>

          <Button variant="ghost" size="icon">
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 min-h-0">
        {/* Left Panel - Board & Content */}
        <div className={cn(
          'flex flex-col flex-1 min-w-0',
          showTerminal && 'border-r'
        )}>
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="flex flex-col h-full"
          >
            <div className="px-6 pt-4">
              <TabsList>
                <TabsTrigger value="board">
                  <LayoutGrid className="w-4 h-4 mr-2" />
                  Board
                </TabsTrigger>
                <TabsTrigger value="agents">
                  <Bot className="w-4 h-4 mr-2" />
                  Agents
                </TabsTrigger>
                <TabsTrigger value="team">
                  <Users className="w-4 h-4 mr-2" />
                  Team
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent
              value="board"
              className="flex-1 mt-0 p-6 overflow-hidden"
            >
              <KanbanBoard
                tasks={tasks}
                onTaskMove={handleTaskMove}
                onTaskClick={handleTaskClick}
                onAddTask={handleAddTask}
              />
            </TabsContent>

            <TabsContent
              value="agents"
              className="flex-1 mt-0 p-6 overflow-auto"
            >
              <div className="max-w-4xl">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Project Agents</h2>
                  <Button variant="outline" size="sm">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Agent
                  </Button>
                </div>

                <AgentList agents={agents as Agent[]} />
              </div>
            </TabsContent>

            <TabsContent value="team" className="flex-1 mt-0 p-6">
              <Card>
                <CardHeader>
                  <CardTitle>Team Members</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    Team management coming soon.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Panel - Terminal */}
        {showTerminal && (
          <div className="w-[500px] flex-shrink-0">
            <IntegratedTerminal
              sessionId={selectedAgent?.currentSessionId}
              agentId={selectedAgent?.id}
              onClose={() => setShowTerminal(false)}
              className="h-full rounded-none border-0"
            />
          </div>
        )}
      </div>

      {/* Progress Bar */}
      {totalTasks > 0 && (
        <div className="px-6 py-3 border-t bg-muted/30">
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              Progress: {completedTasks}/{totalTasks} tasks completed
            </span>
            <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-success transition-all duration-300"
                style={{ width: `${(completedTasks / totalTasks) * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium">
              {Math.round((completedTasks / totalTasks) * 100)}%
            </span>
          </div>
        </div>
      )}

      {/* Task Create Dialog */}
      <TaskCreateDialog
        open={isCreateTaskOpen}
        onOpenChange={setIsCreateTaskOpen}
        onSubmit={handleCreateTask}
        initialStatus={createTaskInitialStatus}
      />

      {/* Task Detail Dialog */}
      <TaskDetailDialog
        open={isTaskDetailOpen}
        onOpenChange={setIsTaskDetailOpen}
        task={selectedTask}
        agents={agents.map((a) => ({ id: a.id, name: a.name }))}
        onUpdate={handleTaskUpdate}
        onDelete={handleTaskDelete}
        onStatusChange={handleTaskStatusChange}
      />
    </div>
  );
}

function ProjectPageSkeleton() {
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div className="flex items-center gap-4">
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64 mt-2" />
          </div>
        </div>
        <div className="flex gap-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-24" />
        </div>
      </div>

      <div className="flex-1 p-6">
        <div className="flex gap-4 h-full">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex-1">
              <Skeleton className="h-8 w-24 mb-4" />
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
