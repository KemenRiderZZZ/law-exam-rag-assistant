import { AppSettings } from '../types';

export interface ModelGatewaySettings {
  baseUrl: string;
  apiKey: string;
  model: string;
  temperature?: number;
  streamMode?: boolean;
  deepseekThinkingMode?: boolean;
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : '未知错误';
}

async function parseGatewayError(response: Response, fallback = '模型接口调用失败') {
  try {
    const payload = await response.json();
    const detail = typeof payload?.error === 'string' ? payload.error : response.statusText;
    return `${fallback}：${detail || `HTTP ${response.status}`}`;
  } catch {
    return `${fallback}：${response.statusText || `HTTP ${response.status}`}`;
  }
}

export function buildGatewayModelSettings(settings: AppSettings): ModelGatewaySettings {
  return {
    baseUrl: settings.modelBaseUrl.trim().replace(/\/+$/, ''),
    apiKey: settings.apiKey.trim(),
    model: settings.model.trim(),
    temperature: settings.temperature,
    streamMode: settings.streamMode,
    deepseekThinkingMode: settings.deepseekThinkingMode,
  };
}

export async function testModelGateway(settings: ModelGatewaySettings, timeoutMs = 60000) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch('/api/model-test', {
      method: 'POST',
      signal: controller.signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });

    if (!response.ok) {
      throw new Error(await parseGatewayError(response, '模型接口测试失败'));
    }

    return response.json();
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`请求超时（${Math.round(timeoutMs / 1000)} 秒）`);
    }
    throw new Error(getErrorMessage(error));
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function requestGatewayChat(payload: {
  settings: ModelGatewaySettings;
  body: Record<string, unknown>;
}) {
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await parseGatewayError(response));
    }

    return response;
  } catch (error) {
    throw new Error(`连接本地模型中转失败：${getErrorMessage(error)}`);
  }
}

export async function requestGatewayMindmap(payload: {
  settings: ModelGatewaySettings;
  body: Record<string, unknown>;
}) {
  try {
    const response = await fetch('/api/mindmap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await parseGatewayError(response, '思维导图接口调用失败'));
    }

    const data = await response.json();
    if (!data?.ok) {
      throw new Error(typeof data?.error === 'string' ? data.error : '思维导图接口调用失败');
    }
    return data;
  } catch (error) {
    throw new Error(`连接本地模型中转失败：${getErrorMessage(error)}`);
  }
}
