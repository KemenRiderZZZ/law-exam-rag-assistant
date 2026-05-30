export interface Citation {
  chunk_id?: string;
  book_name?: string;
  chapter?: string;
  section?: string;
  subsection?: string;
  source_line_start?: number;
  source_line_end?: number;
  text_content?: string;
  score?: number;
}

export type MessageStatus = 'loading' | 'searching' | 'generating' | 'success' | 'error';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  status?: MessageStatus;
  citations?: Citation[];
  error?: string;
}

export interface AppSettings {
  apiBaseUrl: string;
  apiKey: string;
  model: string;
  deepseekThinkingMode: boolean;
  streamMode: boolean;
  searchTopK: number;
  searchApiUrl: string;
  systemPrompt: string;
  temperature: number;
}
