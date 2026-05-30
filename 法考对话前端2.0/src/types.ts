export type Role = 'user' | 'assistant';

export type MessageStatus = 'searching' | 'generating' | 'success' | 'error';
export type StudyMode = 'exam' | 'memorize';

export interface Reference {
  id: string;
  title: string;
  content: string;
  chunkId?: string;
  score?: number;
}

export interface Message {
  id: string;
  role: Role;
  content: string;
  thinking?: string;
  isStreaming?: boolean;
  status?: MessageStatus;
  error?: string;
  references?: Reference[];
}

export interface AppSettings {
  searchApiUrl: string;
  modelBaseUrl: string;
  apiKey: string;
  model: string;
  topK: number;
  temperature: number;
  systemPrompt: string;
  streamMode: boolean;
  deepseekThinkingMode: boolean;
  studyMode: StudyMode;
}

export const defaultSettings: AppSettings = {
  searchApiUrl: '/api/search',
  modelBaseUrl: 'https://api.deepseek.com/v1',
  apiKey: '',
  model: 'deepseek-v4-flash',
  topK: 5,
  temperature: 0.3,
  systemPrompt: '你是专业的法考辅导助手。回答时先识别题型，再用像老师讲题一样的方式组织答案。',
  streamMode: false,
  deepseekThinkingMode: false,
  studyMode: 'exam',
};
