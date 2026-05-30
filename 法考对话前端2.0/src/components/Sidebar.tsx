import { GitBranch, MessageSquareMore, Scale, Settings } from 'lucide-react';
import { cn } from '../lib/utils';
import { AppSettings } from '../types';

interface SidebarProps {
  isOpen: boolean;
  settings: AppSettings;
  onClose: () => void;
  onOpenSettings: () => void;
  onSelectMode: (mode: AppSettings['studyMode']) => void;
}

const navButtonClass = 'flex h-12 w-12 items-center justify-center rounded-2xl transition-colors';

export function Sidebar({ isOpen, settings, onClose, onOpenSettings, onSelectMode }: SidebarProps) {
  return (
    <>
      <div
        className={cn(
          'fixed inset-0 z-30 bg-slate-950/30 transition-opacity duration-200',
          isOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={onClose}
      />

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-20 flex-col items-center border-r border-slate-800 bg-slate-900 py-5 shadow-2xl transition-transform duration-200',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-600 text-white shadow-lg shadow-blue-500/20">
          <Scale className="h-6 w-6 stroke-[2]" />
        </div>

        <div className="mt-7 flex w-full flex-col items-center gap-3">
          <button
            type="button"
            title="答题解析"
            onClick={() => {
              onSelectMode('exam');
              onClose();
            }}
            className={cn(
              navButtonClass,
              settings.studyMode === 'exam' ? 'bg-slate-800 text-blue-400 shadow-sm' : 'text-slate-500 hover:bg-slate-800 hover:text-slate-200',
            )}
          >
            <MessageSquareMore className="h-6 w-6" />
          </button>

          <button
            type="button"
            title="思维导图"
            onClick={() => {
              onSelectMode('memorize');
              onClose();
            }}
            className={cn(
              navButtonClass,
              settings.studyMode === 'memorize' ? 'bg-slate-800 text-blue-400 shadow-sm' : 'text-slate-500 hover:bg-slate-800 hover:text-slate-200',
            )}
          >
            <GitBranch className="h-6 w-6" />
          </button>
        </div>

        <div className="mt-auto flex w-full flex-col items-center gap-3">
          <button
            type="button"
            onClick={onOpenSettings}
            title="设置"
            className={cn(navButtonClass, 'mb-1 text-slate-400 hover:bg-slate-800 hover:text-slate-100')}
          >
            <Settings className="h-6 w-6" />
          </button>
        </div>
      </aside>
    </>
  );
}
