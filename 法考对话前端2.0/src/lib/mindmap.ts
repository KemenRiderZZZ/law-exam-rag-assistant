import { AppSettings, Message } from '../types';
import { buildGatewayModelSettings, requestGatewayMindmap } from './modelApi';
interface GenerateMindmapArgs {
  settings: AppSettings;
  messages: Message[];
  draftInput: string;
}

export interface MindmapNode {
  id: string;
  lineIndex: number;
  level: number;
  raw: string;
  text: string;
  type: 'heading' | 'bullet';
  parentId: string | null;
}

interface GeneratedMindmap {
  title: string;
  markdown: string;
}

interface ExpandMindmapNodeArgs {
  settings: AppSettings;
  markdown: string;
  nodeId: string;
  title: string;
}

interface ExpandMindmapNodeResult {
  markdown: string;
  selectedNodeId: string;
}

const DEFAULT_TOPIC = '法考知识点';
const DETAIL_SPLIT_REGEX = /[，。；;]/;
const PERSISTENCE_NAMESPACE = 'law-mindmap-draft';

interface NormalizeOutlineOptions {
  fallbackTopic: string;
  mode?: 'document' | 'expansion';
  skipHeadingText?: string;
}

function getLastStackId(stack: Array<{ id: string; level: number }>) {
  return stack.length ? stack[stack.length - 1].id : null;
}

function stripMarkdown(text: string): string {
  return text
    .replace(/\r/g, '')
    .replace(/```[\s\S]*?```/g, '')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function sanitizeHeading(text: string): string {
  const normalized = stripMarkdown(text)
    .replace(/[\u0000-\u001f]/g, ' ')
    .replace(/[<>]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return normalized || DEFAULT_TOPIC;
}

function splitDetailLine(text: string): string[] {
  return text
    .split(DETAIL_SPLIT_REGEX)
    .map((item) => item.trim())
    .filter(Boolean);
}

function collectSentences(text: string): string[] {
  return stripMarkdown(text)
    .split('\n')
    .flatMap((line) => splitDetailLine(line))
    .map((line) => line.replace(/[:：].*$/, '').trim())
    .filter((line) => line.length >= 4);
}

type MindmapDetailMode = 'compact' | 'standard' | 'detailed';

interface MindmapDetailProfile {
  mode: MindmapDetailMode;
  maxTokens: number;
  answerSlice: number;
  currentMapSlice: number;
  systemHints: string[];
  userHints: string[];
}

function inferMindmapDetailProfile(args: {
  topic: string;
  question?: string;
  answer?: string;
}): MindmapDetailProfile {
  const combined = `${args.topic}\n${args.question || ''}\n${args.answer || ''}`;
  const answerLength = stripMarkdown(args.answer || '').length;
  const looksLargeScope =
    /整本|全书|全册|体系|总则|分则|整部|完整|全面|框架|通览|总论|专题讲座|整章|整编/.test(combined) ||
    /刑法|民法|刑诉|民诉|行政法|商经知|三国法|理论法/.test(combined);
  const looksDetailRequest = /详细|展开|完整一点|尽量全|细一点|细化|底层逻辑|全面/.test(combined);
  const looksSmallScope = /一道题|单个|某一条|一个罪|一个知识点|一个考点|简版|速记|口诀/.test(combined);

  if ((looksLargeScope && looksDetailRequest) || /大纲/.test(combined) || answerLength > 2600) {
    return {
      mode: 'detailed',
      maxTokens: 5200,
      answerSlice: 12000,
      currentMapSlice: 10000,
      systemHints: [
        'Adapt the outline density to the scope. For a whole book, subject, chapter system, or complete review map, expand more fully instead of giving a tiny skeleton.',
        'For large-scope topics, prefer 6 to 12 H2 branches when the material supports it, 3 to 6 H3 sub-branches under important H2 branches, and 3 to 6 layered bullets under each key sub-branch.',
        'Important branches should not stop at labels only. Add the actual knowledge points, elements, distinctions, exceptions, conditions, effects, and common traps as child bullets.',
      ],
      userHints: [
        'If the topic is a whole subject, whole book, or system review outline, make it noticeably fuller and more teaching-oriented.',
        'Do not stop at only a thin frame such as 概念 / 构成 / 总结. Fill in the concrete points that a student would actually memorize or compare.',
      ],
    };
  }

  if (looksSmallScope && !looksDetailRequest && answerLength < 1200) {
    return {
      mode: 'compact',
      maxTokens: 2200,
      answerSlice: 5000,
      currentMapSlice: 5000,
      systemHints: ['Keep the map concise for narrow topics, but still include the core legal points needed for understanding and memory.'],
      userHints: ['Keep it readable and compact for a single doctrine or single-question topic.'],
    };
  }

  return {
    mode: 'standard',
    maxTokens: 3200,
    answerSlice: 8000,
    currentMapSlice: 7000,
    systemHints: ['Balance structure and detail. Do not be too thin: each important branch should contain the actual rule points, not just empty labels.'],
    userHints: ['Make the outline complete enough for study and memory, not just a bare title tree.'],
  };
}

function getLatestSuccessfulAssistant(messages: Message[]): Message | null {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role === 'assistant' && message.status === 'success' && message.content.trim()) {
      return message;
    }
  }
  return null;
}

function getLatestUserQuestion(messages: Message[]): string {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.role === 'user' && message.content.trim()) {
      return message.content.trim();
    }
  }
  return '';
}

function extractCodeBlock(raw: string): string {
  const fenced = raw.match(/```(?:markdown|md)?\s*([\s\S]*?)```/i);
  return fenced?.[1]?.trim() || raw.trim();
}

function isOutlineLine(line: string): boolean {
  const trimmed = line.trim();
  return /^#{1,6}\s+/.test(trimmed) || /^[-*+]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed);
}

function sanitizeBullet(text: string): string {
  return sanitizeHeading(text).replace(/^[-*+]\s+/, '');
}

function normalizeRelativeHeadingLevel(level: number, baseLevel: number, minLevel: number, maxLevel: number) {
  const relativeLevel = level - baseLevel + minLevel;
  return Math.max(minLevel, Math.min(relativeLevel, maxLevel));
}

function pushBulletWithSplits(target: string[], rawText: string, indentLevel = 0) {
  const normalized = sanitizeBullet(rawText);
  if (!normalized) return;

  const pieces = splitDetailLine(normalized);
  const prefix = `${'  '.repeat(indentLevel)}- `;

  if (pieces.length <= 1) {
    target.push(`${prefix}${normalized}`);
    return;
  }

  const [first, ...rest] = pieces;
  if (first) {
    target.push(`${prefix}${sanitizeBullet(first)}`);
  }

  rest.forEach((piece) => {
    target.push(`${'  '.repeat(indentLevel + 1)}- ${sanitizeBullet(piece)}`);
  });
}

function normalizeOutlineLines(raw: string, options: NormalizeOutlineOptions): string[] {
  const { fallbackTopic, mode = 'document', skipHeadingText } = options;
  const source = extractCodeBlock(raw);
  if (!source) {
    return [];
  }

  const rawLines = source
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.replace(/\t/g, '  ').trimEnd())
    .filter((line) => line.trim());

  if (!rawLines.length) {
    return [];
  }

  const outlineLike = rawLines.some(isOutlineLine);
  if (!outlineLike) {
    const sentences = collectSentences(source);
    if (!sentences.length) return [];
    if (mode === 'expansion') {
      return sentences.map((line) => `- ${sanitizeBullet(line)}`);
    }
    const lines = [`# ${sanitizeHeading(fallbackTopic)}`, '## 模型原始整理'];
    sentences.forEach((line) => pushBulletWithSplits(lines, line));
    return lines;
  }

  const normalized: string[] = [];
  let hasDocumentRoot = false;
  let lastHeadingLevel = 1;
  let baseHeadingLevel: number | null = null;
  const normalizedSkipHeading = skipHeadingText ? sanitizeHeading(skipHeadingText) : '';

  rawLines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) return;

    if (/^#{1,6}\s+/.test(trimmed)) {
      const level = trimmed.match(/^#{1,6}/)?.[0].length || 1;
      const content = sanitizeHeading(trimmed.replace(/^#{1,6}\s+/, ''));

      if (mode === 'document') {
        if (!hasDocumentRoot) {
          normalized.push(`# ${content}`);
          hasDocumentRoot = true;
          lastHeadingLevel = 1;
          baseHeadingLevel = level;
          return;
        }

        const safeLevel = normalizeRelativeHeadingLevel(level, baseHeadingLevel ?? level, 2, 4);
        normalized.push(`${'#'.repeat(safeLevel)} ${content}`);
        lastHeadingLevel = safeLevel;
        return;
      }

      if (!content || content === normalizedSkipHeading) return;
      if (baseHeadingLevel === null) {
        baseHeadingLevel = level;
      }

      const safeLevel = normalizeRelativeHeadingLevel(level, baseHeadingLevel, 3, 4);
      normalized.push(`${'#'.repeat(safeLevel)} ${content}`);
      return;
    }

    const bulletText = /^[-*+]\s+/.test(trimmed)
      ? trimmed.replace(/^[-*+]\s+/, '')
      : /^\d+\.\s+/.test(trimmed)
        ? trimmed.replace(/^\d+\.\s+/, '')
        : trimmed;

    if (mode === 'document') {
      if (!hasDocumentRoot) {
        normalized.push(`# ${sanitizeHeading(fallbackTopic)}`);
        hasDocumentRoot = true;
        lastHeadingLevel = 1;
      }
      if (lastHeadingLevel < 3) {
        normalized.push('### 关键点');
        lastHeadingLevel = 3;
      }
      pushBulletWithSplits(normalized, bulletText);
      return;
    }

    pushBulletWithSplits(normalized, bulletText);
  });

  if (mode === 'document' && !hasDocumentRoot) {
    normalized.unshift(`# ${sanitizeHeading(fallbackTopic)}`);
  }

  return normalized.filter((line) => line.trim());
}

function normalizeMarkdownOutline(raw: string, fallbackTopic: string): string {
  const normalizedLines = normalizeOutlineLines(raw, { fallbackTopic });
  if (!normalizedLines.length) {
    return `# ${sanitizeHeading(fallbackTopic)}`;
  }

  return normalizedLines.join('\n');
}

function normalizeGeneratedMarkdownOutline(raw: string, fallbackTopic: string): string {
  const normalizedLines = normalizeOutlineLines(raw, { fallbackTopic });
  if (!normalizedLines.length) {
    throw new Error('模型已响应，但返回内容无法整理成思维导图大纲。请让模型输出 Markdown 标题或项目符号后重试。');
  }

  return normalizedLines.join('\n');
}

function stableHash(value: string): string {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16);
}

export function getMindmapDraftStorageKey(title: string, markdown: string) {
  return `${PERSISTENCE_NAMESPACE}:${stableHash(`${title}\n${markdown}`)}`;
}

export function parseMindmapNodes(markdown: string): MindmapNode[] {
  const lines = normalizeMarkdownOutline(markdown, DEFAULT_TOPIC).split('\n');
  const nodes: MindmapNode[] = [];
  const stack: Array<{ id: string; level: number }> = [];

  lines.forEach((rawLine, lineIndex) => {
    const trimmed = rawLine.trim();
    if (!trimmed) return;

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      while (stack.length && stack[stack.length - 1].level >= level) {
        stack.pop();
      }
      const node: MindmapNode = {
        id: `line-${lineIndex}`,
        lineIndex,
        level,
        raw: rawLine,
        text: sanitizeHeading(headingMatch[2]),
        type: 'heading',
        parentId: getLastStackId(stack),
      };
      nodes.push(node);
      stack.push({ id: node.id, level });
      return;
    }

    const bulletMatch = rawLine.match(/^(\s*)-\s+(.*)$/);
    if (bulletMatch) {
      const indentSpaces = bulletMatch[1].length;
      const bulletLevel = 4 + Math.floor(indentSpaces / 2);
      while (stack.length && stack[stack.length - 1].level >= bulletLevel) {
        stack.pop();
      }
      const node: MindmapNode = {
        id: `line-${lineIndex}`,
        lineIndex,
        level: bulletLevel,
        raw: rawLine,
        text: sanitizeBullet(bulletMatch[2]),
        type: 'bullet',
        parentId: getLastStackId(stack),
      };
      nodes.push(node);
      stack.push({ id: node.id, level: bulletLevel });
    }
  });

  return nodes;
}

export function getNodePath(markdown: string, nodeId: string): string[] {
  const nodes = parseMindmapNodes(markdown);
  const map = new Map(nodes.map((node) => [node.id, node]));
  const path: string[] = [];
  let current = map.get(nodeId);

  while (current) {
    path.unshift(current.text);
    current = current.parentId ? map.get(current.parentId) || null : null;
  }

  return path;
}

export function insertChildMarkdown(markdown: string, nodeId: string, childMarkdown: string): string {
  const normalizedBase = normalizeMarkdownOutline(markdown, DEFAULT_TOPIC);
  const baseLines = normalizedBase.split('\n');
  const nodes = parseMindmapNodes(normalizedBase);
  const target = nodes.find((node) => node.id === nodeId);
  if (!target) return normalizedBase;

  const childLines = normalizeOutlineLines(childMarkdown, {
    fallbackTopic: DEFAULT_TOPIC,
    mode: 'expansion',
    skipHeadingText: target.text,
  });
  if (!childLines.length) return normalizedBase;

  const converted: string[] = [];
  const targetHeadingLevel = Math.max(2, Math.min(target.level + (target.type === 'heading' ? 1 : 0), 4));

  childLines.forEach((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) return;

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const sourceLevel = headingMatch[1].length;
      const content = sanitizeHeading(headingMatch[2]);
      if (index === 0) {
        converted.push(`${'#'.repeat(targetHeadingLevel)} ${content}`);
      } else {
        const nextLevel = Math.max(targetHeadingLevel, Math.min(sourceLevel + targetHeadingLevel - 1, 4));
        converted.push(`${'#'.repeat(nextLevel)} ${content}`);
      }
      return;
    }

    const bulletMatch = line.match(/^(\s*)-\s+(.*)$/);
    if (bulletMatch) {
      const spaces = bulletMatch[1].length;
      const indent = target.type === 'bullet' ? 1 + Math.floor(spaces / 2) : Math.floor(spaces / 2);
      converted.push(`${'  '.repeat(Math.max(indent, 0))}- ${sanitizeBullet(bulletMatch[2])}`);
      return;
    }

    converted.push(`- ${sanitizeBullet(trimmed)}`);
  });

  const nextSiblingIndex =
    nodes.find((node) => node.lineIndex > target.lineIndex && node.level <= target.level)?.lineIndex ?? baseLines.length;

  const output = [...baseLines.slice(0, nextSiblingIndex), ...converted, ...baseLines.slice(nextSiblingIndex)];
  return normalizeMarkdownOutline(output.join('\n'), DEFAULT_TOPIC);
}

async function requestMindmapFromModel(args: {
  settings: AppSettings;
  topic: string;
  answer: string;
  question: string;
}): Promise<string> {
  const gatewaySettings = buildGatewayModelSettings(args.settings);
  if (!gatewaySettings.baseUrl || !gatewaySettings.apiKey || !gatewaySettings.model) {
    throw new Error('模型配置不完整。请先在设置里填写 Base URL、模型名称和 API Key，本次没有继续发起生成。');
  }

  const detailProfile = inferMindmapDetailProfile(args);
  const body = {
    model: gatewaySettings.model,
    stream: false,
    temperature: 0.2,
    max_tokens: detailProfile.maxTokens,
    messages: [
      {
        role: 'system',
        content: [
          'You generate law-exam study markmap outlines.',
          'Return only markmap-compatible Markdown.',
          'Wrap the answer in a ```markdown code block.',
          'Use a strict hierarchy with heading outline only.',
          'The first line must be one H1 title.',
          'Choose outline density based on topic scope instead of forcing one fixed size.',
          'For ordinary topics, usually use 4 to 8 H2 branches; for whole-book or whole-subject topics, you may use 6 to 12 H2 branches when supported by the material.',
          'Under each H2, create enough H3 sub-branches to cover the actual knowledge structure, such as 概念定位, 体系位置, 构成要件, 核心判断, 适用条件, 例外, 区分点, 易错点, 记忆抓手.',
          'Under each H3, use layered bullet points that contain concrete knowledge points, not only labels.',
          'Keep 概念定位 and 总结记忆 as separate branches, never merge them into one mixed final section.',
          'Do not place orphan H3 headings at the end without belonging to an H2 branch.',
          'Never place multiple clauses joined by semicolons in the same bullet.',
          'If a point contains multiple facts, split them into separate child bullets.',
          'If the user asks for a complete outline, prefer fuller coverage over excessive brevity.',
          'Do not output Mermaid, JSON, XML, HTML, or explanation text.',
          ...detailProfile.systemHints,
        ].join(' '),
      },
      {
        role: 'user',
        content: [
          `Topic: ${args.topic || DEFAULT_TOPIC}`,
          args.question ? `Question: ${args.question}` : '',
          args.answer ? `Answer material:\n${stripMarkdown(args.answer).slice(0, detailProfile.answerSlice)}` : '',
          'Please convert this into a layered review outline for law-exam study.',
          'Important: keep the structure readable for a mind map, and split long sentences into lower levels instead of one long node.',
          ...detailProfile.userHints,
        ]
          .filter(Boolean)
          .join('\n\n'),
      },
    ],
  };
  const payload = await requestGatewayMindmap({
    settings: gatewaySettings,
    body,
  });
  const content = String(payload.content || '').trim();
  if (!content) {
    throw new Error('模型没有返回可用于生成思维导图的正文内容');
  }
  return content;
}

async function requestNodeExpansionFromModel(args: {
  settings: AppSettings;
  title: string;
  markdown: string;
  nodePath: string[];
  nodeText: string;
}): Promise<string> {
  const gatewaySettings = buildGatewayModelSettings(args.settings);
  if (!gatewaySettings.baseUrl || !gatewaySettings.apiKey || !gatewaySettings.model) {
    throw new Error('模型配置不完整。请先在设置里填写 Base URL、模型名称和 API Key，本次没有继续发起扩写。');
  }

  const detailProfile = inferMindmapDetailProfile({
    topic: args.title,
    question: args.nodePath.join(' > '),
    answer: args.markdown,
  });
  const body = {
    model: gatewaySettings.model,
    stream: false,
    temperature: 0.25,
    max_tokens: Math.min(detailProfile.maxTokens, 3200),
    messages: [
      {
        role: 'system',
        content: [
          'You expand one selected node inside a law-exam markmap outline.',
          'Return only markdown for the selected node children.',
          'Do not rewrite the whole map.',
          'Use this structure: one H3 or H4 heading plus bullet points, or multiple bullet groups.',
          'Keep the output layered and suitable for mind map expansion.',
          'If the selected node is broad, expand it with enough child levels and concrete knowledge points instead of only a few thin bullets.',
          'Do not repeat the selected node text as a new heading.',
          'Never put multiple semicolon clauses inside one bullet.',
          'Do not output explanations before or after the markdown.',
          ...detailProfile.systemHints,
        ].join(' '),
      },
      {
        role: 'user',
        content: [
          `Map title: ${args.title}`,
          `Selected node path: ${args.nodePath.join(' > ')}`,
          `Selected node text: ${args.nodeText}`,
          `Current map markdown:\n${args.markdown.slice(0, detailProfile.currentMapSlice)}`,
          'Please expand only the selected node with new child levels.',
          'If this node is a broad chapter, doctrine, or system section, fill in more of the concrete study points instead of stopping at two or three thin bullets.',
        ].join('\n\n'),
      },
    ],
  };
  const payload = await requestGatewayMindmap({
    settings: gatewaySettings,
    body,
  });
  return String(payload.content || '').trim();
}

export async function generateMindmap({ settings, messages, draftInput }: GenerateMindmapArgs): Promise<GeneratedMindmap> {
  const latestAssistant = getLatestSuccessfulAssistant(messages);
  const latestQuestion = draftInput.trim() || getLatestUserQuestion(messages) || DEFAULT_TOPIC;
  const title = latestQuestion.length > 24 ? `${latestQuestion.slice(0, 24)}...` : latestQuestion;
  const sourceAnswer = latestAssistant?.content || '';

  const modelOutline = await requestMindmapFromModel({
    settings,
    topic: title,
    answer: sourceAnswer,
    question: latestQuestion,
  });

  return {
    title,
    markdown: normalizeGeneratedMarkdownOutline(modelOutline, title),
  };
}

export async function expandMindmapNode({
  settings,
  markdown,
  nodeId,
  title,
}: ExpandMindmapNodeArgs): Promise<ExpandMindmapNodeResult> {
  const normalized = normalizeMarkdownOutline(markdown, title || DEFAULT_TOPIC);
  const nodes = parseMindmapNodes(normalized);
  const target = nodes.find((node) => node.id === nodeId);

  if (!target) {
    throw new Error('没有找到当前选中的导图节点。请重新点选大纲中的一行后再扩写。');
  }

  const nodePath = getNodePath(normalized, nodeId);
  const expansion = await requestNodeExpansionFromModel({
    settings,
    title,
    markdown: normalized,
    nodePath,
    nodeText: target.text,
  });

  const nextMarkdown = insertChildMarkdown(normalized, nodeId, expansion);

  return {
    markdown: nextMarkdown,
    selectedNodeId: nodeId,
  };
}

