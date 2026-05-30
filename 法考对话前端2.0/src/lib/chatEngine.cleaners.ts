import { Citation } from './chatEngine.types';

const SOURCE_STYLE_TITLE_PATTERN = /(法考知识片段|知识片段|法考知识点|知识点)\s*\d*/i;
const LAW_NAME_PATTERN = /(?:《)?(?:中华人民共和国)?[\u4e00-\u9fa5A-Za-z]{2,30}(?:法|条例|规定|办法|解释|决定)(?:》)?/g;
const ARTICLE_PATTERN = /第[一二三四五六七八九十百千万零〇0-9]+条(?:之[一二三四五六七八九十百千万零〇0-9]+)?/g;

export function normalizeInlineText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function countMatches(text: string, pattern: RegExp): number {
  return text.match(pattern)?.length || 0;
}

export function sanitizeSourceLabel(value?: string): string {
  const normalized = (value || '').replace(/\s+/g, ' ').trim();
  if (!normalized) return '';
  return normalized
    .replace(/[\(\uff08]\s*20\d{2}\s*\u7248\s*[\)\uff09]/g, '')
    .replace(/[\u300a\u300b]/g, '')
    .trim();
}

function sanitizeLawName(value: string): string {
  return sanitizeSourceLabel(value).replace(/^中华人民共和国/, '中华人民共和国').trim();
}

function isSourceStyledTitle(value?: string): boolean {
  const normalized = sanitizeSourceLabel(value);
  return !normalized || SOURCE_STYLE_TITLE_PATTERN.test(normalized);
}

export function extractLegalBasisEntries(text: string): string[] {
  const normalizedLines = (text || '')
    .replace(/\r/g, '')
    .split(/(?<=[。！？；])\s*|\n+/)
    .map((line) => normalizeInlineText(line))
    .filter(Boolean);

  const entries: string[] = [];
  const seen = new Set<string>();
  let lastLawName = '';

  for (const line of normalizedLines) {
    const lawMatches = [...line.matchAll(LAW_NAME_PATTERN)].map((match) => sanitizeLawName(match[0]));
    const articleMatches = [...line.matchAll(ARTICLE_PATTERN)].map((match) => match[0]);

    if (lawMatches.length) {
      lastLawName = lawMatches[lawMatches.length - 1];
    }

    if (!articleMatches.length) continue;

    const lawName = lawMatches[lawMatches.length - 1] || lastLawName;
    let snippet = line;

    if (lawName && !snippet.includes(lawName)) {
      snippet = `${lawName} ${snippet}`;
    }

    snippet = snippet.replace(/\s+/g, ' ').trim();
    if (!snippet) continue;

    if (!seen.has(snippet)) {
      seen.add(snippet);
      entries.push(snippet);
    }

    if (entries.length >= 4) break;
  }

  return entries;
}

export function extractLegalBasisTitle(citation: Citation, index: number): string {
  const directTitle = sanitizeSourceLabel(citation.title);
  if (directTitle && !isSourceStyledTitle(directTitle)) {
    return directTitle;
  }

  const basisEntries = extractLegalBasisEntries(citation.text_content || '');
  if (basisEntries.length) {
    const firstEntry = basisEntries[0];
    const lawName = firstEntry.match(LAW_NAME_PATTERN)?.[0];
    const article = firstEntry.match(ARTICLE_PATTERN)?.[0];
    if (lawName && article) return `${sanitizeLawName(lawName)} ${article}`;
    if (article) return article;
  }

  return `法条依据 ${index + 1}`;
}

export function repairOcrNoiseLine(text: string): string {
  return text
    .replace(/[ ]/g, ' ')
    .replace(/[|｜]{2,}/g, '；')
    .replace(/\s*[|｜]\s*/g, '；')
    .replace(/[※★☆◆■□◇○●△▽▼◉✦✧✱✳✴]/g, '')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\s*[—–-]{2,}\s*/g, ' ')
    .replace(/\s*[=~_]{2,}\s*/g, ' ')
    .replace(/；{2,}/g, '；')
    .replace(/，{2,}/g, '，')
    .replace(/。{2,}/g, '。')
    .replace(/\(\s*\)/g, '')
    .trim();
}

export function looksLikeCorruptedLine(text: string): boolean {
  const normalized = repairOcrNoiseLine(text).replace(/\s+/g, '');
  if (!normalized) return true;
  if (/[�]/.test(normalized)) return true;
  if (/(?:鈥|銆|锛|鏈€|鍙|鐨|鎬|寮|缁|澶|鏂)/.test(normalized)) return true;
  if (/^[；，。、:：\-_=~#*./\\]+$/.test(normalized)) return true;

  const structureCount = countMatches(normalized, /[|｜_=~#*<>]/g);
  const strangeCount = countMatches(normalized, /[※★☆◆■□◇○●△▽▼◉✦✧✱✳✴]/g);
  const ratio = (structureCount + strangeCount) / Math.max(normalized.length, 1);

  if (normalized.length >= 12 && ratio > 0.22) {
    return true;
  }

  const clauses = normalized.split(/[；;]/).filter(Boolean);
  if (clauses.length >= 6 && !/[。！？]/.test(normalized) && ratio > 0.08) {
    return true;
  }

  return false;
}

export function looksLikeOptionLine(text: string): boolean {
  const normalized = normalizeInlineText(text);
  return /^[A-D][.、\s]/.test(normalized) || /^选项[A-D]/.test(normalized);
}

export function looksLikeExamStemLine(text: string): boolean {
  const normalized = normalizeInlineText(text);
  return (
    /^(下列|关于|对于|依照|根据|案例|案情|题干|真题|单选题|多选题|第?\d+题)/.test(normalized) ||
    /(正确的是|错误的是|说法正确|说法错误|表述正确|表述错误|哪一项|哪些项)/.test(normalized)
  );
}

export function cleanGeneratedAnswerLine(line: string): string {
  const prefixMatch = line.match(/^(\s*(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+)?)(.*)$/);
  if (!prefixMatch) return repairOcrNoiseLine(line);

  const [, prefix, rawContent] = prefixMatch;
  const cleanedContent = repairOcrNoiseLine(rawContent);
  if (!cleanedContent || looksLikeCorruptedLine(cleanedContent)) return '';
  return `${prefix}${cleanedContent}`.trimEnd();
}

export function cleanCitationTextForModel(text: string, examMode: boolean): string {
  const normalized = text.replace(/\r/g, '').trim();
  if (!normalized) return '';

  const lines = normalized
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map(repairOcrNoiseLine)
    .filter(Boolean)
    .filter((line) => !looksLikeCorruptedLine(line))
    .filter((line) => {
      if (!examMode && /^(答案[:：]|解析[:：]|真题|单选题|多选题|选择题)/.test(line)) return false;
      if (!examMode && looksLikeOptionLine(line)) return false;
      if (!examMode && looksLikeExamStemLine(line)) return false;
      return true;
    });

  return lines.join('\n').trim();
}

export function sanitizeCitationTextForKnowledgeAnswerStrict(text: string): string {
  const normalized = cleanCitationTextForModel(text, false);
  if (!normalized) return '';

  const lines = normalized
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => {
      if (/^(答案[:：]|解析[:：]|真题|单选题|多选题|选择题)/.test(line)) return false;
      if (looksLikeOptionLine(line)) return false;
      if (looksLikeExamStemLine(line)) return false;
      return true;
    });

  const sentences = lines
    .join('\n')
    .split(/(?<=[。！？；])/)
    .map((item) => repairOcrNoiseLine(normalizeInlineText(item)))
    .filter(Boolean)
    .filter((item) => !looksLikeCorruptedLine(item))
    .filter((item) => !looksLikeOptionLine(item) && !looksLikeExamStemLine(item));

  const unique: string[] = [];
  for (const sentence of sentences) {
    if (sentence.length < 6) continue;
    if (!unique.includes(sentence)) unique.push(sentence);
    if (unique.length >= 4) break;
  }

  return unique.join(' ').trim();
}

export function isStrictExamStyleQuestion(question: string): boolean {
  const normalized = normalizeInlineText(question);
  return (
    /(^|\s)[A-D][.、\s]/.test(normalized) ||
    /(单选题|多选题|真题|选择题|不定项)/.test(normalized) ||
    /(哪一项|哪些项|正确的是|错误的是|说法正确|说法错误|表述正确|表述错误)/.test(normalized) ||
    /甲某|乙某|被告人|原告|被告|甲公司|乙公司/.test(normalized)
  );
}

export function isStrictExamStyleCitationText(text: string): boolean {
  const normalized = cleanCitationTextForModel(text, true);
  if (!normalized) return false;
  const lines = normalized.split('\n').map((line) => line.trim()).filter(Boolean);
  const optionLines = lines.filter((line) => looksLikeOptionLine(line)).length;
  const stemLines = lines.filter((line) => looksLikeExamStemLine(line)).length;
  return optionLines >= 2 || stemLines >= 1 || /(答案[:：]|解析[:：]|真题|单选题|多选题|选择题)/.test(normalized);
}

export function buildContext(citations: Citation[]): string {
  return citations
    .map((citation, index) => {
      const cleanedText = cleanCitationTextForModel(citation.text_content || '', true);
      if (!cleanedText) return '';
      return [`Fragment ${index + 1}`, `Text: ${cleanedText}`].filter(Boolean).join('\n');
    })
    .filter(Boolean)
    .join('\n\n');
}

export function buildKnowledgeContext(citations: Citation[]): string {
  return citations
    .map((citation, index) => {
      const summary = sanitizeCitationTextForKnowledgeAnswerStrict(citation.text_content || '');
      if (!summary) return '';
      return [`Fragment ${index + 1}`, `Key point: ${summary}`].filter(Boolean).join('\n');
    })
    .filter(Boolean)
    .join('\n\n');
}
