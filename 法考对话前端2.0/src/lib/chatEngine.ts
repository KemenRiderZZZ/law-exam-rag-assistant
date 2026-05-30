import { AppSettings, Message } from '../types';
import { Citation, ConversationMessage, LiveSearchResult } from './chatEngine.types';
import { isStrictExamStyleQuestion } from './chatEngine.cleaners';
import {
  appendReferenceGuide,
  buildReferencesFromCitations,
  buildThinkingSummary,
  formatAssistantAnswer,
} from './chatEngine.formatters';
import {
  buildConversationHistory,
  buildLiveSearchContext,
  buildModelRequestBody,
  buildRetrievalOnlySummary,
  buildSystemPrompt,
  buildUserPrompt,
  filterRelevantCitations,
  inferAnswerStyle,
  isDeepSeekRequest,
  isThoughtRequest,
  shouldUseLiveSearch,
} from './chatEngine.prompt';
import { buildGatewayModelSettings, requestGatewayChat } from './modelApi';

interface RunChatTurnArgs {
  question: string;
  settings: AppSettings;
  messages: Message[];
  onUpdate: (updates: Partial<Message>) => void;
}

const MAX_SEARCH_RESULTS_FOR_ANSWER = 12;
const MAX_CITATIONS_FOR_PROMPT = 8;

async function fetchSearchResults(question: string, settings: AppSettings): Promise<Citation[]> {
  const searchResponse = await fetch(settings.searchApiUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: question, top_k: Math.min(settings.topK, MAX_SEARCH_RESULTS_FOR_ANSWER) }),
  }).catch(() => {
    throw new Error(`无法连接到检索接口：${settings.searchApiUrl}`);
  });

  if (!searchResponse.ok) {
    throw new Error(`检索服务响应异常：${searchResponse.status} ${searchResponse.statusText}`);
  }

  const searchData = await searchResponse.json();
  return searchData.results || searchData.data || (Array.isArray(searchData) ? searchData : []);
}

function extractContentFromGatewayJson(data: any): string {
  return data?.choices?.[0]?.message?.content || data?.choices?.[0]?.delta?.content || '';
}

function extractContentFromSseText(text: string): string {
  return text
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.replace(/^data:\s*/, '').trim())
    .filter((line) => line && line !== '[DONE]')
    .map((line) => {
      try {
        const data = JSON.parse(line);
        const choice = data?.choices?.[0];
        return choice?.delta?.content || choice?.message?.content || '';
      } catch {
        return '';
      }
    })
    .join('');
}

async function readModelAnswer(response: Response): Promise<string> {
  const contentType = response.headers.get('Content-Type') || '';
  const text = await response.text();
  const looksLikeSse = contentType.includes('text/event-stream') || /^\s*data:/m.test(text);

  if (looksLikeSse) {
    return extractContentFromSseText(text);
  }

  try {
    return extractContentFromGatewayJson(JSON.parse(text));
  } catch {
    throw new Error('模型返回格式无法识别，请关闭流式输出后重试');
  }
}

async function fetchLiveSearchContext(question: string): Promise<string> {
  if (!shouldUseLiveSearch(question)) return '';

  try {
    const liveSearchResponse = await fetch('/api/live-search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: question, max_results: 5, auto: false }),
    });

    if (!liveSearchResponse.ok) return '';

    const liveSearchData = await liveSearchResponse.json();
    const liveResults: LiveSearchResult[] = liveSearchData.results || (Array.isArray(liveSearchData) ? liveSearchData : []);
    return typeof liveSearchData.context === 'string' && liveSearchData.context.trim()
      ? liveSearchData.context.trim()
      : buildLiveSearchContext(liveResults);
  } catch {
    return '';
  }
}

async function requestModelAnswer(
  settings: AppSettings,
  requestMessages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>,
  useDeepSeekThinkingMode: boolean,
) {
  const gatewaySettings = buildGatewayModelSettings(settings);
  const body = buildModelRequestBody(settings, gatewaySettings.model, requestMessages, useDeepSeekThinkingMode);
  return requestGatewayChat({
    settings: gatewaySettings,
    body,
  });
}

export async function runChatTurn({ question, settings, messages, onUpdate }: RunChatTurnArgs) {
  const trimmedQuestion = question.trim();
  const conversationHistory = messages.map((message) => ({
    role: message.role,
    content: message.content,
    status: message.status,
  })) as ConversationMessage[];
  const apiKey = settings.apiKey.trim();
  const model = settings.model.trim();
  const baseUrl = settings.modelBaseUrl.trim().replace(/\/+$/, '');
  const systemPrompt = settings.systemPrompt.trim();

  try {
    const rawCitations = await fetchSearchResults(trimmedQuestion, settings);
    const liveSearchContext = await fetchLiveSearchContext(trimmedQuestion);
    const citations = filterRelevantCitations(trimmedQuestion, rawCitations, liveSearchContext).slice(0, MAX_CITATIONS_FOR_PROMPT);
    const references = buildReferencesFromCitations(citations);
    const strictExamMode = isStrictExamStyleQuestion(trimmedQuestion) || isThoughtRequest(trimmedQuestion);
    const thinking = buildThinkingSummary(trimmedQuestion, citations, liveSearchContext);

    onUpdate({
      status: 'generating',
      references,
      thinking,
    });

    if (!apiKey || !model) {
      onUpdate({
        status: 'success',
        content: appendReferenceGuide(buildRetrievalOnlySummary(trimmedQuestion, citations), references),
        references,
        thinking,
      });
      return;
    }

    const requestMessages = [
      {
        role: 'system' as const,
        content: buildSystemPrompt(systemPrompt),
      },
      ...buildConversationHistory(conversationHistory),
      {
        role: 'user' as const,
        content: buildUserPrompt(trimmedQuestion, citations, inferAnswerStyle(trimmedQuestion, citations), liveSearchContext),
      },
    ];
    const useDeepSeekThinkingMode = settings.deepseekThinkingMode && isDeepSeekRequest(baseUrl, model);

    const generationResponse = await requestModelAnswer(settings, requestMessages, useDeepSeekThinkingMode);
    const answer = await readModelAnswer(generationResponse);
    onUpdate({
      status: 'success',
      content: appendReferenceGuide(formatAssistantAnswer(answer, citations, strictExamMode), references),
      references,
      thinking,
      isStreaming: false,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : '系统底层异常';
    onUpdate({
      status: 'error',
      error: message,
      content: '',
      isStreaming: false,
    });
  }
}

