import React, { MouseEvent, useState } from 'react';
import { X, Settings2, Code, KeyRound, Save, LoaderCircle, Link2, RotateCcw } from 'lucide-react';
import { AppSettings } from '../types';
import { BUILT_IN_SEARCH_API_URL, getHealthUrl, normalizeSettings } from '../lib/settings';
import { buildGatewayModelSettings, testModelGateway } from '../lib/modelApi';

interface SettingsModalProps {
  settings: AppSettings;
  onClose: () => void;
  onSave: (settings: AppSettings) => void;
}

interface LinkTestResult {
  kind: 'success' | 'error';
  searchMessage: string;
  modelMessage: string;
}

const LINK_TEST_TIMEOUT_MS = 60000;
const BASIC_STUDY_MODES: Array<{ id: AppSettings['studyMode']; label: string }> = [
  { id: 'exam', label: '真题解析' },
  { id: 'memorize', label: '思维导图' },
];

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = LINK_TEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    if (error.name === 'AbortError') {
      return `请求超时（${Math.round(LINK_TEST_TIMEOUT_MS / 1000)} 秒）`;
    }
    return error.message;
  }
  return '未知错误';
}

export function SettingsModal({ settings, onClose, onSave }: SettingsModalProps) {
  const [localSettings, setLocalSettings] = useState<AppSettings>(normalizeSettings(settings));
  const [activeTab, setActiveTab] = useState<'basic' | 'advanced'>('basic');
  const [isTestingLinks, setIsTestingLinks] = useState(false);
  const [testResult, setTestResult] = useState<LinkTestResult | null>(null);

  const handleChange = (key: keyof AppSettings, value: AppSettings[keyof AppSettings]) => {
    setLocalSettings((previous) => ({ ...previous, [key]: value }));
    setTestResult(null);
  };

  const handleTopKChange = (rawValue: string) => {
    const parsed = parseInt(rawValue, 10);
    handleChange('topK', Number.isNaN(parsed) ? 1 : Math.min(30, Math.max(1, parsed)));
  };

  const handleResetBuiltInSearch = () => {
    setLocalSettings((previous) => ({
      ...previous,
      searchApiUrl: BUILT_IN_SEARCH_API_URL,
    }));
    setTestResult(null);
  };

  const handleTestLinks = async (event?: MouseEvent<HTMLButtonElement>) => {
    event?.preventDefault();
    event?.stopPropagation();

    const normalizedSettings = normalizeSettings(localSettings);
    const searchHealthUrl = getHealthUrl(normalizedSettings.searchApiUrl);

    setIsTestingLinks(true);
    setTestResult(null);

    try {
      const searchMessagePromise = fetchWithTimeout(searchHealthUrl)
        .then(async (response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return `内置检索接口连接成功：${searchHealthUrl}`;
        })
        .catch((error) => `内置检索接口连接失败：${searchHealthUrl}；${getErrorMessage(error)}`);

      const modelMessagePromise = (() => {
        if (!normalizedSettings.modelBaseUrl) {
          return Promise.resolve('模型接口未测试：请先填写模型 Base URL。');
        }
        if (!normalizedSettings.model) {
          return Promise.resolve('模型接口未测试：请先填写模型名称。');
        }
        if (!normalizedSettings.apiKey) {
          return Promise.resolve('模型接口未测试：请先填写 API Key。');
        }

        return testModelGateway(buildGatewayModelSettings(normalizedSettings), LINK_TEST_TIMEOUT_MS)
          .then((payload) => `模型接口连接成功：${payload?.endpoint || normalizedSettings.modelBaseUrl}`)
          .catch((error) => `模型接口连接失败：${normalizedSettings.modelBaseUrl}；${getErrorMessage(error)}`);
      })();

      const [searchMessage, modelMessage] = await Promise.all([searchMessagePromise, modelMessagePromise]);
      const kind = searchMessage.includes('连接成功') && modelMessage.includes('连接成功') ? 'success' : 'error';
      setTestResult({ kind, searchMessage, modelMessage });
    } finally {
      setIsTestingLinks(false);
    }
  };

  const handleSave = (event?: MouseEvent<HTMLButtonElement>) => {
    event?.preventDefault();
    event?.stopPropagation();
    onSave(normalizeSettings(localSettings));
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 font-sans backdrop-blur-sm" onClick={onClose}>
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl" onClick={(event) => event.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-800">
            <Settings2 className="h-5 w-5 text-blue-600" />
            偏好与模型设置
          </h2>
          <button type="button" onClick={onClose} className="rounded-full p-2 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex gap-6 border-b border-slate-200 bg-slate-50 px-6 pt-2">
          <button
            type="button"
            className={`pb-3 text-sm font-medium transition-colors ${
              activeTab === 'basic' ? 'border-b-2 border-blue-600 text-blue-600' : 'border-b-2 border-transparent text-slate-500 hover:text-slate-700'
            }`}
            onClick={() => setActiveTab('basic')}
          >
            学习偏好
          </button>
          <button
            type="button"
            className={`flex items-center gap-1.5 pb-3 text-sm font-medium transition-colors ${
              activeTab === 'advanced' ? 'border-b-2 border-blue-600 text-blue-600' : 'border-b-2 border-transparent text-slate-500 hover:text-slate-700'
            }`}
            onClick={() => setActiveTab('advanced')}
          >
            <Code className="h-4 w-4" />
            模型与检索
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto bg-white p-6">
          {activeTab === 'basic' && (
            <div className="space-y-6">
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-700">默认学习模式</label>
                <div className="grid grid-cols-2 gap-3">
                  {BASIC_STUDY_MODES.map((mode) => (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => handleChange('studyMode', mode.id)}
                      className={`rounded-xl border px-4 py-3 text-sm font-medium transition-all ${
                        localSettings.studyMode === mode.id
                          ? 'border-blue-600 bg-blue-50 text-blue-700 ring-1 ring-blue-600/20'
                          : 'border-slate-200 bg-white text-slate-600 hover:border-blue-300'
                      }`}
                    >
                      {mode.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm text-slate-600">这里只保留已经接通主链路的模式，避免界面选项和真实能力错位。</p>
              </div>
            </div>
          )}

          {activeTab === 'advanced' && (
            <div className="space-y-4">
              <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
                <KeyRound className="mt-0.5 h-4 w-4 shrink-0" />
                <p>API Key 只保存在当前浏览器本地，并由当前服务通过 OpenAI 兼容接口代发请求。前端不再直接访问第三方模型域名。</p>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-slate-700">内置检索服务</p>
                    <p className="text-xs text-slate-500">检索接口固定使用当前站点内置服务，不需要手动填写。默认地址：{BUILT_IN_SEARCH_API_URL}</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleResetBuiltInSearch}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-100"
                  >
                    <RotateCcw className="h-4 w-4" />
                    恢复默认
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-slate-700">模型 Base URL</label>
                  <input
                    type="text"
                    value={localSettings.modelBaseUrl}
                    onChange={(event) => handleChange('modelBaseUrl', event.target.value)}
                    placeholder="https://api.deepseek.com/v1"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-slate-700">模型名称</label>
                  <input
                    type="text"
                    value={localSettings.model}
                    onChange={(event) => handleChange('model', event.target.value)}
                    placeholder="deepseek-v4-flash"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-700">API Key</label>
                <input
                  type="password"
                  value={localSettings.apiKey}
                  onChange={(event) => handleChange('apiKey', event.target.value)}
                  placeholder="sk-..."
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>

              <div className="space-y-4">
                <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    <span>Temperature</span>
                    <span className="text-xs font-medium text-slate-500">{localSettings.temperature}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={localSettings.temperature}
                    onChange={(event) => handleChange('temperature', parseFloat(event.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs leading-5 text-slate-500">控制回答发散程度。越低越稳定，越高越灵活。</p>
                </div>

                <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                      <span>Top K</span>
                      <span className="text-xs font-medium text-slate-500">1 - 30</span>
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="30"
                      step="1"
                      value={localSettings.topK}
                      onChange={(event) => handleTopKChange(event.target.value)}
                      className="w-28 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                  <p className="text-xs leading-5 text-slate-500">控制检索参考范围。数值越大，覆盖越广，但速度可能变慢。</p>
                </div>
              </div>

              <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-700">链接测试</p>
                    <p className="text-xs text-slate-500">检查内置检索接口和本地模型中转是否可用。模型接口测试超时已放宽到 60 秒，测试期间不会关闭弹窗。</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleTestLinks}
                    disabled={isTestingLinks}
                    className="inline-flex items-center gap-2 rounded-lg border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isTestingLinks ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />}
                    {isTestingLinks ? '测试中...' : '测试链接'}
                  </button>
                </div>

                {testResult && (
                  <div
                    className={`space-y-1 rounded-lg border px-3 py-2 text-xs ${
                      testResult.kind === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-rose-200 bg-rose-50 text-rose-700'
                    }`}
                  >
                    <p>{testResult.searchMessage}</p>
                    <p>{testResult.modelMessage}</p>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <label className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  <span>流式输出</span>
                  <input type="checkbox" checked={localSettings.streamMode} onChange={(event) => handleChange('streamMode', event.target.checked)} className="h-4 w-4" />
                </label>
                <label className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  <span>DeepSeek 思考模式</span>
                  <input
                    type="checkbox"
                    checked={localSettings.deepseekThinkingMode}
                    onChange={(event) => handleChange('deepseekThinkingMode', event.target.checked)}
                    className="h-4 w-4"
                  />
                </label>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-700">System Prompt</label>
                <textarea
                  value={localSettings.systemPrompt}
                  onChange={(event) => handleChange('systemPrompt', event.target.value)}
                  rows={4}
                  className="w-full resize-none rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-600 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                />
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-3 border-t border-slate-200 bg-slate-50 px-6 py-4">
          <button type="button" onClick={onClose} className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-200">
            取消
          </button>
          <button type="button" onClick={handleSave} className="flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700">
            <Save className="h-4 w-4" />
            保存设置
          </button>
        </div>
      </div>
    </div>
  );
}
