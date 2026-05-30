import React, { useEffect, useState } from 'react';
import { Sidebar } from './Sidebar';
import { ChatArea } from './ChatArea';
import { ReferencePanel } from './ReferencePanel';
import { AppSettings, Message } from '../types';
import { SettingsModal } from './SettingsModal';
import { AnnouncementModal } from './AnnouncementModal';
import { getHealthUrl, loadStoredSettings, persistSettings } from '../lib/settings';

type HealthState = 'checking' | 'ok' | 'error';

export function Layout() {
  const [settings, setSettings] = useState<AppSettings>(() => loadStoredSettings());
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isAnnouncementOpen, setIsAnnouncementOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeReferenceId, setActiveReferenceId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [health, setHealth] = useState<HealthState>('checking');

  useEffect(() => {
    persistSettings(settings);
  }, [settings]);

  useEffect(() => {
    const checkHealth = async () => {
      setHealth('checking');
      try {
        const response = await fetch(getHealthUrl(settings.searchApiUrl));
        setHealth(response.ok ? 'ok' : 'error');
      } catch {
        setHealth('error');
      }
    };

    checkHealth();
  }, [settings.searchApiUrl]);

  const handleSelectMode = (mode: AppSettings['studyMode']) => {
    setSettings((previous) => ({ ...previous, studyMode: mode }));
  };

  const handleReferenceClick = (refId: string) => {
    setActiveReferenceId((previous) => (previous === refId ? null : refId));
  };

  const handleOpenSettings = () => {
    setIsSidebarOpen(false);
    window.setTimeout(() => setIsSettingsOpen(true), 0);
  };

  return (
    <div className="relative flex h-[100dvh] min-h-0 w-full overflow-hidden bg-slate-50 font-sans text-slate-900">
      <Sidebar
        isOpen={isSidebarOpen}
        settings={settings}
        onClose={() => setIsSidebarOpen(false)}
        onOpenSettings={handleOpenSettings}
        onSelectMode={handleSelectMode}
      />

      <main className="flex min-w-0 min-h-0 flex-1 transition-all duration-300">
        <div className={`flex min-w-0 flex-1 flex-col transition-all duration-300 ${activeReferenceId ? 'mr-[340px]' : ''}`}>
          <ChatArea
            messages={messages}
            setMessages={setMessages}
            activeReferenceId={activeReferenceId}
            onReferenceClick={handleReferenceClick}
            settings={settings}
            health={health}
            onOpenSidebar={() => setIsSidebarOpen(true)}
            onOpenAnnouncement={() => setIsAnnouncementOpen(true)}
          />
        </div>

        <ReferencePanel activeReferenceId={activeReferenceId} onClose={() => setActiveReferenceId(null)} messages={messages} />
      </main>

      {isSettingsOpen && <SettingsModal settings={settings} onClose={() => setIsSettingsOpen(false)} onSave={setSettings} />}
      <AnnouncementModal isOpen={isAnnouncementOpen} onClose={() => setIsAnnouncementOpen(false)} />
    </div>
  );
}
