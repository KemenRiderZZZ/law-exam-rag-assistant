import { ArrowLeft, Download, ExternalLink } from 'lucide-react';
import { buildXmindBlob, detectWeakMindmapBrowser, readMindmapPreviewSession, safeFilename } from '../lib/mindmapPreview';
import { MindmapPreviewView } from './MindmapPreviewView';

function downloadBlob(blob: Blob, filename: string) {
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

export function MindmapPreviewPage() {
  const searchParams = typeof window === 'undefined' ? null : new URLSearchParams(window.location.search);
  const session = readMindmapPreviewSession(searchParams?.get('id'));
  const weakBrowser = detectWeakMindmapBrowser();

  if (!session) {
    return (
      <div className="flex min-h-screen min-h-[100dvh] items-center justify-center bg-[linear-gradient(180deg,_#eef2ff_0%,_#f8fafc_100%)] px-4 py-10">
        <div className="max-w-lg rounded-[2rem] border border-slate-200 bg-white/95 p-6 text-center shadow-xl">
          <h1 className="text-xl font-semibold text-slate-800">没有可预览的导图</h1>
          <p className="mt-3 text-sm leading-7 text-slate-500">请先回到法考智学 V2 中生成导图，再从站内打开预览页。</p>
          <button
            type="button"
            onClick={() => window.history.back()}
            className="mt-5 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>返回上一页</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen min-h-[100dvh] bg-[linear-gradient(180deg,_#eef2ff_0%,_#f8fafc_100%)] px-4 py-4 pb-6 md:px-6 md:py-6">
      <div className="mx-auto flex max-w-6xl flex-col gap-4">
        <header className="rounded-[2rem] border border-slate-200 bg-white/92 px-4 py-4 shadow-sm md:px-6">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-widest text-blue-600">Mindmap Preview</p>
              <h1 className="mt-1 truncate text-xl font-semibold tracking-tight text-slate-800 md:text-2xl">
                {session.title || '思维导图'}
              </h1>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                {weakBrowser
                  ? '当前浏览器已切换到兼容预览，优先保证层级清楚与导出稳定。'
                  : '这是站内稳定预览页，继续保留现有官方 Markmap 预览。'}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => window.history.back()}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>返回上一页</span>
              </button>
              <a
                href="/"
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
              >
                <ExternalLink className="h-4 w-4" />
                <span>回到首页</span>
              </a>
              {weakBrowser ? (
                <button
                  type="button"
                  onClick={() => downloadBlob(buildXmindBlob(session.markdown, session.title || '思维导图'), `${safeFilename(session.title || '思维导图')}.xmind`)}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700"
                >
                  <Download className="h-4 w-4" />
                  <span>导出 XMind</span>
                </button>
              ) : null}
            </div>
          </div>
        </header>

        <MindmapPreviewView title={session.title} markdown={session.markdown} alwaysShowStaticPreview={weakBrowser} />

        <section className="rounded-[2rem] border border-slate-200 bg-white/92 p-4 shadow-sm md:p-6">
          <h2 className="text-sm font-semibold text-slate-800">原始 Markdown</h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">如果某些浏览器不支持图形预览，也可以直接复制或阅读原始大纲。</p>
          <pre className="mt-4 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs leading-6 text-slate-700">
            {session.markdown}
          </pre>
        </section>
      </div>
    </div>
  );
}
