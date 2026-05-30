import { Reference } from '../types';
import { Citation } from './chatEngine.types';
import {
  cleanGeneratedAnswerLine,
  extractLegalBasisEntries,
  extractLegalBasisTitle,
  looksLikeCorruptedLine,
  looksLikeExamStemLine,
  looksLikeOptionLine,
  normalizeInlineText,
} from './chatEngine.cleaners';
import { detectAnswerMode, inferAnalysisDimensions, inferSubjectTrack } from './chatEngine.prompt';

const MAX_VISIBLE_REFERENCES = 6;

function stripVerbatimCitationOverlap(answer: string, citations: Citation[]): string {
  const citationLines = new Set<string>();

  for (const citation of citations) {
    const lines = (citation.text_content || '')
      .replace(/\r/g, '')
      .split('\n')
      .map((item) => normalizeInlineText(item))
      .filter((item) => item.length >= 24)
      .filter((item) => !looksLikeOptionLine(item))
      .filter((item) => !looksLikeExamStemLine(item))
      .filter((item) => !looksLikeCorruptedLine(item));

    for (const line of lines) {
      citationLines.add(line);
    }
  }

  return answer
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.trimEnd())
    .filter((line) => {
      const normalized = normalizeInlineText(line);
      if (normalized.length < 24) return true;
      return !citationLines.has(normalized);
    })
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .trim();
}

function normalizeAnswerPunctuation(answer: string): string {
  return answer
    .replace(/[；;]{2,}/g, '；')
    .replace(/([：:])[；;]+/g, '$1')
    .replace(/([，。！？；：])\1+/g, '$1')
    .replace(/[；;]+([）)])/g, '$1')
    .replace(/([（(])[；;]+/g, '$1')
    .replace(/\s+([，。！？；：])/g, '$1')
    .replace(/([（(])\s+/g, '$1')
    .replace(/\s+([）)])/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function stripExamArtifactsFromKnowledgeAnswer(answer: string): string {
  return answer
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => cleanGeneratedAnswerLine(line.trim()))
    .filter(Boolean)
    .filter((line) => {
      if (looksLikeOptionLine(line)) return false;
      if (looksLikeExamStemLine(line)) return false;
      if (/^(答案[:：]|解析[:：])/.test(line)) return false;
      if (looksLikeCorruptedLine(line)) return false;
      return true;
    })
    .join('\n')
    .trim();
}

function preserveStructuredHeadings(text: string) {
  return text
    .replace(/^(答案|结论|考点定位|题眼提取|判断链条|判断步骤|核心分析维度|选项分析|结论展开|易错点|记忆提示|一句话记忆|核心规则|判断标准|命题陷阱|法律后果|实务场景应用|易混考点对比)([:：])/gm, '### $1$2')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function stripCorruptedAnswerArtifacts(answer: string): string {
  return answer
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => cleanGeneratedAnswerLine(line))
    .filter(Boolean)
    .filter((line) => !looksLikeCorruptedLine(line))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function formatAssistantAnswer(answer: string, citations: Citation[], examMode = false): string {
  const normalized = (answer || '').trim();
  if (!normalized) return normalized;
  const cleaned = stripVerbatimCitationOverlap(normalized, citations);
  const deNoised = stripCorruptedAnswerArtifacts(cleaned);
  const modeAdjusted = examMode ? deNoised : stripExamArtifactsFromKnowledgeAnswer(deNoised);
  return normalizeAnswerPunctuation(preserveStructuredHeadings(modeAdjusted));
}

function mapCitationToReference(citation: Citation, index: number): Reference | null {
  const basisEntries = extractLegalBasisEntries(citation.text_content || '');
  if (!basisEntries.length) return null;

  return {
    id: String(index + 1),
    title: extractLegalBasisTitle(citation, index),
    content: basisEntries.join('\n\n'),
    chunkId: citation.chunk_id,
    score: citation.score,
  };
}

export function buildReferencesFromCitations(citations: Citation[]): Reference[] {
  const references: Reference[] = [];
  const seenTitles = new Set<string>();
  citations.forEach((citation, index) => {
    if (references.length >= MAX_VISIBLE_REFERENCES) return;
    const reference = mapCitationToReference(citation, index);
    if (!reference) return;
    const titleKey = normalizeInlineText(reference.title || '').replace(/\s+/g, '');
    if (titleKey && seenTitles.has(titleKey)) return;
    if (titleKey) seenTitles.add(titleKey);
    references.push({
      ...reference,
      id: String(references.length + 1),
    });
  });
  return references;
}

export function appendReferenceGuide(answer: string, references: Reference[]) {
  return answer;
}

export function buildThinkingSummary(question: string, citations: Citation[], liveSearchContext: string) {
  const mode = detectAnswerMode(question);
  const dimensions = inferAnalysisDimensions(question, citations);
  const subjectTrack = inferSubjectTrack(question, citations);
  const lines = [
    `题型识别：${mode}`,
    `分析维度：${dimensions.join('、')}`,
    `组织方式：${subjectTrack}`,
    `本地命中：${citations.length} 条`,
  ];
  if (liveSearchContext) lines.push('附加信息：已启用最新公开信息补充');
  return lines.join('\n');
}
