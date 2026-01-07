"use client"

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, FileText, Folder, FolderOpen } from 'lucide-react'

import { api, type ApiResponse, type FileEntry, type FileTreeResponse } from '@/lib/api'
import { cn } from '@/lib/utils'

type FileTreeProps = {
  onSelectFile: (path: string) => void
  selectedPath?: string
  rootPath?: string
  className?: string
}

type FileTreeNodeProps = {
  entry: FileEntry
  depth: number
  onSelectFile: (path: string) => void
  selectedPath?: string
}

function resolveTreeResponse(response: ApiResponse<FileTreeResponse> | FileTreeResponse) {
  if ('data' in response) {
    return response.data
  }
  return response
}

function useFileEntries(path: string, enabled: boolean) {
  return useQuery({
    queryKey: ['files', 'list', path],
    queryFn: () => api.files.list(path || undefined),
    enabled,
    select: resolveTreeResponse,
  })
}

function FileTreeNode({ entry, depth, onSelectFile, selectedPath }: FileTreeNodeProps) {
  const isDirectory = entry.type === 'directory'
  const [isExpanded, setIsExpanded] = useState(false)
  const showToggle = isDirectory && (entry.hasChildren ?? true)
  const { data, isLoading, isError } = useFileEntries(entry.path, isDirectory && isExpanded)

  const handleClick = () => {
    if (isDirectory) {
      if (showToggle) {
        setIsExpanded((prev) => !prev)
      }
      return
    }
    onSelectFile(entry.path)
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleClick}
        className={cn(
          'flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm transition hover:bg-muted/60',
          selectedPath === entry.path && 'bg-muted text-foreground'
        )}
        style={{ paddingLeft: depth * 12 + 8 }}
        aria-expanded={isDirectory ? isExpanded : undefined}
      >
        {showToggle ? (
          isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )
        ) : (
          <span className="h-4 w-4" />
        )}
        {isDirectory ? (
          isExpanded ? (
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          ) : (
            <Folder className="h-4 w-4 text-muted-foreground" />
          )
        ) : (
          <FileText className="h-4 w-4 text-muted-foreground" />
        )}
        <span className="truncate">{entry.name}</span>
      </button>
      {isDirectory && isExpanded ? (
        <div>
          {isLoading ? (
            <div
              className="py-1 text-xs text-muted-foreground"
              style={{ paddingLeft: (depth + 1) * 12 + 8 }}
            >
              Loading...
            </div>
          ) : isError ? (
            <div
              className="py-1 text-xs text-destructive"
              style={{ paddingLeft: (depth + 1) * 12 + 8 }}
            >
              Failed to load
            </div>
          ) : (
            data?.entries.map((child) => (
              <FileTreeNode
                key={child.path}
                entry={child}
                depth={depth + 1}
                onSelectFile={onSelectFile}
                selectedPath={selectedPath}
              />
            ))
          )}
        </div>
      ) : null}
    </div>
  )
}

export function FileTree({ onSelectFile, selectedPath, rootPath = '', className }: FileTreeProps) {
  const { data, isLoading, isError } = useFileEntries(rootPath, true)

  return (
    <div className={cn('space-y-1', className)}>
      {isLoading ? (
        <div className="px-2 py-2 text-sm text-muted-foreground">Loading files...</div>
      ) : isError ? (
        <div className="px-2 py-2 text-sm text-destructive">Failed to load files</div>
      ) : (
        data?.entries.map((entry) => (
          <FileTreeNode
            key={entry.path}
            entry={entry}
            depth={0}
            onSelectFile={onSelectFile}
            selectedPath={selectedPath}
          />
        ))
      )}
    </div>
  )
}
