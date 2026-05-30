import { Message } from '../types';

export interface Citation {
  chunk_id?: string;
  text_content?: string;
  score?: number;
  title?: string;
}

export interface LiveSearchResult {
  title?: string;
  link?: string;
  snippet?: string;
  page_title?: string;
  page_excerpt?: string;
  published_at?: string;
  effective_at?: string;
  status?: string;
  authority?: string;
}

export type AnswerMode = 'exam' | 'reasoning' | 'comparison' | 'concept' | 'knowledge';
export type ConversationMessage = Pick<Message, 'role' | 'content' | 'status'>;
