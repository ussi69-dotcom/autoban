"use client"

import { useMemo } from 'react'
import dynamic from 'next/dynamic'

import { cn } from '@/lib/utils'

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false })

const LANGUAGE_BY_EXTENSION: Record<string, string> = {
  ts: 'typescript',
  tsx: 'typescript',
  js: 'javascript',
  jsx: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  json: 'json',
  md: 'markdown',
  markdown: 'markdown',
  html: 'html',
  htm: 'html',
  css: 'css',
  scss: 'scss',
  less: 'less',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'toml',
  py: 'python',
  rb: 'ruby',
  go: 'go',
  rs: 'rust',
  java: 'java',
  kt: 'kotlin',
  swift: 'swift',
  php: 'php',
  c: 'c',
  h: 'c',
  cpp: 'cpp',
  cxx: 'cpp',
  cc: 'cpp',
  hpp: 'cpp',
  cs: 'csharp',
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  sql: 'sql',
}

function getLanguageFromPath(path?: string) {
  if (!path) {
    return 'plaintext'
  }
  const fileName = path.split('/').pop()?.toLowerCase() ?? ''
  if (fileName === 'dockerfile' || fileName.startsWith('dockerfile.')) {
    return 'dockerfile'
  }
  if (fileName === 'makefile') {
    return 'makefile'
  }
  const extension = fileName.includes('.') ? fileName.split('.').pop() : ''
  if (extension && LANGUAGE_BY_EXTENSION[extension]) {
    return LANGUAGE_BY_EXTENSION[extension]
  }
  return 'plaintext'
}

export type CodeEditorProps = {
  value: string
  language?: string
  path?: string
  onChange?: (value: string) => void
  readOnly?: boolean
  height?: string | number
  className?: string
}

export function CodeEditor({
  value,
  language,
  path,
  onChange,
  readOnly = false,
  height = '100%',
  className,
}: CodeEditorProps) {
  const resolvedLanguage = useMemo(() => language ?? getLanguageFromPath(path), [language, path])

  return (
    <div className={cn('h-full w-full', className)}>
      <MonacoEditor
        value={value}
        language={resolvedLanguage}
        height={height}
        theme="vs"
        path={path}
        loading={<div className="p-4 text-sm text-muted-foreground">Loading editor...</div>}
        onChange={(next) => onChange?.(next ?? '')}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbersMinChars: 3,
          scrollBeyondLastLine: false,
          automaticLayout: true,
        }}
      />
    </div>
  )
}
