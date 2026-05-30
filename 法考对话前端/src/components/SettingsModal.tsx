import React from 'react';
import { X } from 'lucide-react';
import { AppSettings } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: AppSettings;
  onSave: (s: AppSettings) => void;
}

export function SettingsModal({ isOpen, onClose, settings, onSave }: SettingsModalProps) {
  const [local, setLocal] = React.useState<AppSettings>(settings);
  const [testState, setTestState] = React.useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [testMessage, setTestMessage] = React.useState('');

  React.useEffect(() => {
    if (isOpen) {
      setLocal(settings);
      setTestState('idle');
      setTestMessage('');
    }
  }, [isOpen, settings]);

  if (!isOpen) return null;

  const handleChange = (field: keyof AppSettings, value: string | number | boolean) => {
    setLocal((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = () => {
    onSave({
      ...local,
      searchApiUrl: local.searchApiUrl.trim(),
      apiBaseUrl: local.apiBaseUrl.trim().replace(/\/+$/, ''),
      apiKey: local.apiKey.trim(),
      model: local.model.trim(),
      systemPrompt: local.systemPrompt.trim(),
    });
    onClose();
  };

  const handleTestConnection = async () => {
    const baseUrl = local.apiBaseUrl.trim().replace(/\/+$/, '');
    const apiKey = local.apiKey.trim();
    const model = local.model.trim();
    const isDeepSeek =
      baseUrl.toLowerCase().includes('deepseek.com') ||
      baseUrl.toLowerCase().includes('deepseek.cn') ||
      model.toLowerCase().startsWith('deepseek');

    if (!baseUrl) {
      setTestState('error');
      setTestMessage('请先填写 Base URL。');
      return;
    }

    if (!apiKey) {
      setTestState('error');
      setTestMessage('请先填写 API Key。');
      return;
    }

    if (!model) {
      setTestState('error');
      setTestMessage('请先填写模型名称。');
      return;
    }

    setTestState('loading');
    setTestMessage('正在测试模型链接...');

    try {
      const requestBody: Record<string, unknown> = {
        model,
        messages: [{ role: 'user', content: '请只回复：ok' }],
        max_tokens: 8,
        stream: false,
      };

      if (local.deepseekThinkingMode && isDeepSeek) {
        requestBody.reasoning_effort = 'high';
        requestBody.extra_body = {
          thinking: { type: 'enabled' },
        };
      } else {
        requestBody.temperature = 0;
      }

      const response = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${apiKey}`,
        },
        body: JSON.stringify(requestBody),
      });

      let payload: any = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      if (!response.ok) {
        const detail =
          payload?.error?.message ||
          payload?.message ||
          `${response.status} ${response.statusText}`.trim();
        throw new Error(detail);
      }

      const content = payload?.choices?.[0]?.message?.content?.trim() || 'ok';
      setTestState('success');
      setTestMessage(`测试成功：${content}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : '连接测试失败';
      const looksLikeCors =
        message.includes('Failed to fetch') ||
        message.includes('NetworkError') ||
        message.includes('Load failed');

      setTestState('error');
      setTestMessage(
        looksLikeCors
          ? '测试失败：浏览器无法直接访问该模型接口，可能是跨域限制、网络拦截或 Base URL 不可达。'
          : `测试失败：${message}`,
      );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-gray-800">连接配置</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">检索接口 (Search API)</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              value={local.searchApiUrl}
              onChange={(e) => handleChange('searchApiUrl', e.target.value)}
              placeholder="http://localhost:8000/api/search"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">模型接口 (Base URL)</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              value={local.apiBaseUrl}
              onChange={(e) => handleChange('apiBaseUrl', e.target.value)}
              placeholder="https://api.openai.com/v1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <input
              type="password"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              value={local.apiKey}
              onChange={(e) => handleChange('apiKey', e.target.value)}
              placeholder="sk-..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">模型名称 (Model)</label>
            <input
              type="text"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
              value={local.model}
              onChange={(e) => handleChange('model', e.target.value)}
              placeholder="gpt-4o-mini"
            />
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2.5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[13px] font-medium leading-5 text-gray-800">模型链接测试</p>
                <p className="mt-0.5 text-[11px] leading-4 text-gray-500">
                  用当前 Base URL、API Key 和模型名发起一次最小请求。
                </p>
              </div>
              <button
                type="button"
                onClick={handleTestConnection}
                disabled={testState === 'loading'}
                className="shrink-0 rounded-md bg-blue-50 px-2.5 py-1.5 text-xs font-medium text-blue-700 transition-colors hover:bg-blue-100 disabled:bg-gray-200 disabled:text-gray-400"
              >
                {testState === 'loading' ? '测试中...' : '测试链接'}
              </button>
            </div>

            {testState !== 'idle' && (
              <div
                className={`mt-2 rounded-md px-2.5 py-1.5 text-xs leading-5 ${
                  testState === 'success'
                    ? 'border border-green-100 bg-green-50 text-green-700'
                    : testState === 'error'
                      ? 'border border-red-100 bg-red-50 text-red-700'
                      : 'border border-blue-100 bg-blue-50 text-blue-700'
                }`}
              >
                {testMessage}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between py-2 border-y border-gray-100">
            <label className="text-sm font-medium text-gray-700">流式输出 (Stream)</label>
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 bg-gray-50 text-blue-600 focus:ring-blue-500"
              checked={local.streamMode}
              onChange={(e) => handleChange('streamMode', e.target.checked)}
            />
          </div>

          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <div className="pr-4">
              <label className="text-sm font-medium text-gray-700">DeepSeek 思考模式</label>
              <p className="mt-0.5 text-[11px] leading-4 text-gray-500">
                仅在 DeepSeek 接口下生效，请求会自动注入 thinking 参数。
              </p>
            </div>
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 bg-gray-50 text-blue-600 focus:ring-blue-500"
              checked={local.deepseekThinkingMode}
              onChange={(e) => handleChange('deepseekThinkingMode', e.target.checked)}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Top K (检索数)</label>
              <input
                type="number"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                value={local.searchTopK}
                onChange={(e) => handleChange('searchTopK', Number(e.target.value))}
                min={1}
                max={20}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">温度 (Temp)</label>
              <input
                type="number"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500"
                value={local.temperature}
                onChange={(e) => handleChange('temperature', Number(e.target.value))}
                min={0}
                max={2}
                step={0.1}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">系统提示词 (System Prompt)</label>
            <textarea
              className="h-24 w-full resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
              value={local.systemPrompt}
              onChange={(e) => handleChange('systemPrompt', e.target.value)}
            />
          </div>
        </div>

        <div className="mt-8 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-lg bg-gray-50 px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-100 hover:text-gray-900"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
          >
            保存并应用
          </button>
        </div>
      </div>
    </div>
  );
}
