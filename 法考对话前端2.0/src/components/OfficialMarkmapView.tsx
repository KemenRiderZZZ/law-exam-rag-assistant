import { useEffect, useMemo, useRef, useState } from 'react';
import { Transformer } from 'markmap-lib';
import { Markmap } from 'markmap-view';
import { normalizeMindmapMarkdown } from '../lib/mindmapPreview';

const transformer = new Transformer();

interface OfficialMarkmapViewProps {
  markdown: string;
  compact?: boolean;
  onRenderStateChange?: (state: 'pending' | 'ready' | 'error') => void;
}

function hasRenderedMarkmapNodes(svg: SVGSVGElement) {
  const nodeCount = svg.querySelectorAll('g.markmap-node').length;
  const foreignObjectCount = svg.querySelectorAll('foreignObject.markmap-foreign').length;
  const readableText = (svg.textContent || '').replace(/\s+/g, '');
  return nodeCount > 0 && (foreignObjectCount > 0 || readableText.length > 0);
}

export function OfficialMarkmapView({ markdown, compact = false, onRenderStateChange }: OfficialMarkmapViewProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const markmapRef = useRef<Markmap | null>(null);
  const [error, setError] = useState('');

  const root = useMemo(() => {
    const normalized = normalizeMindmapMarkdown(markdown);
    return transformer.transform(normalized).root;
  }, [markdown]);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return undefined;

    let cancelled = false;
    setError('');
    onRenderStateChange?.('pending');

    try {
      if (markmapRef.current) {
        markmapRef.current.destroy();
        markmapRef.current = null;
      }

      svg.innerHTML = '';

      const markmap = Markmap.create(
        svg,
        {
          autoFit: true,
          duration: 0,
          embedGlobalCSS: true,
          fitRatio: 0.94,
          initialExpandLevel: 6,
          maxInitialScale: 1.2,
          maxWidth: compact ? 260 : 320,
          nodeMinHeight: 20,
          paddingX: compact ? 10 : 14,
          pan: true,
          scrollForPan: true,
          spacingHorizontal: compact ? 62 : 82,
          spacingVertical: compact ? 8 : 12,
          zoom: true,
        },
        root,
      );
      markmapRef.current = markmap;

      const finishWithError = (message: string) => {
        if (cancelled) return;
        setError(message);
        onRenderStateChange?.('error');
      };

      const verifyRender = (attempt = 0) => {
        if (cancelled) return;

        const rect = svg.getBoundingClientRect();
        if (!rect.width || !rect.height) {
          finishWithError('当前浏览器没有正确计算导图画布尺寸，已切换到兼容预览。');
          return;
        }

        if (hasRenderedMarkmapNodes(svg)) {
          markmap.fit().then(() => {
            if (!cancelled) {
              onRenderStateChange?.('ready');
            }
          }).catch(() => {
            finishWithError('官方导图自动适配失败，已切换到兼容预览。');
          });
          return;
        }

        const retryDelays = [220, 500];
        const nextDelay = retryDelays[attempt];
        if (nextDelay) {
          window.setTimeout(() => verifyRender(attempt + 1), nextDelay);
          return;
        }

        markmap.fit().then(() => {
          if (!cancelled && hasRenderedMarkmapNodes(svg)) {
            onRenderStateChange?.('ready');
            return;
          }
          finishWithError('官方导图节点没有稳定显示，已切换到兼容预览。');
        }).catch(() => {
          finishWithError('官方导图自动适配失败，已切换到兼容预览。');
        });
      };

      window.setTimeout(() => verifyRender(), 80);
    } catch (renderError) {
      setError(renderError instanceof Error ? renderError.message : '官方导图预览初始化失败，已切换到兼容预览。');
      onRenderStateChange?.('error');
    }

    return () => {
      cancelled = true;
      if (markmapRef.current) {
        markmapRef.current.destroy();
        markmapRef.current = null;
      }
    };
  }, [compact, onRenderStateChange, root]);

  return (
    <div className="rounded-2xl border border-blue-100 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-4 py-3">
        <h4 className="text-sm font-semibold text-slate-800">Markmap 官方导图预览</h4>
        <p className="mt-1 text-xs leading-5 text-slate-500">使用 markmap-lib + markmap-view 渲染；若移动浏览器无法显示节点，会自动保留兼容预览。</p>
        {error ? <p className="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-700">{error}</p> : null}
      </div>
      <div className="overflow-auto bg-[radial-gradient(circle_at_top_left,_rgba(59,130,246,0.08),_transparent_32%),#ffffff]">
        <svg
          ref={svgRef}
          className="block h-[420px] min-h-[360px] w-[960px] max-w-none md:h-[560px] md:w-full md:min-w-[920px]"
          role="img"
          aria-label="Markmap 官方思维导图预览"
        />
      </div>
    </div>
  );
}
