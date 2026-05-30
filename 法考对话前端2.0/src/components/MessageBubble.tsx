import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AlertCircle, ChevronDown, ChevronRight, FileText, Loader2, Copy, Check } from 'lucide-react';
import { Message } from '../types';
import { cn } from '../lib/utils';
import { copyText } from '../lib/copy';

interface MessageBubbleProps {
  message: Message;
  activeReferenceId: string | null;
  onReferenceClick: (refId: string) => void;
}

function fallbackMarkdownToPlainText(markdown: string) {
  return markdown
    .replace(/\r\n/g, '\n')
    .replace(/```[\s\S]*?```/g, (block) => block.replace(/```[^\n]*\n?|\n?```/g, ''))
    .replace(/^\s*[-*_]{3,}\s*$/gm, '')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    .replace(/^\s*[-*+]\s+\[(?: |x|X)\]\s+/gm, '• ')
    .replace(/^\s*[-*+]\s+/gm, '• ')
    .replace(/^\s*(\d+)\.\s+/gm, '$1. ')
    .replace(/^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$/gm, '')
    .replace(/^\s*\|(.+)\|\s*$/gm, (_, cells: string) =>
      cells
        .split('|')
        .map((cell) => cell.trim())
        .filter(Boolean)
        .join('  '),
    )
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function MessageBubble({ message, activeReferenceId, onReferenceClick }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [isThinkingExpanded, setIsThinkingExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState('');
  const [isCopying, setIsCopying] = useState(false);
  const renderedContentRef = React.useRef<HTMLDivElement | null>(null);

  const handleCopy = async () => {
    if (!message.content || isCopying) return;

    setIsCopying(true);
    setCopyError('');

    const renderedText = renderedContentRef.current?.innerText?.trim();
    const textToCopy = renderedText || fallbackMarkdownToPlainText(message.content) || message.content;

    try {
      await copyText(textToCopy);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch (error) {
      const messageText = error instanceof Error ? error.message : '复制失败，请稍后重试';
      setCopied(false);
      setCopyError(messageText);
    } finally {
      setIsCopying(false);
    }
  };

  const components = {
    code({ inline, className, children, ...props }: any) {
      const match = /\[(\d+)\]/.exec(String(children || ''));
      if (inline && match && message.references) {
        const refId = match[1];
        const isActive = activeReferenceId === refId;
        return (
          <button
            onClick={() => onReferenceClick(refId)}
            className={cn(
              'relative -top-1 mx-0.5 inline-flex items-center justify-center rounded-sm border px-1.5 py-0.5 text-[10px] font-bold transition-colors',
              isActive ? 'border-blue-600 bg-blue-600 text-white shadow-sm' : 'border-blue-200 bg-white text-blue-600 hover:bg-blue-50',
            )}
            title="查看引用详情"
          >
            {refId}
          </button>
        );
      }
      return (
        <code className={cn('rounded bg-slate-100 px-1.5 py-0.5 font-mono text-sm text-pink-600', className)} {...props}>
          {children}
        </code>
      );
    },
    h3: ({ ...props }: any) => <h3 className="mb-3 mt-6 border-b pb-2 text-base font-bold text-slate-800" {...props} />,
    h4: ({ ...props }: any) => <h4 className="mb-2 mt-5 text-sm font-bold text-slate-800" {...props} />,
    p: ({ ...props }: any) => <p className="mb-3 text-sm leading-relaxed text-slate-700" {...props} />,
    ol: ({ ...props }: any) => <ol className="mb-4 ml-5 list-decimal space-y-2 text-sm text-slate-700" {...props} />,
    ul: ({ ...props }: any) => <ul className="mb-4 ml-5 list-disc space-y-2 text-sm text-slate-700" {...props} />,
    li: ({ ...props }: any) => <li className="leading-relaxed" {...props} />,
    strong: ({ ...props }: any) => <strong className="rounded-sm bg-blue-50 px-1 font-semibold text-slate-900" {...props} />,
  };

  if (isUser) {
    return (
      <div className="flex w-full justify-end">
        <div className="max-w-[80%] whitespace-pre-wrap rounded-2xl rounded-tr-sm bg-blue-600 p-4 text-sm leading-relaxed text-white shadow-md">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex w-full justify-start">
      <div className="group flex w-full max-w-3xl flex-col gap-3">
        <div className="mb-0.5 flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-800 text-[10px] font-bold text-white">AI</div>
          <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">
            {message.thinking ? 'Thinking Process & Answer' : 'Assistant'}
          </span>
        </div>

        {message.status === 'searching' && (
          <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700">
            <Loader2 className="h-4 w-4 animate-spin" />
            正在检索本地法考知识库...
          </div>
        )}

        {message.status === 'generating' && (
          <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-medium text-blue-700">
            <Loader2 className="h-4 w-4 animate-spin" />
            检索完成，正在整理答案...
          </div>
        )}

        {message.status === 'error' && (
          <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">
            <AlertCircle className="h-4 w-4" />
            <span>{message.error || '系统异常'}</span>
          </div>
        )}

        {(message.thinking || message.content) && (
          <div className="flex min-w-0 flex-col gap-2">
            {message.thinking && (
              <div className="overflow-hidden rounded-2xl rounded-tl-sm border border-slate-200 bg-slate-50 transition-all">
                <button
                  onClick={() => setIsThinkingExpanded((previous) => !previous)}
                  className="flex w-full items-center justify-between px-4 py-3 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-100"
                >
                  <div className="flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500"></span>
                    </span>
                    考点检索与分析思路
                  </div>
                  {isThinkingExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                </button>
                {isThinkingExpanded && (
                  <div className="border-t border-slate-100 px-4 pb-4">
                    <div className="whitespace-pre-wrap pt-3 font-mono text-xs leading-relaxed text-slate-600">{message.thinking}</div>
                  </div>
                )}
              </div>
            )}

            {message.content && (
              <>
                <div className="relative w-full rounded-2xl rounded-tl-sm border border-slate-200 bg-white p-6 shadow-sm">
                  <div ref={renderedContentRef} className="prose prose-sm prose-slate max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components as any}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={handleCopy}
                    disabled={isCopying}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
                  >
                    {isCopying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>{isCopying ? '复制中' : copied ? '已复制' : '复制内容'}</span>
                  </button>

                  {copyError && <div className="text-xs text-red-500">{copyError}</div>}
                </div>
              </>
            )}

            {message.references && message.references.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-2">
                {message.references.map((reference) => (
                  <button
                    key={reference.id}
                    onClick={() => onReferenceClick(reference.id)}
                    className={cn(
                      'flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                      activeReferenceId === reference.id
                        ? 'border-blue-200 bg-blue-50 text-blue-700'
                        : 'border-slate-200 bg-white text-slate-500 hover:border-blue-300 hover:bg-slate-50 hover:text-blue-600',
                    )}
                  >
                    <FileText className="h-3 w-3" />
                    {`${reference.title || '法条依据'} [${reference.id}]`}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


