import { AppSettings, defaultSettings, StudyMode } from '../types';

export const BUILT_IN_SEARCH_API_URL = '/api/search';
const SETTINGS_STORAGE_KEY = 'app_settings_v2';
const LEGACY_SETTINGS_STORAGE_KEY = 'app_settings';

function normalizeStudyMode(value: unknown): StudyMode {
  return value === 'memorize' ? 'memorize' : 'exam';
}

function clampTopK(value: number) {
  return Math.min(30, Math.max(1, Math.round(value || 1)));
}

export function getHealthUrl(searchApiUrl: string) {
  return searchApiUrl.replace(/\/search\/?$/, '/health');
}

export function normalizeSettings(source: AppSettings): AppSettings {
  return {
    ...source,
    searchApiUrl: BUILT_IN_SEARCH_API_URL,
    modelBaseUrl: source.modelBaseUrl.trim().replace(/\/+$/, ''),
    apiKey: source.apiKey.trim(),
    model: source.model.trim(),
    systemPrompt: source.systemPrompt.trim(),
    topK: clampTopK(source.topK),
    studyMode: normalizeStudyMode(source.studyMode),
  };
}

export function loadStoredSettings(): AppSettings {
  const storedV2 = localStorage.getItem(SETTINGS_STORAGE_KEY);
  if (storedV2) {
    try {
      return normalizeSettings({ ...defaultSettings, ...JSON.parse(storedV2) });
    } catch {
      // Fall through to legacy migration.
    }
  }

  const legacyStored = localStorage.getItem(LEGACY_SETTINGS_STORAGE_KEY);
  if (legacyStored) {
    try {
      const legacy = JSON.parse(legacyStored);
      return normalizeSettings({
        ...defaultSettings,
        modelBaseUrl: typeof legacy.apiBaseUrl === 'string' ? legacy.apiBaseUrl : defaultSettings.modelBaseUrl,
        apiKey: typeof legacy.apiKey === 'string' ? legacy.apiKey : defaultSettings.apiKey,
        model: typeof legacy.model === 'string' ? legacy.model : defaultSettings.model,
        topK: typeof legacy.searchTopK === 'number' ? legacy.searchTopK : defaultSettings.topK,
        temperature: typeof legacy.temperature === 'number' ? legacy.temperature : defaultSettings.temperature,
        systemPrompt: typeof legacy.systemPrompt === 'string' ? legacy.systemPrompt : defaultSettings.systemPrompt,
        streamMode: typeof legacy.streamMode === 'boolean' ? legacy.streamMode : defaultSettings.streamMode,
        deepseekThinkingMode:
          typeof legacy.deepseekThinkingMode === 'boolean'
            ? legacy.deepseekThinkingMode
            : defaultSettings.deepseekThinkingMode,
        studyMode: normalizeStudyMode(legacy.studyMode),
        searchApiUrl: BUILT_IN_SEARCH_API_URL,
      });
    } catch {
      return normalizeSettings(defaultSettings);
    }
  }

  return normalizeSettings(defaultSettings);
}

export function persistSettings(settings: AppSettings) {
  localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(normalizeSettings(settings)));
}
