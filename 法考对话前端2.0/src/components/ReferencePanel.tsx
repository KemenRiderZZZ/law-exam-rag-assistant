import React, { useMemo } from 'react';
import { X, Scale, Bookmark } from 'lucide-react';
import { Message } from '../types';

interface ReferencePanelProps {
  activeReferenceId: string | null;
  onClose: () => void;
  messages: Message[];
}

export function ReferencePanel({ activeReferenceId, onClose, messages }: ReferencePanelProps) {
  const activeReference = useMemo(() => {
    if (!activeReferenceId) return null;
    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message.references) {
        const found = message.references.find((reference) => reference.id === activeReferenceId);
        if (found) return found;
      }
    }
    return null;
  }, [activeReferenceId, messages]);

  if (!activeReferenceId) {
    return <div className="pointer-events-none fixed inset-y-0 right-0 z-20 hidden w-[340px] translate-x-full transform border-l border-slate-200 bg-slate-50 shadow-2xl transition-all duration-300 md:block"></div>;
  }

  return (
    <aside className="fixed inset-0 z-40 flex flex-col bg-white md:inset-y-0 md:left-auto md:w-[340px] md:border-l md:border-slate-200 md:shadow-2xl">
      <div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-slate-50/80 p-4">
        <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-500">
          <Bookmark className="ml-1 h-4 w-4" />
          法条依据
        </h3>
        <button type="button" onClick={onClose} className="rounded-full p-1.5 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-600">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
        {activeReference ? (
          <div className="rounded-xl border border-slate-100 bg-white p-4 transition-all hover:border-blue-200 hover:bg-blue-50/30">
            <div className="mb-2 flex items-start justify-between gap-2">
              <span className="rounded bg-blue-100 px-2 py-0.5 text-[9px] font-bold uppercase text-blue-700">法条依据</span>
            </div>

            <p className="mb-3 text-sm font-bold text-slate-800">{activeReference.title}</p>

            <div className="whitespace-pre-wrap rounded-xl border border-slate-100 bg-slate-50 p-4 font-serif text-[12px] leading-6 text-slate-700">
              {activeReference.content}
            </div>
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center p-6 text-center text-slate-500">
            <Scale className="mb-3 h-8 w-8 text-slate-300" />
            <p className="text-sm">暂未找到对应法条依据</p>
          </div>
        )}
      </div>
    </aside>
  );
}
