import React from 'react';
import { X, BookOpen } from 'lucide-react';
import { Citation } from '../types';

interface ReaderPanelProps {
  isOpen: boolean;
  citation: Citation | null;
  onClose: () => void;
}

export function ReaderPanel({ isOpen, citation, onClose }: ReaderPanelProps) {
  if (!isOpen || !citation) return null;

  const path = [citation.chapter, citation.section, citation.subsection].filter(Boolean).join(' / ');

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-[440px] bg-white shadow-2xl border-l border-gray-200 z-40 flex flex-col transform transition-transform duration-300">
      <div className="h-16 px-4 border-b border-gray-200 flex items-center justify-between bg-white shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="bg-blue-100 p-1.5 rounded-md">
            <BookOpen size={18} className="text-blue-700" />
          </div>
          <div className="min-w-0">
            <h2 className="font-semibold text-gray-800 tracking-tight truncate">原文片段</h2>
            <p className="text-xs text-gray-500 truncate">{citation.book_name || '未知文献'}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 bg-gray-50/60">
        <div className="bg-white border border-gray-200 shadow-sm rounded-2xl p-5">
          <div className="flex flex-col gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-blue-600 font-semibold mb-1">Source</p>
              <h3 className="text-lg font-semibold text-gray-900 leading-snug">
                {citation.subsection || citation.section || citation.chapter || citation.book_name || '引用片段'}
              </h3>
            </div>

            <div className="text-sm text-gray-500 leading-relaxed space-y-1">
              {path && <p>{path}</p>}
              <p>
                行号 {citation.source_line_start || '-'} - {citation.source_line_end || '-'}
              </p>
              {typeof citation.score === 'number' && <p>相似度得分 {citation.score.toFixed(4)}</p>}
              {citation.chunk_id && <p>Chunk ID: {citation.chunk_id}</p>}
            </div>

            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 whitespace-pre-wrap leading-7 text-[14px] text-gray-700 font-serif">
              {citation.text_content || '暂无原文内容'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
