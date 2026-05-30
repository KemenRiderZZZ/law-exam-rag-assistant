import React, { useEffect, useRef, useState } from 'react';
import { BarChart3, CheckCircle2, Loader2, Menu, Network, Scale, Send, Server, XCircle } from 'lucide-react';
import { AppSettings, Message } from '../types';
import { MessageBubble } from './MessageBubble';
import { QuickActions } from './QuickActions';
import { MindmapModal } from './MindmapModal';
import { cn } from '../lib/utils';
import { runChatTurn } from '../lib/chatEngine';
import { generateMindmap } from '../lib/mindmap';

interface ChatAreaProps {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  activeReferenceId: string | null;
  onReferenceClick: (refId: string) => void;
  settings: AppSettings;
  health: 'checking' | 'ok' | 'error';
  onOpenSidebar: () => void;
  onOpenAnnouncement: () => void;
}

interface ChatHeaderProps {
  health: ChatAreaProps['health'];
  onOpenSidebar: () => void;
  onOpenAnnouncement: () => void;
}

type TrafficSummary = {
  ok: boolean;
  date: string;
  searchCount: number;
  chatCount: number;
  mindmapCount: number;
};

interface MindmapIntroProps {
  onPickPrompt: (text: string) => void;
}

interface MessageListProps {
  messages: Message[];
  activeReferenceId: string | null;
  onReferenceClick: (refId: string) => void;
  onQuickAction: (text: string) => void;
  showQuickActions: boolean;
  bottomRef: React.RefObject<HTMLDivElement | null>;
}

interface ComposerProps {
  input: string;
  placeholder: string;
  isBusy: boolean;
  isMindmapMode: boolean;
  isGeneratingMindmap: boolean;
  mindmapError: string;
  onInputChange: (value: string) => void;
  onKeyDown: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  onSubmit: (event?: React.FormEvent) => void;
  onGenerateMindmap: () => void;
}

const floatingActionButtonClass =
  'flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-white transition-all md:h-[74px] md:w-14';

const mindmapExamples = [
  '帮我梳理民法中的表见代理',
  '帮我梳理刑法中的共同犯罪',
  '帮我梳理民诉中的一审普通程序',
];

function getInputPlaceholder(isMindmapMode: boolean) {
  return isMindmapMode
    ? '输入知识点、考点框架或题目，生成思维导图...'
    : '粘贴历年真题，或输入你要解析的题目...';
}

function getAssistantThinkingText() {
  return '正在检索本地法考知识库并组织回答...';
}

function getFooterHint(isMindmapMode: boolean) {
  return isMindmapMode
    ? 'Enter 生成导图 · Shift + Enter 换行 · 支持基于最近一轮答案生成 Markmap'
    : 'Enter 发送 · Shift + Enter 换行 · 系统会先检索本地法考知识库，再组织回答';
}

function UsageStatsBadge() {
  const [summary, setSummary] = useState<TrafficSummary | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadSummary = async () => {
      try {
        const response = await fetch('/api/traffic-summary', { cache: 'no-store' });
        const payload = (await response.json()) as TrafficSummary;
        if (isMounted && response.ok && payload.ok) {
          setSummary(payload);
        }
      } catch {
        if (isMounted) {
          setSummary(null);
        }
      }
    };

    loadSummary();
    const timer = window.setInterval(loadSummary, 60_000);
    return () => {
      isMounted = false;
      window.clearInterval(timer);
    };
  }, []);

  if (!summary) {
    return null;
  }

  return (
    <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-[11px] text-slate-500 lg:flex">
      <BarChart3 className="h-3.5 w-3.5 text-slate-400" />
      <span>今日</span>
      <span>搜索 {summary.searchCount}</span>
      <span>聊天 {summary.chatCount}</span>
      <span>导图 {summary.mindmapCount}</span>
    </div>
  );
}

function ChatHeader({ health, onOpenSidebar, onOpenAnnouncement }: ChatHeaderProps) {
  return (
    <header className="flex shrink-0 flex-col gap-2 border-b border-slate-200 bg-white px-3 py-2.5 md:h-14 md:flex-row md:items-center md:justify-between md:gap-0 md:px-6 md:py-0">
      <div className="flex min-w-0 items-center gap-3 md:gap-4">
        <button
          type="button"
          onClick={onOpenSidebar}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-500 transition-colors hover:bg-slate-50 hover:text-slate-800"
          title="打开侧边栏"
        >
          <Menu className="h-5 w-5" />
        </button>

        <h1 className="min-w-0 truncate text-[13px] font-semibold tracking-tight text-slate-800 md:text-sm">
          法考智学 V2
          <span className="ml-2 hidden text-xs font-normal text-slate-400 sm:inline">本地知识库 + 大模型</span>
        </h1>

        <div className="hidden h-4 w-px bg-slate-200 md:block"></div>

        <div className="flex min-w-0 items-center gap-2">
          <Server className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span className="truncate text-xs font-mono text-slate-500">Local Search</span>

          {health === 'checking' && (
            <span className="flex items-center gap-1 text-xs text-amber-600">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              检测中
            </span>
          )}

          {health === 'ok' && (
            <span className="flex items-center gap-1 text-xs text-emerald-600">
              <CheckCircle2 className="h-3.5 w-3.5" />
              正常
            </span>
          )}

          {health === 'error' && (
            <span className="flex items-center gap-1 text-xs text-red-500">
              <XCircle className="h-3.5 w-3.5" />
              无法访问
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center justify-end gap-3">
        <UsageStatsBadge />
        <button type="button" onClick={onOpenAnnouncement} className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] text-slate-600 hover:bg-slate-50 md:text-xs">
          公告
        </button>
      </div>
    </header>
  );
}

function MindmapIntro({ onPickPrompt }: MindmapIntroProps) {
  return (
    <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col justify-center px-0 py-2 md:p-6">
      <div className="rounded-[1.6rem] border border-slate-200 bg-white p-4 shadow-sm md:rounded-[2rem] md:p-8">
        <div className="mb-4 flex items-start gap-3 md:mb-6 md:items-center">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 md:h-12 md:w-12">
            <Network className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-800">思维导图生成</h2>
            <p className="mt-1 text-sm leading-6 text-slate-500">
              侧边栏默认隐藏，点左上角按钮再展开。进入这里后，你可以基于当前输入内容或上一轮答案，生成符合 Markmap Markdown 格式的思维导图。
            </p>
          </div>
        </div>

        <div className="grid gap-3 md:gap-4 md:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 md:p-5">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">使用方式</h3>
            <p className="text-sm leading-7 text-slate-500">
              先输入一个法考知识点、题目或结构框架，再点击“生成思维导图”。如果前面已经有回答，也会优先结合最近一轮答案生成。
            </p>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 md:p-5">
            <h3 className="mb-2 text-sm font-semibold text-slate-700">输出结果</h3>
            <p className="text-sm leading-7 text-slate-500">
              生成后会弹出预览窗口，左侧是 Markmap 预览，右侧是 Markdown 源码，方便你继续修改或发到别处使用。
            </p>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-2.5 md:mt-6 md:gap-3">
          {mindmapExamples.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => onPickPrompt(example)}
              className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-[11px] font-medium text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 md:px-4 md:text-xs"
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function EmptyChatState({ onPickPrompt }: { onPickPrompt: (text: string) => void }) {
  return (
    <div className="mx-auto flex min-h-full w-full max-w-lg flex-col items-center justify-center px-1 py-3 text-center md:p-6">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 shadow-sm md:mb-6 md:h-16 md:w-16">
        <Scale className="h-7 w-7 stroke-[1.5] md:h-8 md:w-8" />
      </div>

      <h2 className="mb-2 text-3xl font-semibold tracking-tight text-slate-800 md:text-2xl">准备好攻克法考了吗？</h2>
      <p className="mb-5 text-[13px] leading-6 text-slate-500 md:mb-8 md:text-sm md:leading-7">
        把真题、概念或难点交给我，我会先检索本地法考知识库，再用像老师讲题一样的方式帮你梳理逻辑和依据。
      </p>

      <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:flex-wrap sm:justify-center">
        <button
          onClick={() => onPickPrompt('张三离职后打招呼帮李四拿项目并收钱，构成什么罪？')}
          className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2.5 text-[11px] font-medium text-slate-600 transition-colors hover:bg-slate-100 md:py-2 md:text-xs"
        >
          “张三离职打招呼”定什么罪？
        </button>

        <button
          onClick={() => onPickPrompt('帮我梳理一下“不作为犯罪”的构成要件')}
          className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2.5 text-[11px] font-medium text-slate-600 transition-colors hover:bg-slate-100 md:py-2 md:text-xs"
        >
          拆解“不作为犯罪”
        </button>
      </div>
    </div>
  );
}

function MessageList({ messages, activeReferenceId, onReferenceClick, onQuickAction, showQuickActions, bottomRef }: MessageListProps) {
  return (
    <div className="mx-auto max-w-3xl space-y-5 md:space-y-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} activeReferenceId={activeReferenceId} onReferenceClick={onReferenceClick} />
      ))}

      {showQuickActions && <QuickActions onActionSelect={(action) => onQuickAction(action)} />}

      <div ref={bottomRef} className="h-1" />
    </div>
  );
}

function Composer({
  input,
  placeholder,
  isBusy,
  isMindmapMode,
  isGeneratingMindmap,
  mindmapError,
  onInputChange,
  onKeyDown,
  onSubmit,
  onGenerateMindmap,
}: ComposerProps) {
  return (
    <div className="fixed bottom-0 left-0 right-0 z-20 border-t border-slate-200 bg-white/95 px-3 py-3 pb-[calc(env(safe-area-inset-bottom)+0.75rem)] backdrop-blur md:px-6 md:py-6">
      <div className="mx-auto flex max-w-3xl flex-col gap-2.5 md:gap-3">
        {isMindmapMode && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onGenerateMindmap}
              disabled={isBusy || isGeneratingMindmap}
              className="inline-flex items-center gap-1.5 rounded-full bg-blue-600 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isGeneratingMindmap ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Network className="h-3.5 w-3.5" />}
              <span>{isGeneratingMindmap ? '生成中...' : '生成思维导图'}</span>
            </button>
          </div>
        )}
        {isMindmapMode && mindmapError && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-700">
            {mindmapError}
          </div>
        )}

        <form onSubmit={onSubmit} className="relative flex items-end gap-2">
          <div className="flex-1 rounded-2xl border border-transparent bg-slate-100 p-2.5 transition-all focus-within:border-blue-300 focus-within:bg-white md:p-3">
            <textarea
              value={input}
              onChange={(event) => onInputChange(event.target.value)}
              onKeyDown={onKeyDown}
              placeholder={placeholder}
              className="min-h-[42px] max-h-32 w-full resize-none border-none bg-transparent text-[13px] leading-relaxed text-slate-700 outline-none md:min-h-[48px] md:max-h-48 md:text-sm"
              rows={1}
            />
          </div>

          {isMindmapMode ? (
            <button
              type="button"
              onClick={onGenerateMindmap}
              disabled={isBusy || isGeneratingMindmap}
              className={cn(
                floatingActionButtonClass,
                isBusy || isGeneratingMindmap ? 'bg-slate-200 text-slate-400 shadow-none' : 'bg-blue-600 shadow-lg shadow-blue-200 hover:bg-blue-700',
              )}
            >
              {isGeneratingMindmap ? <Loader2 className="h-5 w-5 animate-spin" /> : <Network className="h-5 w-5" />}
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim() || isBusy}
              className={cn(
                floatingActionButtonClass,
                !input.trim() || isBusy ? 'bg-slate-200 text-slate-400 shadow-none' : 'bg-blue-600 shadow-lg shadow-blue-200 hover:bg-blue-700',
              )}
            >
              <Send className="h-5 w-5" />
            </button>
          )}
        </form>

        <div className="mt-0.5 flex justify-center md:mt-1">
          <p className="text-center text-[9px] leading-4 text-slate-400 md:text-[10px] md:leading-5">{getFooterHint(isMindmapMode)}</p>
        </div>
      </div>
    </div>
  );
}

function getMainContent(
  isMindmapMode: boolean,
  messages: Message[],
  activeReferenceId: string | null,
  onReferenceClick: (refId: string) => void,
  onQuickAction: (text: string) => void,
  showQuickActions: boolean,
  bottomRef: React.RefObject<HTMLDivElement | null>,
  onPickPrompt: (text: string) => void,
) {
  if (isMindmapMode) {
    return <MindmapIntro onPickPrompt={onPickPrompt} />;
  }

  if (messages.length === 0) {
    return <EmptyChatState onPickPrompt={onPickPrompt} />;
  }

  return (
    <MessageList
      messages={messages}
      activeReferenceId={activeReferenceId}
      onReferenceClick={onReferenceClick}
      onQuickAction={onQuickAction}
      showQuickActions={showQuickActions}
      bottomRef={bottomRef}
    />
  );
}

export function ChatArea({
  messages,
  setMessages,
  activeReferenceId,
  onReferenceClick,
  settings,
  health,
  onOpenSidebar,
  onOpenAnnouncement,
}: ChatAreaProps) {
  const [input, setInput] = useState('');
  const [isMindmapOpen, setIsMindmapOpen] = useState(false);
  const [mindmapTitle, setMindmapTitle] = useState('');
  const [mindmapCode, setMindmapCode] = useState('');
  const [mindmapInstanceKey, setMindmapInstanceKey] = useState(0);
  const [isGeneratingMindmap, setIsGeneratingMindmap] = useState(false);
  const [mindmapError, setMindmapError] = useState('');
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, settings.studyMode]);

  const lastMessage = messages[messages.length - 1];
  const isBusy = lastMessage?.role === 'assistant' && (lastMessage.status === 'searching' || lastMessage.status === 'generating');
  const isMindmapMode = settings.studyMode === 'memorize';
  const showQuickActions = !isBusy && messages.length > 0 && lastMessage?.role === 'assistant' && !isMindmapMode;

  const sendMessage = async (rawText?: string) => {
    const text = (rawText ?? input).trim();
    if (!text || isBusy) return;

    const timestamp = Date.now();
    const userMessage: Message = {
      id: String(timestamp),
      role: 'user',
      content: text,
      status: 'success',
    };

    const assistantMessageId = String(timestamp + 1);
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      status: 'searching',
      thinking: getAssistantThinkingText(),
    };

    const nextMessages = [...messages, userMessage];
    setMessages((previous) => [...previous, userMessage, assistantMessage]);
    setInput('');

    await runChatTurn({
      question: text,
      settings,
      messages: nextMessages,
      onUpdate: (updates) => {
        setMessages((previous) =>
          previous.map((message) => (message.id === assistantMessageId ? { ...message, ...updates } : message)),
        );
      },
    });
  };

  const handleSend = async (event?: React.FormEvent) => {
    event?.preventDefault();
    await sendMessage();
  };

  const handleGenerateMindmap = async () => {
    if (isGeneratingMindmap || isBusy) return;

    if (!settings.modelBaseUrl.trim()) {
      setMindmapError('还没有填写模型 Base URL。请先到设置里配置 OpenAI 兼容接口，本次没有发起模型请求。');
      return;
    }
    if (!settings.model.trim()) {
      setMindmapError('还没有填写模型名称。请先到设置里配置模型，本次没有发起模型请求。');
      return;
    }
    if (!settings.apiKey.trim()) {
      setMindmapError('还没有填写 API Key。请先到设置里配置密钥，本次没有发起模型请求。');
      return;
    }

    setIsGeneratingMindmap(true);
    setMindmapError('');
    try {
      const generated = await generateMindmap({
        settings,
        messages,
        draftInput: input,
      });
      setMindmapInstanceKey((previous) => previous + 1);
      setMindmapTitle(generated.title);
      setMindmapCode(generated.markdown);
      setIsMindmapOpen(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : '';
      setMindmapError(message || '思维导图生成失败，请检查模型配置后重试。');
    } finally {
      setIsGeneratingMindmap(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Enter' || event.shiftKey) return;

    event.preventDefault();
    if (isMindmapMode) {
      void handleGenerateMindmap();
      return;
    }
    void sendMessage();
  };

  return (
    <div className="relative flex h-full min-h-0 flex-1 flex-col">
      <ChatHeader health={health} onOpenSidebar={onOpenSidebar} onOpenAnnouncement={onOpenAnnouncement} />

      <div className="flex-1 overflow-y-auto px-3 py-3 pb-32 md:px-6 md:py-6 md:pb-36">
        {getMainContent(
          isMindmapMode,
          messages,
          activeReferenceId,
          onReferenceClick,
          (text) => void sendMessage(text),
          showQuickActions,
          bottomRef,
          setInput,
        )}
      </div>

      <Composer
        input={input}
        placeholder={getInputPlaceholder(isMindmapMode)}
        isBusy={Boolean(isBusy)}
        isMindmapMode={isMindmapMode}
        isGeneratingMindmap={isGeneratingMindmap}
        mindmapError={mindmapError}
        onInputChange={setInput}
        onKeyDown={handleKeyDown}
        onSubmit={handleSend}
        onGenerateMindmap={() => void handleGenerateMindmap()}
      />

      <MindmapModal
        key={mindmapInstanceKey}
        isOpen={isMindmapOpen}
        title={mindmapTitle}
        markdownCode={mindmapCode}
        settings={settings}
        onClose={() => setIsMindmapOpen(false)}
      />
    </div>
  );
}
