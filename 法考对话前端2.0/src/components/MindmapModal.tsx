import React, { useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy, Download, ExternalLink, FileText, LayoutList, Loader2, Network, RotateCcw, Sparkles, X } from 'lucide-react';
import { expandMindmapNode, getMindmapDraftStorageKey, getNodePath, type MindmapNode, parseMindmapNodes } from '../lib/mindmap';
import {
  buildStandaloneMindmapHtml,
  buildMindmapPreviewPath,
  buildXmindBlob,
  detectWeakMindmapBrowser,
  markdownToPlainOutline,
  normalizeMindmapMarkdown,
  openMindmapPreviewWindow,
  safeFilename,
} from '../lib/mindmapPreview';
import { AppSettings } from '../types';
import { copyText } from '../lib/copy';
import { MindmapPreviewView } from './MindmapPreviewView';

interface MindmapModalProps {
  isOpen: boolean;
  title: string;
  markdownCode: string;
  settings: AppSettings;
  onClose: () => void;
}

interface SaveWindow extends Window {
  showSaveFilePicker?: (options?: {
    suggestedName?: string;
    types?: Array<{
      description?: string;
      accept: Record<string, string[]>;
    }>;
  }) => Promise<{
    createWritable: () => Promise<{
      write: (data: Blob | string) => Promise<void>;
      close: () => Promise<void>;
    }>;
  }>;
}

interface DraftPayload {
  markdown: string;
  updatedAt: number;
}

type SecondaryPaneState = 'collapsed' | 'outline' | 'document';
type MobileTab = 'preview' | 'outline' | 'document';

function useMediaQuery(query: string) {
  const getInitialValue = () => (typeof window === 'undefined' ? false : window.matchMedia(query).matches);
  const [matches, setMatches] = useState(getInitialValue);

  useEffect(() => {
    const mediaQuery = window.matchMedia(query);
    const handleChange = () => setMatches(mediaQuery.matches);
    handleChange();
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [query]);

  return matches;
}

function readStoredDraft(storageKey: string): DraftPayload | null {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as DraftPayload;
    if (!parsed?.markdown) return null;
    return parsed;
  } catch {
    return null;
  }
}

function writeStoredDraft(storageKey: string, markdown: string) {
  try {
    localStorage.setItem(
      storageKey,
      JSON.stringify({
        markdown,
        updatedAt: Date.now(),
      } satisfies DraftPayload),
    );
  } catch {
    // Ignore localStorage issues.
  }
}

function clearStoredDraft(storageKey: string) {
  try {
    localStorage.removeItem(storageKey);
  } catch {
    // Ignore.
  }
}

function findNodeByCursor(nodes: MindmapNode[], markdown: string, cursor: number) {
  const lineIndex = markdown.slice(0, cursor).split('\n').length - 1;
  let target: MindmapNode | null = null;
  for (const node of nodes) {
    if (node.lineIndex <= lineIndex) {
      target = node;
    } else {
      break;
    }
  }
  return target;
}

async function saveTextFile(
  content: string,
  filename: string,
  mimeType: string,
  pickerTypes?: Array<{
    description?: string;
    accept: Record<string, string[]>;
  }>,
) {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
  const pickerWindow = window as SaveWindow;

  if (typeof pickerWindow.showSaveFilePicker === 'function') {
    const handle = await pickerWindow.showSaveFilePicker({
      suggestedName: filename,
      types: pickerTypes,
    });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return;
  }

  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.rel = 'noopener';
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(url), 1200);
  }
}

async function saveBlobFile(
  blob: Blob,
  filename: string,
  pickerTypes?: Array<{
    description?: string;
    accept: Record<string, string[]>;
  }>,
) {
  const pickerWindow = window as SaveWindow;

  if (typeof pickerWindow.showSaveFilePicker === 'function') {
    const handle = await pickerWindow.showSaveFilePicker({
      suggestedName: filename,
      types: pickerTypes,
    });
    const writable = await handle.createWritable();
    await writable.write(blob);
    await writable.close();
    return;
  }

  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.rel = 'noopener';
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    window.setTimeout(() => URL.revokeObjectURL(url), 1200);
  }
}

async function saveHtmlFile(html: string, filename: string) {
  await saveTextFile(html, filename, 'text/html', [
    {
      description: 'HTML 文件',
      accept: { 'text/html': ['.html'] },
    },
  ]);
}

function OutlineEditorPanel({
  editableMarkdown,
  compact = false,
  toolbar,
  onChange,
  onCursorSync,
}: {
  editableMarkdown: string;
  compact?: boolean;
  toolbar?: React.ReactNode;
  onChange: (value: string) => void;
  onCursorSync: (cursor: number) => void;
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3">
        <h3 className="text-sm font-semibold text-slate-800">可编辑大纲</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          这里是导图底层大纲。可以直接改标题、层级、子项，也可以先选中一行再点上面的 AI 扩写。
        </p>
      </div>
      {toolbar ? <div className="mb-3">{toolbar}</div> : null}
      <textarea
        value={editableMarkdown}
        onChange={(event) => onChange(event.target.value)}
        onClick={(event) => onCursorSync((event.target as HTMLTextAreaElement).selectionStart)}
        onKeyUp={(event) => onCursorSync((event.target as HTMLTextAreaElement).selectionStart)}
        className={`w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 font-mono text-xs leading-6 text-slate-700 outline-none transition focus:border-blue-300 focus:bg-white ${
          compact ? 'min-h-[46vh]' : 'min-h-[58vh]'
        }`}
      />
    </div>
  );
}

function DocumentPanel({ markdown, compact = false }: { markdown: string; compact?: boolean }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm ${compact ? '' : ''}`}>
      <div className="prose prose-slate max-w-none text-sm leading-7 prose-headings:font-semibold prose-headings:text-slate-800 prose-p:text-slate-600 prose-strong:text-slate-800 prose-li:text-slate-600 prose-ul:my-3 prose-ol:my-3 prose-li:marker:text-slate-400">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
      </div>
    </div>
  );
}

function MobileTabButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-1 flex-col items-center justify-center gap-1 rounded-2xl px-3 py-2 text-[11px] font-medium transition-colors ${
        active ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

export function MindmapModal({ isOpen, title, markdownCode, settings, onClose }: MindmapModalProps) {
  const isDesktopLayout = useMediaQuery('(min-width: 768px)');
  const isWeakMindmapBrowser = useMemo(() => detectWeakMindmapBrowser(), []);
  const initialMarkdown = useMemo(() => normalizeMindmapMarkdown(markdownCode), [markdownCode]);
  const storageKey = useMemo(() => getMindmapDraftStorageKey(title || '思维导图', initialMarkdown), [initialMarkdown, title]);
  const [editableMarkdown, setEditableMarkdown] = useState(initialMarkdown);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [isCopying, setIsCopying] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isExpandingNode, setIsExpandingNode] = useState(false);
  const [hasDraft, setHasDraft] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null);
  const [activeSecondaryPane, setActiveSecondaryPane] = useState<SecondaryPaneState>('collapsed');
  const [mobileTab, setMobileTab] = useState<MobileTab>('preview');
  const [panelError, setPanelError] = useState('');
  const isMountedRef = useRef(false);

  const parsedNodes = useMemo(() => {
    try {
      return {
        nodes: parseMindmapNodes(editableMarkdown),
        error: '',
      };
    } catch (error) {
      console.error('思维导图节点解析失败', error);
      return {
        nodes: [],
        error: '导图大纲解析失败。你可以先在可编辑大纲里检查标题或项目符号格式。',
      };
    }
  }, [editableMarkdown]);

  const nodes = parsedNodes.nodes;
  const visiblePanelError = panelError || parsedNodes.error;
  const selectedNode = selectedNodeId ? nodes.find((node) => node.id === selectedNodeId) || null : null;
  const selectedPath = useMemo(() => {
    if (!selectedNode) return [];
    try {
      return getNodePath(editableMarkdown, selectedNode.id);
    } catch (error) {
      console.error('思维导图路径解析失败', error);
      return [];
    }
  }, [editableMarkdown, selectedNode]);

  const exportHtml = useMemo(() => buildStandaloneMindmapHtml(editableMarkdown, title || '思维导图'), [editableMarkdown, title]);
  const exportXmind = useMemo(() => buildXmindBlob(editableMarkdown, title || '思维导图'), [editableMarkdown, title]);
  const isDocumentVisible = activeSecondaryPane === 'document';

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!isOpen) return;

    const stored = readStoredDraft(storageKey);
    if (stored) {
      setEditableMarkdown(stored.markdown);
      setHasDraft(true);
      setLastSavedAt(stored.updatedAt);
    } else {
      setEditableMarkdown(initialMarkdown);
      setHasDraft(false);
      setLastSavedAt(null);
    }

    setSelectedNodeId(null);
    setActiveSecondaryPane('collapsed');
    setMobileTab('preview');
    setPanelError('');
  }, [initialMarkdown, isOpen, storageKey]);

  useEffect(() => {
    if (!isOpen) return;
    writeStoredDraft(storageKey, editableMarkdown);
    setHasDraft(editableMarkdown !== initialMarkdown);
    setLastSavedAt(Date.now());
  }, [editableMarkdown, initialMarkdown, isOpen, storageKey]);

  useEffect(() => {
    if (!isOpen) return;
    if (typeof window !== 'undefined') {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
    return undefined;
  }, [isOpen]);

  const handleCopy = async () => {
    const plainTextCode = markdownToPlainOutline(editableMarkdown);
    if (!plainTextCode || isCopying) return;

    setIsCopying(true);
    try {
      await copyText(plainTextCode);
      if (!isMountedRef.current) return;
      setCopied(true);
      window.setTimeout(() => {
        if (isMountedRef.current) {
          setCopied(false);
        }
      }, 1800);
    } catch {
      if (!isMountedRef.current) return;
      setCopied(false);
    } finally {
      if (!isMountedRef.current) return;
      setIsCopying(false);
    }
  };

  const handleExportHtml = async () => {
    if (isExporting) return;

    setIsExporting(true);
    setPanelError('');
    try {
      await saveHtmlFile(exportHtml, `${safeFilename(title || '思维导图')}.html`);
    } catch (error) {
      if (!isMountedRef.current) return;
      setPanelError(error instanceof Error ? error.message : '导出 HTML 失败，请稍后重试。');
    } finally {
      if (!isMountedRef.current) return;
      setIsExporting(false);
    }
  };

  const handleExportXmind = async () => {
    if (isExporting) return;

    setIsExporting(true);
    setPanelError('');
    try {
      await saveBlobFile(exportXmind, `${safeFilename(title || '思维导图')}.xmind`, [
        {
          description: 'XMind 导图文件',
          accept: {
            'application/vnd.xmind.workbook': ['.xmind'],
            'application/zip': ['.xmind'],
          },
        },
      ]);
    } catch (error) {
      if (!isMountedRef.current) return;
      setPanelError(error instanceof Error ? error.message : '导出 XMind 失败，请稍后重试。');
    } finally {
      if (!isMountedRef.current) return;
      setIsExporting(false);
    }
  };

  const handleOpenInPage = () => {
    try {
      openMindmapPreviewWindow(title || '思维导图', editableMarkdown);
    } catch (error) {
      setPanelError(error instanceof Error ? error.message : '站内预览页打开失败，请稍后重试。');
    }
  };

  const handleRestoreInitial = () => {
    clearStoredDraft(storageKey);
    setEditableMarkdown(initialMarkdown);
    setHasDraft(false);
    setLastSavedAt(null);
    setSelectedNodeId(null);
    setActiveSecondaryPane('collapsed');
    setMobileTab('preview');
    setPanelError('');
  };

  const handleExpandCurrentNode = async () => {
    if (!selectedNodeId || isExpandingNode) return;

    setIsExpandingNode(true);
    setPanelError('');
    try {
      const expanded = await expandMindmapNode({
        settings,
        markdown: editableMarkdown,
        nodeId: selectedNodeId,
        title: title || '思维导图',
      });
      if (!isMountedRef.current) return;
      setEditableMarkdown(expanded.markdown);
      setSelectedNodeId(expanded.selectedNodeId);
    } catch (error) {
      if (!isMountedRef.current) return;
      setPanelError(error instanceof Error ? error.message : 'AI 扩写失败，请检查模型配置后重试。');
    } finally {
      if (!isMountedRef.current) return;
      setIsExpandingNode(false);
    }
  };

  const handleCursorSync = (cursor: number) => {
    try {
      const target = findNodeByCursor(nodes, editableMarkdown, cursor);
      if (target) {
        setSelectedNodeId(target.id);
      }
    } catch (error) {
      console.error('思维导图光标同步失败', error);
    }
  };

  const desktopOutlineToolbar = (
    <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
      <button
        type="button"
        onClick={handleCopy}
        disabled={isCopying}
        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isCopying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        <span>{copied ? '已复制' : '复制大纲'}</span>
      </button>
      <button
        type="button"
        onClick={handleExpandCurrentNode}
        disabled={!selectedNodeId || isExpandingNode}
        className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs text-blue-700 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isExpandingNode ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
        <span>{isExpandingNode ? '扩写中...' : 'AI 扩写当前节点'}</span>
      </button>
      <button
        type="button"
        onClick={handleRestoreInitial}
        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-amber-200 hover:bg-amber-50 hover:text-amber-700"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        <span>恢复初始版本</span>
      </button>
    </div>
  );

  const mobileOutlineToolbar = (
    <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-3">
      <button
        type="button"
        onClick={handleCopy}
        disabled={isCopying}
        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isCopying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
        <span>{copied ? '已复制' : '复制'}</span>
      </button>
      <button
        type="button"
        onClick={handleExpandCurrentNode}
        disabled={!selectedNodeId || isExpandingNode}
        className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs text-blue-700 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isExpandingNode ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
        <span>{isExpandingNode ? 'AI扩写中' : 'AI扩写'}</span>
      </button>
      <button
        type="button"
        onClick={handleRestoreInitial}
        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-amber-200 hover:bg-amber-50 hover:text-amber-700"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        <span>恢复</span>
      </button>
      <button
        type="button"
        onClick={handleOpenInPage}
        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
      >
        <ExternalLink className="h-3.5 w-3.5" />
        <span>站内预览页</span>
      </button>
    </div>
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/55" onClick={onClose}>
      <div
        className="flex h-screen h-[100dvh] w-full flex-col overflow-hidden bg-white shadow-2xl md:mx-auto md:mt-4 md:h-[calc(100dvh-2rem)] md:max-h-[92vh] md:max-w-[1300px] md:rounded-3xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="hidden items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-4 md:flex md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-200">
              <Network className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-slate-800 md:text-lg">思维导图</h2>
              <p className="truncate text-sm text-slate-500">{title || '查看思维导图'}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              onClick={handleCopy}
              disabled={isCopying}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isCopying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              <span>{copied ? '已复制' : '复制文本'}</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveSecondaryPane((previous) => (previous === 'document' ? 'collapsed' : 'document'))}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
            >
              <FileText className="h-3.5 w-3.5" />
              <span>{isDocumentVisible ? '收起文档' : '查看文档'}</span>
            </button>

            <button
              type="button"
              onClick={handleExpandCurrentNode}
              disabled={!selectedNodeId || isExpandingNode}
              className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs text-blue-700 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isExpandingNode ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              <span>{isExpandingNode ? '扩写中...' : 'AI 扩写当前节点'}</span>
            </button>

            <button
              type="button"
              onClick={handleOpenInPage}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>站内预览页</span>
            </button>

            <button
              type="button"
              onClick={handleRestoreInitial}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-amber-200 hover:bg-amber-50 hover:text-amber-700"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>恢复初始版本</span>
            </button>

            <button
              type="button"
              onClick={handleExportHtml}
              disabled={isExporting}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isExporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              <span>{isExporting ? '导出中...' : '导出 HTML'}</span>
            </button>

            {isWeakMindmapBrowser ? (
              <button
                type="button"
                onClick={handleExportXmind}
                disabled={isExporting}
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isExporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                <span>{isExporting ? '导出中...' : '导出 XMind'}</span>
              </button>
            ) : null}

            <button type="button" onClick={onClose} className="rounded-full p-2 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-700">
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="hidden border-b border-slate-200 bg-white px-4 py-3 md:block md:px-6">
          {visiblePanelError ? (
            <div className="mb-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-700">{visiblePanelError}</div>
          ) : null}
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span>当前节点：{selectedNode ? selectedNode.text : '未选中，先点左侧大纲中的某一行'}</span>
            <span className="hidden md:inline">{hasDraft ? '本地草稿已保存' : '当前仍是初始生成版本'}</span>
            {selectedPath.length > 0 ? <span className="hidden md:inline">节点路径：{selectedPath.join(' / ')}</span> : null}
            {lastSavedAt ? <span>最近保存：{new Date(lastSavedAt).toLocaleTimeString()}</span> : null}
          </div>
        </div>

        {!isDesktopLayout ? (
          <div className="flex min-h-0 flex-1 flex-col bg-[linear-gradient(180deg,_#f8fafc_0%,_#eef2ff_100%)] md:hidden">
            <header className="shrink-0 border-b border-slate-200 bg-white/95 px-4 pb-3 pt-3 backdrop-blur">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-200">
                      <Network className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h2 className="truncate text-base font-semibold text-slate-800">思维导图</h2>
                      <p className="truncate text-sm text-slate-500">{title || '查看思维导图'}</p>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] leading-5 text-slate-500">
                    <span>当前节点：{selectedNode ? selectedNode.text : '未选中'}</span>
                    {lastSavedAt ? <span>最近保存：{new Date(lastSavedAt).toLocaleTimeString()}</span> : null}
                  </div>
                </div>

                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    onClick={handleExportHtml}
                    disabled={isExporting}
                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isExporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                    <span>{isExporting ? '导出中' : '导出'}</span>
                  </button>
                  {isWeakMindmapBrowser ? (
                    <button
                      type="button"
                      onClick={handleExportXmind}
                      disabled={isExporting}
                      className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isExporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                      <span>XMind</span>
                    </button>
                  ) : null}
                  <button type="button" onClick={onClose} className="rounded-full p-2 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-700">
                    <X className="h-5 w-5" />
                  </button>
                </div>
              </div>

              <div className="mt-3">
                <div className="grid grid-cols-3 gap-2 rounded-[1.4rem] border border-slate-200 bg-slate-50 p-1.5">
                  <MobileTabButton active={mobileTab === 'preview'} icon={<Network className="h-4 w-4" />} label="导图" onClick={() => setMobileTab('preview')} />
                  <MobileTabButton active={mobileTab === 'outline'} icon={<LayoutList className="h-4 w-4" />} label="大纲" onClick={() => setMobileTab('outline')} />
                  <MobileTabButton active={mobileTab === 'document'} icon={<FileText className="h-4 w-4" />} label="文档" onClick={() => setMobileTab('document')} />
                </div>
              </div>
            </header>

            <div className="min-h-0 flex-1 overflow-auto px-4 py-4 pb-[calc(env(safe-area-inset-bottom)+5.5rem)]">
              {visiblePanelError ? (
                <div className="mb-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs leading-5 text-rose-700">{visiblePanelError}</div>
              ) : null}

              {mobileTab === 'preview' ? <MindmapPreviewView title={title} markdown={editableMarkdown} compact /> : null}

              {mobileTab === 'outline' ? (
                <OutlineEditorPanel compact editableMarkdown={editableMarkdown} onChange={setEditableMarkdown} onCursorSync={handleCursorSync} toolbar={mobileOutlineToolbar} />
              ) : null}

              {mobileTab === 'document' ? <DocumentPanel compact markdown={editableMarkdown} /> : null}
            </div>

            <footer className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-200 bg-white/95 px-4 pb-[calc(env(safe-area-inset-bottom)+0.75rem)] pt-3 backdrop-blur md:hidden">
              <div className="mx-auto max-w-3xl">
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={handleOpenInPage}
                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    <span>站内预览页</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleCopy}
                    disabled={isCopying}
                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isCopying ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>{copied ? '已复制' : '复制'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleRestoreInitial}
                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-amber-200 hover:bg-amber-50 hover:text-amber-700"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    <span>恢复</span>
                  </button>
                  {isWeakMindmapBrowser ? (
                    <button
                      type="button"
                      onClick={handleExportXmind}
                      disabled={isExporting}
                      className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isExporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                      <span>导出 XMind</span>
                    </button>
                  ) : null}
                </div>
              </div>
            </footer>
          </div>
        ) : null}

        {isDesktopLayout ? (
          <div className={`hidden flex-1 gap-0 overflow-hidden md:grid ${isDocumentVisible ? 'md:grid-cols-[0.9fr_1.1fr_0.9fr]' : 'md:grid-cols-[1fr_1.2fr]'}`}>
            <div className="overflow-auto border-r border-slate-200 bg-slate-50 p-4 md:p-5">
              <OutlineEditorPanel editableMarkdown={editableMarkdown} onChange={setEditableMarkdown} onCursorSync={handleCursorSync} toolbar={desktopOutlineToolbar} />
            </div>

            <div className="overflow-auto bg-[radial-gradient(circle_at_top,_rgba(59,130,246,0.08),_transparent_32%),linear-gradient(180deg,_#ffffff_0%,_#f8fafc_100%)] p-4 md:p-6">
              <MindmapPreviewView title={title} markdown={editableMarkdown} />
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleOpenInPage}
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  <span>打开 {buildMindmapPreviewPath()}</span>
                </button>
                <button
                  type="button"
                  onClick={handleExportHtml}
                  disabled={isExporting}
                  className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isExporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                  <span>{isExporting ? '导出中...' : '导出自包含 HTML'}</span>
                </button>
                {isWeakMindmapBrowser ? (
                  <button
                    type="button"
                    onClick={handleExportXmind}
                    disabled={isExporting}
                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isExporting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                    <span>导出 XMind</span>
                  </button>
                ) : null}
              </div>
            </div>

            {isDocumentVisible && (
              <div className="overflow-auto border-l border-slate-200 bg-slate-50 p-4 md:p-6">
                <h3 className="mb-3 text-sm font-semibold text-slate-700">文档阅读</h3>
                <DocumentPanel markdown={editableMarkdown} />
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
