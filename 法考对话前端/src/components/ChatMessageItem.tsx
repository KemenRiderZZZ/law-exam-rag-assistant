import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AlertCircle, Check, Copy, Loader2 } from 'lucide-react';
import { ChatMessage } from '../types';

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
        .join('  ')
    )
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function ChatMessageItem({
  message,
}: {
  message: ChatMessage;
}) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = React.useState(false);
  const [copyError, setCopyError] = React.useState('');
  const [isCopying, setIsCopying] = React.useState(false);
  const renderedContentRef = React.useRef<HTMLDivElement | null>(null);

  const handleCopy = async () => {
    if (!message.content || isCopying) return;

    setIsCopying(true);
    setCopyError('');

    const renderedText = renderedContentRef.current?.innerText?.trim();
    const textToCopy = renderedText || fallbackMarkdownToPlainText(message.content) || message.content;

    try {
      const response = await fetch('/api/copy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: textToCopy,
        }),
      });

      const payload = await response.json().catch(() => null);
      if (!response.ok || !payload?.ok) {
        throw new Error(payload?.error || `复制失败: HTTP ${response.status}`);
      }

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

  return (
    <div className={`mb-8 flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[90%] rounded-2xl p-5 shadow-sm md:max-w-[80%] ${
          isUser ? 'rounded-br-sm bg-blue-600 text-white' : 'rounded-bl-sm border border-gray-200 bg-white text-gray-800'
        }`}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
        ) : (
          <div className="flex flex-col gap-4">
            {message.status === 'searching' && (
              <div className="flex items-center gap-2 text-sm font-medium text-blue-600">
                <Loader2 size={16} className="animate-spin" />
                正在检索相关法考资料...
              </div>
            )}

            {message.status === 'generating' && (
              <div className="flex items-center gap-2 text-sm font-medium text-blue-600">
                <Loader2 size={16} className="animate-spin" />
                检索完成，正在整理答案...
              </div>
            )}

            {message.status === 'error' && (
              <div className="flex items-center gap-2 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-red-600">
                <AlertCircle size={18} />
                <span className="text-sm font-medium">错误: {message.error}</span>
              </div>
            )}

            {message.content && (
              <>
                <div
                  ref={renderedContentRef}
                  className="markdown-content break-words text-[15px] leading-[1.75] text-gray-800"
                >
                  <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
                </div>

                <div className="flex flex-col items-end gap-2 pt-1">
                  <button
                    type="button"
                    onClick={handleCopy}
                    disabled={isCopying}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:border-gray-200 disabled:bg-gray-100 disabled:text-gray-400"
                  >
                    {isCopying ? <Loader2 size={14} className="animate-spin" /> : copied ? <Check size={14} /> : <Copy size={14} />}
                    <span>{isCopying ? '复制中' : copied ? '已复制' : '复制内容'}</span>
                  </button>

                  {copyError && <div className="text-xs text-red-500">{copyError}</div>}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
