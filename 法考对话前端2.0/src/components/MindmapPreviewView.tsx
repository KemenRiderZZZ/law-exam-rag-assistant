import { useMemo, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import {
  buildCompatibilityPreviewModel,
  buildMarkmapLikeSvg,
  buildMindmapTree,
  detectWeakMindmapBrowser,
  markdownToPlainOutline,
  type CanonicalMindmapNode,
  type MindmapTreeNode,
} from '../lib/mindmapPreview';
import { OfficialMarkmapView } from './OfficialMarkmapView';

interface MindmapPreviewViewProps {
  title: string;
  markdown: string;
  compact?: boolean;
  alwaysShowStaticPreview?: boolean;
}

type OfficialRenderState = 'pending' | 'ready' | 'error';

function MindmapTreeBranch({ node, depth = 0 }: { node: MindmapTreeNode; depth?: number }) {
  return (
    <li className="list-none">
      <div
        className={`rounded-2xl border px-3 py-2 text-sm leading-6 shadow-sm ${
          depth === 0
            ? 'border-blue-200 bg-blue-50 text-blue-950'
            : depth === 1
              ? 'border-emerald-200 bg-emerald-50 text-emerald-950'
              : 'border-slate-200 bg-white text-slate-700'
        }`}
      >
        <span className="font-medium">{node.text}</span>
      </div>
      {node.children.length > 0 ? (
        <ul className="mt-2 space-y-2 border-l border-slate-200 pl-3">
          {node.children.map((child) => (
            <MindmapTreeBranch key={child.id} node={child} depth={depth + 1} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function CompatibilityPreviewNode({ node, index = 0 }: { node: CanonicalMindmapNode; index?: number }) {
  const depthClass =
    node.depth === 0
      ? 'border-blue-200 bg-blue-50'
      : node.depth === 1
        ? 'border-emerald-200 bg-emerald-50'
        : node.kind === 'heading'
          ? 'border-amber-200 bg-amber-50'
          : 'border-slate-200 bg-white';

  return (
    <section className={`rounded-[1.35rem] border px-3 py-3 shadow-sm ${depthClass}`}>
      <div className="flex items-start gap-3">
        <span
          className={`mt-0.5 inline-flex h-6 min-w-6 items-center justify-center rounded-full px-1.5 text-[11px] font-semibold ${
            node.kind === 'heading' ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700'
          }`}
        >
          {node.kind === 'heading' ? index + 1 : '•'}
        </span>
        <div className="min-w-0 flex-1">
          <h4
            className={`break-words leading-7 ${
              node.depth === 0
                ? 'text-base font-semibold text-slate-900'
                : node.depth === 1
                  ? 'text-[15px] font-semibold text-slate-800'
                  : node.kind === 'heading'
                    ? 'text-sm font-semibold text-slate-700'
                    : 'text-sm font-medium text-slate-600'
            }`}
          >
            {node.text}
          </h4>
          {node.children.length > 0 ? (
            <div className="mt-3 space-y-3 border-l-2 border-blue-100 pl-3">
              {node.children.map((child, childIndex) => (
                <CompatibilityPreviewNode key={child.id} node={child} index={childIndex} />
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function MindmapPreviewView({ title, markdown, compact = false, alwaysShowStaticPreview = false }: MindmapPreviewViewProps) {
  const [officialRenderState, setOfficialRenderState] = useState<OfficialRenderState>('pending');
  const weakBrowser = useMemo(() => detectWeakMindmapBrowser(), []);
  const preview = useMemo(() => {
    try {
      return {
        svgPayload: buildMarkmapLikeSvg(markdown, title),
        error: '',
      };
    } catch (error) {
      return {
        svgPayload: null,
        error: error instanceof Error ? error.message : '导图暂时无法预览',
      };
    }
  }, [markdown, title]);

  const outline = useMemo(() => markdownToPlainOutline(markdown), [markdown]);
  const tree = useMemo(() => buildMindmapTree(markdown), [markdown]);
  const compatibilityTree = useMemo(() => buildCompatibilityPreviewModel(markdown, title), [markdown, title]);

  const shouldUseCompatibilityPreview = weakBrowser;
  const shouldShowStaticPreview = Boolean(
    preview.svgPayload && !shouldUseCompatibilityPreview && (alwaysShowStaticPreview || compact || officialRenderState !== 'ready'),
  );
  const shouldShowTreeFallback = tree.length > 0 && !shouldUseCompatibilityPreview && officialRenderState === 'error';

  return (
    <div className={`rounded-3xl border border-slate-200 bg-white/92 shadow-sm ${compact ? 'p-3' : 'p-4 md:p-6'}`}>
      <div className={compact ? 'mb-3' : 'mb-4'}>
        <h3 className="text-sm font-semibold text-slate-800">{compact ? '导图预览' : 'Mind Map 预览'}</h3>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          {shouldUseCompatibilityPreview
            ? '当前浏览器已切换到兼容预览，优先保证层级关系可读。'
            : '继续优先使用现有官方 Markmap 预览；如果浏览器不稳定，会保留兼容视图。'}
        </p>
      </div>

      {shouldUseCompatibilityPreview ? (
        <div className="rounded-[1.8rem] border border-slate-200 bg-[linear-gradient(180deg,_#ffffff_0%,_#f8fafc_100%)] p-3 md:p-5">
          <div className="mx-auto max-w-4xl rounded-[1.8rem] border border-slate-200 bg-white p-4 shadow-sm md:p-6">
            <div className="border-b border-slate-200 pb-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-blue-600">Compatibility Preview</p>
              <h4 className="mt-2 text-xl font-semibold tracking-tight text-slate-900">{compatibilityTree.text}</h4>
              <p className="mt-2 text-xs leading-6 text-slate-500">这是弱兼容浏览器专用预览，层级关系与导出文件保持一致。</p>
            </div>
            <div className="mt-4 space-y-3">
              {compatibilityTree.children.map((node, index) => (
                <CompatibilityPreviewNode key={node.id} node={node} index={index} />
              ))}
            </div>
          </div>
        </div>
      ) : null}

      {!shouldUseCompatibilityPreview && tree.length > 0 ? (
        <OfficialMarkmapView markdown={markdown} compact={compact} onRenderStateChange={setOfficialRenderState} />
      ) : null}

      {shouldShowStaticPreview ? (
        <div className="mt-4 overflow-auto rounded-2xl border border-slate-200 bg-[linear-gradient(180deg,_#ffffff_0%,_#f8fafc_100%)] p-3 md:p-4">
          <div className="mb-3">
            <h4 className="text-sm font-semibold text-slate-800">静态导图预览</h4>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              {officialRenderState === 'ready'
                ? '这是移动端保留的可读预览图，导出文件仍会优先显示官方 Markmap。'
                : '正在等待官方导图节点渲染；如果上方为空，可以直接查看这张兼容预览图。'}
            </p>
          </div>
          <div
            className="min-h-[260px] min-w-max"
            aria-label={title || '思维导图静态预览'}
            dangerouslySetInnerHTML={{ __html: preview.svgPayload.svg }}
          />
        </div>
      ) : null}

      {shouldShowTreeFallback ? (
        <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3 md:p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div>
              <h4 className="text-sm font-semibold text-slate-800">兼容大纲树</h4>
              <p className="mt-1 text-xs leading-5 text-slate-500">当前浏览器未能稳定显示官方导图，下面保留可读结构。</p>
            </div>
          </div>
          <ul className="space-y-2">
            {tree.map((node) => (
              <MindmapTreeBranch key={node.id} node={node} />
            ))}
          </ul>
        </div>
      ) : null}

      {!compatibilityTree.children.length ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4">
          <div className="flex items-start gap-2 text-sm text-amber-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-medium">{preview.error || '导图暂时无法渲染'}</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">当前自动切换为可读大纲，保证内容仍可查看。</p>
            </div>
          </div>

          <pre className="mt-4 whitespace-pre-wrap break-words rounded-2xl border border-slate-200 bg-white p-4 font-mono text-xs leading-6 text-slate-700">
            {outline || markdown}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
