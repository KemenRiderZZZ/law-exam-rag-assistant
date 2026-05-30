import React from 'react';

interface ErrorBoundaryState {
  error: Error | null;
}

function clearMindmapDrafts() {
  const keys: string[] = [];
  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index);
    if (key?.startsWith('law-mindmap-draft:')) {
      keys.push(key);
    }
  }
  keys.forEach((key) => localStorage.removeItem(key));
}

export class ErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('前端界面发生错误', error, info);
  }

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-slate-50 px-4 py-10 text-slate-800">
        <div className="w-full max-w-lg rounded-3xl border border-slate-200 bg-white p-6 shadow-xl">
          <p className="text-sm font-semibold text-rose-600">页面遇到了一点问题</p>
          <h1 className="mt-3 text-2xl font-bold tracking-tight">不用担心，数据没有丢。</h1>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            某个前端模块运行出错，系统已拦截，避免整页白屏。你可以先刷新页面；如果刚才在编辑思维导图，可以清除本地导图草稿后再刷新。
          </p>
          <p className="mt-3 rounded-2xl bg-slate-50 px-4 py-3 font-mono text-xs text-slate-500">
            {this.state.error.message || '未知前端错误'}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="rounded-full bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-blue-700"
            >
              刷新页面
            </button>
            <button
              type="button"
              onClick={() => {
                clearMindmapDrafts();
                window.location.reload();
              }}
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              清除导图草稿并刷新
            </button>
          </div>
        </div>
      </div>
    );
  }
}
