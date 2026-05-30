import React, { useEffect, useRef, useState } from 'react';
import { Send, Settings, Server, CheckCircle2, XCircle, BookOpen, BellRing } from 'lucide-react';
import { AppSettings, ChatMessage, Citation } from './types';
import { SettingsModal } from './components/SettingsModal';
import { ChatMessageItem } from './components/ChatMessageItem';
import { AnnouncementModal } from './components/AnnouncementModal';

interface LiveSearchResult {
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

type AnswerMode = 'exam' | 'reasoning' | 'comparison' | 'concept' | 'knowledge';

const defaultSettings: AppSettings = {
  apiBaseUrl: 'https://api.openai.com/v1',
  apiKey: '',
  model: 'gpt-4o-mini',
  deepseekThinkingMode: false,
  streamMode: true,
  searchTopK: 5,
  searchApiUrl: '/api/search',
  systemPrompt:
    '你是专业的法考应试助手。回答时先识别题型，再选择最合适的分析维度和学科组织方式，输出像老师讲题一样的判断链条，而不是只堆结论或法条。',
  temperature: 0.3,
};

const hiddenAssistantPolicy = [
  '你是面向终端用户的法考应试助手。',
  '回答时直接进入结论、考点和判断路径，不要先交代你参考了什么材料。',
  '禁止提及：检索、片段、来源、资料、知识库、本地文件、原文、上下文、内部参考、命中结果。',
  '严禁直接摘抄内部参考原句，必须先吸收再用自己的讲解语言重写。',
  '如果命中材料只有部分信息，要继续结合通用法律知识补全回答，不要机械退回“无法确认”。',
  '真题、案例题、选择题和“整理思路”类请求，必须先识别题型，再选择分析维度，再组织答案。',
  '分析时优先输出判断链条，优先使用“先看……再看……最后看……”这类老师讲题口吻，而不是只给法条结论。',
  '分析维度不是固定全写，而是按题选择最相关的 1 到 3 个：构成要件拆解、法律后果延伸、实务场景应用、易混考点对比。',
  '如果题目涉及程序、机关、路径、申请方向、管辖或阶段流转，优先结合实务场景应用来讲。',
  '如果题目涉及构成、成立、要件、主体资格、责任门槛，优先做构成要件拆解并点出命题陷阱。',
  '如果题目涉及无效、撤销、责任、返还、赔偿、再审、发回、排除等结果问题，优先做法律后果延伸。',
  '如果题目涉及区分、比较、混淆、陷阱、为什么不是另一项，优先做易混考点对比。',
  '如果题目涉及程序规则、管辖规则、主体资格、救济路径、制度适用条件，必须主动检查“通常规则”和“法定例外”两个层面，不能只讲一般规则。',
  '当题目本身容易落在例外情形时，要明确写出：一般怎么处理、本题为什么落入例外、例外改变了什么结论。',
  '如果题目同时包含两个以上程序层级或判断层级，必须先拆成子问题分别分析，例如“向谁申请”“由谁审理”“适用什么程序”要分开处理。',
  '每个子问题只能使用本层级对应的规则和例外，禁止把后一步的例外拿来回答前一步，也禁止把程序选择的例外混进申请法院的判断。',
  '对题目解析，不能只重复答案字母；要把答案放进“考点体系 + 分析维度 + 命题陷阱”里讲清楚。',
  '对普通知识点问答，也要保持应试化表达：先总述，再讲核心规则、判断标准、易混点和记忆提示。',
].join('\n');

function getCurrentDateText(): string {
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
}

function buildRealtimeLawPolicy(): string {
  const today = getCurrentDateText();

  return [
    '动态日期基准：',
    `当前日期：${today}`,
    '回答法律时效、现行规则、修订、生效时间时，必须以当前日期为准判断。',
    '一律优先适用当前已经生效的法律、司法解释和公开有效规则，不得默认沿用旧法。',
    '如果规则存在时间变化，必须明确区分草案、已通过但未生效、已经正式施行三种状态。',
    '如果无法确认某规则在当前日期的效力状态，应明确说明无法确认现行有效状态，而不是直接引用旧规则。',
  ].join('\n');
}

function normalizeInlineText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function looksLikeOptionLine(text: string): boolean {
  const normalized = normalizeInlineText(text);
  return /^[A-DＡ-Ｄ][.．、)\s]/.test(normalized) || /^选项[A-DＡ-Ｄ]/.test(normalized);
}

function looksLikeExamStemLine(text: string): boolean {
  const normalized = normalizeInlineText(text);
  return (
    /^(下列|关于|对于|依照|根据|案例|案情|题干|真题|单选题|多选题|不定项|第?\d+题)/.test(normalized) ||
    /(正确的是|错误的是|说法正确|说法错误|表述正确|表述错误|哪一项|哪些项)/.test(normalized)
  );
}

function isExamStyleQuestion(question: string): boolean {
  const normalized = normalizeInlineText(question);
  return (
    /[A-DＡ-Ｄ][.．、)]/.test(normalized) ||
    /(单选题|多选题|真题|选择题|不定项)/.test(normalized) ||
    /(下列.*(正确|错误|说法|表述)|哪一项|哪些项)/.test(normalized) ||
    /甲公司|乙公司|甲某|乙某|被告人|原告|被告/.test(normalized)
  );
}

function isExamStyleCitationText(text: string): boolean {
  const normalized = text.trim();
  return (
    /[A-DＡ-Ｄ][.．、)]/.test(normalized) ||
    /(答案[:：]|解析[:：]|真题|单选题|多选题|选择题)/.test(normalized)
  );
}

function isStrictExamStyleQuestion(question: string): boolean {
  const normalized = normalizeInlineText(question);
  return (
    /(^|\s)[A-DＡ-Ｄ][.．、)]/.test(normalized) ||
    /(单选题|多选题|真题|选择题|不定项)/.test(normalized) ||
    /(哪一项|哪些项|正确的是|错误的是|说法正确|说法错误|表述正确|表述错误)/.test(normalized) ||
    ((/甲公司|乙公司|甲某|乙某|被告人|原告|被告/.test(normalized) || /A[.．、)]|B[.．、)]|C[.．、)]|D[.．、)]/.test(normalized)) &&
      /(下列|关于|案例|案情|说法|表述|哪一项|哪些项)/.test(normalized))
  );
}

function isStrictExamStyleCitationText(text: string): boolean {
  const normalized = text.replace(/\r/g, '').trim();
  if (!normalized) return false;

  const lines = normalized.split('\n').map((line) => line.trim()).filter(Boolean);
  const optionLines = lines.filter((line) => looksLikeOptionLine(line)).length;
  const stemLines = lines.filter((line) => looksLikeExamStemLine(line)).length;

  return optionLines >= 2 || stemLines >= 1 || /(答案[:：]|解析[:：]|真题|单选题|多选题|选择题)/.test(normalized);
}

function isThoughtRequest(question: string): boolean {
  return /(整理思路|思考逻辑|做题思路|考察角度|拆考点|重新梳理逻辑|命题陷阱|为什么这么选|分析思路)/.test(
    question,
  );
}

function isComparisonRequest(question: string): boolean {
  return /(区别|区分|比较|对比|易混|混淆|为什么不是|相同点|不同点)/.test(question);
}

function isConceptRequest(question: string): boolean {
  return /(是什么|什么意思|如何理解|怎么理解|概念|定义|内涵|外延|如何认定)/.test(question);
}

function detectAnswerMode(question: string): AnswerMode {
  if (isStrictExamStyleQuestion(question)) return 'exam';
  if (isThoughtRequest(question)) return 'reasoning';
  if (isComparisonRequest(question)) return 'comparison';
  if (isConceptRequest(question)) return 'concept';
  return 'knowledge';
}

function inferSubjectTrack(question: string, citations: Citation[]): string {
  const corpus = [question, ...citations.map((citation) => citation.text_content || ''), ...citations.map((citation) => citation.chapter || '')]
    .join('\n')
    .toLowerCase();

  if (/(诈骗|抢劫|抢夺|盗窃|共同犯罪|正当防卫|牵连犯|想象竞合|累犯|自首|立功|假释|减刑|刑罚)/.test(corpus)) {
    return '刑法组织方式：优先围绕构成要件、罪名区分、责任评价和刑罚后果展开。';
  }

  if (/(物权|合同|可撤销|无效合同|违约金|定金|要约|承诺|人格权|婚姻|继承|买卖合同)/.test(corpus)) {
    return '民法组织方式：优先围绕成立与生效、效力与后果、救济方式和易混制度对比展开。';
  }

  if (/(行政许可|行政处罚|行政复议|行政诉讼|具体行政行为|抽象行政行为|听证|受案范围|举证责任)/.test(corpus)) {
    return '行政法组织方式：优先围绕行为性质、主体权限、程序路径和救济机关展开。';
  }

  if (/(民事诉讼|刑事诉讼|行政诉讼|再审|上诉|管辖|举证|证明责任|立案|强制措施|辩护|审判程序|复议机关|法院)/.test(corpus)) {
    return '诉讼法组织方式：优先围绕程序阶段定位、主体/法院/机关确定、规则适用和程序后果展开。';
  }

  if (/(公司法|合伙企业|破产|重整|清算|消费者|反垄断|反不正当竞争|股东|董事|合并|分立)/.test(corpus)) {
    return '商经法组织方式：优先围绕主体结构、权利义务、治理责任和制度边界区分展开。';
  }

  return '通用组织方式：优先围绕核心规则、判断标准、适用路径和易混点展开。';
}

function inferAnalysisDimensions(question: string, citations: Citation[]): string[] {
  const corpus = [question, ...citations.map((citation) => citation.text_content || '')].join('\n');
  const dimensions: string[] = [];

  if (/(构成|成立|要件|主体资格|责任能力|门槛|条件|是否具备|如何认定|程序要件)/.test(corpus)) {
    dimensions.push('构成要件拆解');
  }

  if (/(无效|可撤销|后果|责任|返还|赔偿|折价|再审|撤诉|驳回|发回重审|排除|效力|执行)/.test(corpus)) {
    dimensions.push('法律后果延伸');
  }

  if (/(案例|案情|机关|法院|复议机关|向谁申请|由谁管辖|程序路径|怎么办|如何处理|适用哪个程序|阶段)/.test(corpus)) {
    dimensions.push('实务场景应用');
  }

  if (/(区别|区分|比较|对比|易混|混淆|陷阱|为什么不是|相似|近似)/.test(corpus)) {
    dimensions.push('易混考点对比');
  }

  if (!dimensions.length) {
    if (isStrictExamStyleQuestion(question)) {
      dimensions.push('实务场景应用', '易混考点对比');
    } else {
      dimensions.push('构成要件拆解');
    }
  }

  return dimensions.slice(0, 3);
}

function buildExamStructureInstructions(mode: AnswerMode): string[] {
  if (mode === 'reasoning') {
    return [
      '这次按“思路拆解模板”输出。',
      '固定结构：1. 结论 2. 考点定位 3. 题眼提取 4. 判断链条 5. 核心分析维度 6. 命题陷阱/易混点 7. 一句话记忆。',
      '弱化逐项选项复述，重点把做题路径讲清楚。',
      '判断链条必须写成步骤，而不是只堆结论。',
      '如果本题涉及程序、管辖、主体资格、制度适用条件，要在判断链条里主动区分“一般规则”和“法定例外”。',
      '如果本题有多个判断层级，固定按“先拆子问题，再逐层判断”的方式输出，每一层只回答这一层的问题。',
    ];
  }

  return [
    '这次按“题目解析模板”输出。',
    '固定结构：1. 答案/结论 2. 考点定位 3. 题眼提取 4. 判断链条 5. 核心分析维度 6. 选项或结论展开 7. 易错点/记忆提示。',
    '必须先给出答案或结论，但不能只写答案字母。',
    '如果只有少数选项最关键，可以重点解释关键选项，但仍需说明其余选项为什么不成立。',
    '如果本题涉及程序、管辖、主体资格、制度适用条件，要明确写出“一般规则是什么、例外规则是什么、本题落在哪一边”。',
    '如果本题同时问“向谁申请”“由谁审理”“适用什么程序”等多个层级，必须逐层拆开，不能把后一步的例外混到前一步去。',
  ];
}

function buildComparisonStructureInstructions(): string[] {
  return [
    '这次按“易混辨析模板”输出。',
    '固定结构：1. 一句话区分结论 2. 对比维度 3. 各维度下的判断标准 4. 高频陷阱 5. 一句话记忆。',
    '至少给出一个清晰的区分轴，并解释为什么容易混淆。',
  ];
}

function buildConceptStructureInstructions(): string[] {
  return [
    '这次按“知识点讲解模板”输出。',
    '固定结构：1. 一句话总述 2. 核心规则 3. 判断标准 4. 可选分析维度 5. 易混点 6. 记忆提示。',
    '不要写成百科式定义，要写成面向法考备考的讲解。',
  ];
}

function inferAnswerStyle(question: string, citations: Citation[]): string {
  const mode = detectAnswerMode(question);
  const dimensions = inferAnalysisDimensions(question, citations);
  const subjectTrack = inferSubjectTrack(question, citations);

  const introMap: Record<AnswerMode, string> = {
    exam: '先识别这是一道题目解析请求。',
    reasoning: '先识别这是一道“整理做题思路/考察角度”的请求。',
    comparison: '先识别这是一道易混辨析请求。',
    concept: '先识别这是一个知识点讲解请求。',
    knowledge: '先识别这是一个普通知识问答请求。',
  };

  const structure =
    mode === 'exam' || mode === 'reasoning'
      ? buildExamStructureInstructions(mode)
      : mode === 'comparison'
        ? buildComparisonStructureInstructions()
        : buildConceptStructureInstructions();

  return [
    introMap[mode],
    `主分析维度建议：${dimensions.join('、')}。`,
    subjectTrack,
    '分析维度只展开最相关的 1 到 3 个，不要四个全部机械堆满。',
    ...structure,
    '如果命中材料里已经有现成解析，要吸收其中的理由后重新组织成老师讲题口吻，不能直接照抄。',
    '如果用户问的是具体题目或案例，要把抽象规则代回题干事实，说明为什么落在这个结论上。',
  ].join('\n');
}

function buildRetrievalOnlySummary(question: string, citations: Citation[]): string {
  if (!citations.length) {
    return `暂未找到与“${question}”直接相关的本地结果。你可以换一种问法再试，或者先配置模型接口以获得完整讲解。`;
  }

  const first = citations[0];
  const location = [first.book_name, first.chapter, first.section, first.subsection].filter(Boolean).join(' / ');

  return [
    `已检索到与“${question}”相关的内容。`,
    location ? `命中位置：${location}。` : '',
    '当前还没有配置模型接口，所以这里只保留命中结果，不直接展开生成讲解。',
    '如果你想要“答案 + 思路链 + 分析维度”的完整讲题版本，请先在右上角配置模型接口。',
  ]
    .filter(Boolean)
    .join('');
}

function buildLiveSearchContext(results: LiveSearchResult[]): string {
  if (!results.length) return '';

  return results
    .map((result, index) =>
      [
        `【最新公开信息 ${index + 1}】`,
        result.page_title || result.title ? `标题：${result.page_title || result.title}` : '',
        result.published_at ? `发布时间：${result.published_at}` : '',
        result.effective_at ? `施行时间：${result.effective_at}` : '',
        result.status ? `状态：${result.status}` : '',
        result.authority ? `机关：${result.authority}` : '',
        result.snippet ? `摘要：${result.snippet}` : '',
        result.page_excerpt ? `正文片段：${result.page_excerpt}` : '',
        result.link ? `链接：${result.link}` : '',
      ]
        .filter(Boolean)
        .join('\n'),
    )
    .join('\n\n');
}

function shouldUseLiveSearch(question: string): boolean {
  return /(最新|现行|目前|现在|今天|今日|修订|修正|施行|生效|发布日期|什么时候|哪一年|时间效力)/.test(
    question,
  );
}

function extractAnchorTerms(question: string): string[] {
  const terms = new Set<string>();
  const addTerm = (value: string) => {
    const normalized = normalizeInlineText(value);
    if (!normalized) return;
    terms.add(normalized);
  };

  const bracketMatches: string[] = question.match(/《[^》]{1,40}》/g) || [];
  bracketMatches.forEach((match) => addTerm(match.replace(/[《》]/g, '')));

  const lawMatches: string[] = question.match(/[\u4e00-\u9fa5A-Za-z]{2,30}(?:法|条例|规定|办法|解释|决定|草案)/g) || [];
  lawMatches.forEach((match) => addTerm(match));

  return [...terms];
}

function sanitizeCitationTextForKnowledgeAnswerStrict(text: string): string {
  const normalized = text.replace(/\r/g, '').trim();
  if (!normalized) return '';

  const lines = normalized
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => {
      if (/^(答案[:：]|解析[:：]|真题|单选题|多选题|选择题)/.test(line)) return false;
      if (looksLikeOptionLine(line)) return false;
      if (looksLikeExamStemLine(line)) return false;
      if (/^\|(?:\s*:?-+:?\s*\|)+$/.test(line)) return false;
      return true;
    })
    .map((line) => line.replace(/^\d+[.．、]\s*/g, '').replace(/^第?\d+题[:：]?\s*/g, '').replace(/^[-•]\s*/g, '').trim())
    .filter(Boolean);

  const sentences = lines
    .join('\n')
    .split(/(?<=[。！？；])/)
    .map((item) => normalizeInlineText(item))
    .filter(Boolean)
    .filter((item) => !looksLikeOptionLine(item) && !looksLikeExamStemLine(item));

  const unique: string[] = [];
  for (const sentence of sentences) {
    if (sentence.length < 6) continue;
    if (!unique.includes(sentence)) unique.push(sentence);
    if (unique.length >= 4) break;
  }

  return unique.join(' ').trim();
}

function buildContext(citations: Citation[]): string {
  return citations
    .map((citation, index) => {
      const path = [citation.chapter, citation.section, citation.subsection].filter(Boolean).join(' / ');
      return [
        `【片段 ${index + 1}】`,
        `书籍：${citation.book_name || '未知文献'}`,
        path ? `位置：${path}` : '',
        `行号：${citation.source_line_start || '-'} - ${citation.source_line_end || '-'}`,
        `原文：${citation.text_content || ''}`,
      ]
        .filter(Boolean)
        .join('\n');
    })
    .join('\n\n');
}

function buildKnowledgeContext(citations: Citation[]): string {
  return citations
    .map((citation, index) => {
      const path = [citation.chapter, citation.section, citation.subsection].filter(Boolean).join(' / ');
      const summary = sanitizeCitationTextForKnowledgeAnswerStrict(citation.text_content || '');
      if (!summary) return '';

      return [
        `【片段 ${index + 1}】`,
        `书籍：${citation.book_name || '未知文献'}`,
        path ? `位置：${path}` : '',
        `行号：${citation.source_line_start || '-'} - ${citation.source_line_end || '-'}`,
        `规则要点：${summary}`,
      ]
        .filter(Boolean)
        .join('\n');
    })
    .filter(Boolean)
    .join('\n\n');
}

function filterRelevantCitations(question: string, citations: Citation[], liveSearchContext: string): Citation[] {
  if (!citations.length) return citations;
  const examMode = isStrictExamStyleQuestion(question);
  const anchorTerms = extractAnchorTerms(question);

  const sanitize = (items: Citation[]) =>
    items
      .map((citation) => {
        if (examMode) return citation;
        const sanitizedText = sanitizeCitationTextForKnowledgeAnswerStrict(citation.text_content || '');
        if (!sanitizedText) return null;
        return { ...citation, text_content: sanitizedText };
      })
      .filter((citation): citation is Citation => Boolean(citation))
      .filter((citation) => (citation.text_content || '').trim());

  if (!anchorTerms.length) {
    if (examMode) return citations;
    const nonExamCitations = citations.filter((citation) => !isStrictExamStyleCitationText(citation.text_content || ''));
    return sanitize(nonExamCitations.length ? nonExamCitations : citations);
  }

  const relevant = citations.filter((citation) => {
    const corpus = [citation.book_name, citation.chapter, citation.section, citation.subsection, citation.text_content]
      .filter(Boolean)
      .join('\n');
    return anchorTerms.some((term) => corpus.includes(term));
  });

  if (relevant.length) {
    if (examMode) return relevant;
    const nonExamRelevant = relevant.filter((citation) => !isStrictExamStyleCitationText(citation.text_content || ''));
    return sanitize(nonExamRelevant.length ? nonExamRelevant : relevant);
  }

  if (liveSearchContext || shouldUseLiveSearch(question)) {
    return [];
  }

  if (examMode) return citations;
  const nonExamCitations = citations.filter((citation) => !isStrictExamStyleCitationText(citation.text_content || ''));
  return sanitize(nonExamCitations.length ? nonExamCitations : citations);
}

function buildPromptMeta(question: string, citations: Citation[]): string {
  const mode = detectAnswerMode(question);
  const dimensions = inferAnalysisDimensions(question, citations);
  const subjectTrack = inferSubjectTrack(question, citations);

  const modeLabelMap: Record<AnswerMode, string> = {
    exam: '选择题/案例题',
    reasoning: '思路整理题',
    comparison: '易混辨析题',
    concept: '概念讲解题',
    knowledge: '普通知识问答',
  };

  return [
    '请先在内部完成以下判断，再开始作答：',
    `- 题型识别：${modeLabelMap[mode]}`,
    `- 主分析维度：${dimensions.join('、')}`,
    `- 学科组织方式：${subjectTrack}`,
  ].join('\n');
}

function buildUserPrompt(question: string, citations: Citation[], answerStyle: string, liveSearchContext = ''): string {
  const examMode = isStrictExamStyleQuestion(question) || isThoughtRequest(question);
  const promptContext = examMode ? buildContext(citations) : buildKnowledgeContext(citations);

  const liveSearchPriorityNotice = liveSearchContext
    ? [
        '这次问题涉及最新、现行或时间效力内容时，必须优先以“最新公开信息摘要”为准。',
        '如果最新公开信息与旧知识或本地材料冲突，一律以最新公开信息为准。',
        '回答时必须明确区分草案审议中、已经通过但未生效、已经正式施行三种状态。',
      ].join('\n')
    : '';

  const reasoningHints = [
    buildPromptMeta(question, citations),
    '如果是题目、案例或思路整理请求，先定位考点，再提取题眼，再写判断链条，再选择最相关的分析维度展开。',
    '分析维度只展开最相关的 1 到 3 个，不要机械把所有维度都写满。',
    '如果题目涉及程序、管辖、主体资格、制度适用条件，判断链条里必须主动检查“一般规则 + 法定例外”，并明确本题是否落入例外。',
    '如果题目有多个判断层级，先把问题拆开，例如先判断申请法院，再判断再审由谁审理，最后判断适用什么程序。',
    '拆成子问题后，每个子问题只能调用本层级规则；不要把“审理程序”的例外拿去回答“申请法院”的问题。',
    '构成要件拆解要写清法定要素、判断标准、题干对应点和命题陷阱。',
    '法律后果延伸要写清认定后会发生什么、程序或责任如何继续推进。',
    '实务场景应用要把抽象规则落回本题事实，说明这题具体该怎么走。',
    '易混考点对比要给出关键区分轴，解释为什么本题是 A 而不是 B。',
  ].join('\n');

  if (!citations.length) {
    return [
      '当前本地材料没有直接命中这个问题。',
      '请继续像一个正常的法考应试助手一样完成回答：即使本地材料未直接命中，也要结合当前可用的一般知识、现行有效规则理解和法律常识尽量给出完整答案。',
      '不要对外强调没有命中本地材料，也不要强调是否用了联网信息。请直接自然开始作答。',
      liveSearchPriorityNotice,
      liveSearchContext ? '以下是最新公开信息摘要，请优先吸收这些内容：' : '',
      liveSearchContext || '',
      '',
      reasoningHints,
      '',
      '本次回答方式要求：',
      answerStyle,
      '',
      '用户问题：',
      question,
    ].join('\n');
  }

  return [
    '下面是仅供你内部参考的材料，请吸收后直接回答用户问题，不要提及这些材料的存在。',
    '如果这些材料只覆盖了问题的一部分，你应继续结合现行有效规则理解和一般法律常识补全答案，而不是停在材料本身。',
    '如果命中材料中混有题干、选项、答案字母或真题解析，而用户当前并不是在问那道题本身，请只吸收其中的规则、判断标准和理由，不要把原题原样搬进最终回答。',
    '绝对不要直接引用命中材料原句；必须把命中的内容转化成自己的讲解口吻后再回答。',
    liveSearchPriorityNotice,
    liveSearchContext ? '以下是最新公开信息摘要，请优先吸收这些内容，再结合本地材料作答：' : '',
    liveSearchContext || '',
    '',
    reasoningHints,
    '',
    promptContext,
    '',
    '---',
    '',
    '本次回答方式要求：',
    answerStyle,
    '',
    '---',
    '',
    '用户问题：',
    question,
  ].join('\n');
}

function buildConversationHistory(messages: ChatMessage[]) {
  return messages
    .filter((message) => message.status === 'success' && (message.role === 'user' || message.role === 'assistant'))
    .slice(-8)
    .map((message) => ({
      role: message.role,
      content: message.content,
    }));
}

function isDeepSeekRequest(baseUrl: string, model: string): boolean {
  const normalizedBaseUrl = baseUrl.toLowerCase();
  const normalizedModel = model.toLowerCase();

  return (
    normalizedBaseUrl.includes('deepseek.com') ||
    normalizedBaseUrl.includes('deepseek.cn') ||
    normalizedModel.startsWith('deepseek')
  );
}

function buildModelRequestBody(
  settings: AppSettings,
  model: string,
  messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>,
  useDeepSeekThinkingMode: boolean,
) {
  const baseBody: Record<string, unknown> = {
    model,
    messages,
    stream: settings.streamMode,
  };

  if (useDeepSeekThinkingMode) {
    return {
      ...baseBody,
      reasoning_effort: 'high',
      extra_body: {
        thinking: { type: 'enabled' },
      },
    };
  }

  return {
    ...baseBody,
    temperature: settings.temperature,
  };
}

function stripVerbatimCitationOverlap(answer: string, citations: Citation[]): string {
  let cleaned = answer;

  for (const citation of citations) {
    const fragments = (citation.text_content || '')
      .replace(/\r/g, '')
      .split(/[\n。！？；]/)
      .map((item) => item.trim())
      .filter((item) => item.length >= 12);

    for (const fragment of fragments) {
      if (cleaned.includes(fragment)) {
        cleaned = cleaned.split(fragment).join('');
      }
    }
  }

  return cleaned
    .replace(/\n{3,}/g, '\n\n')
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/([。！？；])\s*([。！？；])/g, '$1')
    .trim();
}

function stripExamArtifactsFromKnowledgeAnswer(answer: string): string {
  return answer
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => {
      if (looksLikeOptionLine(line)) return false;
      if (looksLikeExamStemLine(line)) return false;
      if (/^(答案[:：]|解析[:：])/.test(line)) return false;
      return true;
    })
    .join('\n')
    .trim();
}

function preserveStructuredHeadings(text: string): string {
  return text
    .replace(/^(答案|结论|考点定位|题眼提取|判断链条|判断步骤|核心分析维度|选项分析|结论展开|易错点|记忆提示|一句话记忆|核心规则|判断标准|命题陷阱|法律后果|实务场景应用|易混考点对比)([:：])/gm, '### $1$2')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function formatAssistantAnswer(answer: string, citations: Citation[], usedModel: boolean, examMode = false): string {
  void usedModel;
  const normalized = (answer || '').trim();
  if (!normalized) return normalized;

  const withoutPrefix = normalized.replace(/^以下为未命中本地资料时的联网模型知识分析[:：]?\s*/u, '').trim();
  const cleaned = stripVerbatimCitationOverlap(withoutPrefix, citations);
  const modeAdjusted = examMode ? cleaned : stripExamArtifactsFromKnowledgeAnswer(cleaned);

  return preserveStructuredHeadings(modeAdjusted);
}

export default function App() {
  const [settings, setSettings] = useState<AppSettings>(() => {
    const stored = localStorage.getItem('app_settings');
    if (stored) {
      try {
        return { ...defaultSettings, ...JSON.parse(stored) };
      } catch {
        return defaultSettings;
      }
    }
    return defaultSettings;
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isAnnouncementOpen, setIsAnnouncementOpen] = useState(false);
  const [health, setHealth] = useState<'checking' | 'ok' | 'error'>('checking');

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem('app_settings', JSON.stringify(settings));
  }, [settings]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    const checkHealth = async () => {
      setHealth('checking');
      try {
        const url = settings.searchApiUrl.replace(/\/search\/?$/, '/health');
        const response = await fetch(url);
        setHealth(response.ok ? 'ok' : 'error');
      } catch {
        setHealth('error');
      }
    };

    checkHealth();
  }, [settings.searchApiUrl]);

  const updateMessage = (id: string, updates: Partial<ChatMessage>) => {
    setMessages((prev) => prev.map((message) => (message.id === id ? { ...message, ...updates } : message)));
  };

  const finishWithLocalRetrieval = (messageId: string, question: string, citations: Citation[]) => {
    updateMessage(messageId, {
      status: 'success',
      content: buildRetrievalOnlySummary(question, citations),
      citations,
    });
  };

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    const text = inputValue.trim();
    const conversationHistory = buildConversationHistory(messages);
    const trimmedApiKey = settings.apiKey.trim();
    const trimmedModel = settings.model.trim();
    const trimmedBaseUrl = settings.apiBaseUrl.trim().replace(/\/+$/, '');
    const trimmedSystemPrompt = settings.systemPrompt.trim();
    setInputValue('');

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      status: 'success',
    };
    const assistantMessageId = `${Date.now() + 1}`;
    const assistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      status: 'searching',
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);

    try {
      const searchResponse = await fetch(settings.searchApiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, top_k: settings.searchTopK }),
      }).catch(() => {
        throw new Error(`无法连接到检索接口：${settings.searchApiUrl}`);
      });

      if (!searchResponse.ok) {
        throw new Error(`检索服务响应异常：${searchResponse.status} ${searchResponse.statusText}`);
      }

      const searchData = await searchResponse.json();
      const rawCitations: Citation[] = searchData.results || searchData.data || (Array.isArray(searchData) ? searchData : []);
      let liveSearchContext = '';

      if (shouldUseLiveSearch(text)) {
        try {
          const liveSearchResponse = await fetch('/api/live-search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: text, max_results: 5, auto: false }),
          });

          if (liveSearchResponse.ok) {
            const liveSearchData = await liveSearchResponse.json();
            const liveResults: LiveSearchResult[] = liveSearchData.results || (Array.isArray(liveSearchData) ? liveSearchData : []);
            liveSearchContext =
              typeof liveSearchData.context === 'string' && liveSearchData.context.trim()
                ? liveSearchData.context.trim()
                : buildLiveSearchContext(liveResults);
          }
        } catch {
          liveSearchContext = '';
        }
      }

      const citations = filterRelevantCitations(text, rawCitations, liveSearchContext);
      const strictExamMode = isStrictExamStyleQuestion(text) || isThoughtRequest(text);

      updateMessage(assistantMessageId, {
        status: 'generating',
        citations,
      });

      if (!trimmedApiKey || !trimmedModel) {
        finishWithLocalRetrieval(assistantMessageId, text, citations);
        return;
      }

      const answerStyle = inferAnswerStyle(text, citations);
      const realtimeLawPolicy = buildRealtimeLawPolicy();
      const useDeepSeekThinkingMode = settings.deepseekThinkingMode && isDeepSeekRequest(trimmedBaseUrl, trimmedModel);
      const requestMessages = [
        {
          role: 'system' as const,
          content: `${hiddenAssistantPolicy}\n\n${realtimeLawPolicy}\n\n用户额外风格要求：\n${trimmedSystemPrompt || '无'}`,
        },
        ...conversationHistory,
        {
          role: 'user' as const,
          content: buildUserPrompt(text, citations, answerStyle, liveSearchContext),
        },
      ];

      const body = buildModelRequestBody(settings, trimmedModel, requestMessages, useDeepSeekThinkingMode);

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${trimmedApiKey}`,
      };

      const endpoint = `${trimmedBaseUrl}/chat/completions`;
      const generationResponse = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
      }).catch(() => {
        throw new Error('连接模型接口失败，可能是网络、CORS 或 Base URL 配置有问题。');
      });

      if (!generationResponse.ok) {
        let detail = '';
        try {
          const errorData = await generationResponse.json();
          detail = errorData.error?.message || JSON.stringify(errorData);
        } catch {
          detail = generationResponse.statusText;
        }
        throw new Error(`模型调用失败：HTTP ${generationResponse.status} ${detail}`);
      }

      if (settings.streamMode) {
        const reader = generationResponse.body?.getReader();
        if (!reader) throw new Error('无法读取流式返回结果。');

        const decoder = new TextDecoder();
        let fullText = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n').filter((line) => line.trim() !== '');

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const payload = line.slice(6).trim();
            if (payload === '[DONE]') continue;

            try {
              const parsed = JSON.parse(payload);
              const delta = parsed.choices?.[0]?.delta?.content;
              if (delta) {
                fullText += delta;
                updateMessage(assistantMessageId, {
                  content: formatAssistantAnswer(fullText, citations, true, strictExamMode),
                  citations,
                });
              }
            } catch {
              continue;
            }
          }
        }

        updateMessage(assistantMessageId, { status: 'success' });
      } else {
        const generationData = await generationResponse.json();
        const answer = generationData.choices?.[0]?.message?.content || '';
        updateMessage(assistantMessageId, {
          content: formatAssistantAnswer(answer, citations, true, strictExamMode),
          citations,
          status: 'success',
        });
      }
    } catch (error: any) {
      updateMessage(assistantMessageId, {
        status: 'error',
        error: error.message || '系统底层异常',
      });
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="relative flex h-screen w-full overflow-hidden bg-gray-50 font-sans text-gray-900">
      <div className="flex min-w-0 flex-1 flex-col transition-all">
        <header className="sticky top-0 z-10 flex h-16 flex-shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 shadow-sm">
              <BookOpen size={16} className="text-white" />
            </div>
            <h1 className="text-[17px] font-semibold tracking-tight text-gray-800">法考对话平台</h1>

            <div className="ml-2 hidden items-center gap-1.5 rounded-full border border-gray-100 bg-gray-50 px-2.5 py-1 text-[11px] font-medium text-gray-500 sm:flex">
              <Server size={12} />
              <span>检索服务</span>
              {health === 'checking' && <span className="text-yellow-600">检测中</span>}
              {health === 'ok' && (
                <span className="flex items-center gap-1 text-green-600">
                  <CheckCircle2 size={12} /> 连接稳定
                </span>
              )}
              {health === 'error' && (
                <span className="flex items-center gap-1 text-red-500">
                  <XCircle size={12} /> 无法访问
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsAnnouncementOpen(true)}
              className="flex items-center gap-2 rounded-lg border border-transparent p-2 text-sm font-medium text-gray-500 transition-colors hover:border-amber-100 hover:bg-amber-50 hover:text-amber-700"
            >
              <BellRing size={18} />
              <span className="hidden sm:inline">公告说明</span>
            </button>

            <button
              onClick={() => setIsSettingsOpen(true)}
              className="flex items-center gap-2 rounded-lg border border-transparent p-2 text-sm font-medium text-gray-500 transition-colors hover:border-blue-100 hover:bg-blue-50 hover:text-blue-700"
            >
              <Settings size={18} />
              <span className="hidden sm:inline">接口配置</span>
            </button>
          </div>
        </header>

        <div className="w-full flex-1 overflow-y-auto pb-6">
          <div className="mx-auto w-full max-w-4xl px-4 py-8">
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center pb-12 pt-24 text-center">
                <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl border border-blue-100 bg-blue-50 shadow-sm">
                  <BookOpen size={30} className="text-blue-600" />
                </div>
                <h2 className="mb-3 text-2xl font-semibold tracking-tight text-gray-800">你好，欢迎来到法考对话平台</h2>
                <p className="mb-10 max-w-md text-sm leading-relaxed text-gray-500">
                  现在已经接上本地法考知识检索。
                  <br />
                  不配置模型时，它会先返回命中的检索结果；配置好模型后，就会在检索基础上继续生成“答案 + 思路链 + 分析维度”的完整讲解。
                </p>
                <div className="grid w-full max-w-xl grid-cols-1 gap-3 sm:grid-cols-2">
                  {[
                    '民诉中再审程序如何区分原审法院再审和上级法院提审？',
                    '诈骗罪的构成要件和常见命题陷阱是什么？',
                    '定金和违约金怎么区分？',
                    '根据这个题目整理做题思路和考察角度。',
                  ].map((question, index) => (
                    <button
                      key={index}
                      onClick={() => setInputValue(question)}
                      className="truncate rounded-xl border border-gray-200 bg-white px-5 py-3.5 text-left text-[14px] font-medium text-gray-700 transition-all hover:border-blue-300 hover:shadow-sm lg:whitespace-nowrap"
                    >
                      "{question}"
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col">
                {messages.map((message) => (
                  <ChatMessageItem key={message.id} message={message} />
                ))}
                <div ref={bottomRef} className="h-1" />
              </div>
            )}
          </div>
        </div>

        <div className="shrink-0 border-t border-gray-200 bg-white/80 px-4 py-4 pb-6 shadow-sm backdrop-blur-md">
          <div className="relative mx-auto flex max-w-4xl items-end">
            <textarea
              className="w-full resize-none rounded-2xl border border-gray-300 bg-gray-50 py-3.5 pl-5 pr-14 text-[15px] leading-relaxed text-gray-800 shadow-sm transition-all focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-4 focus:ring-blue-100/50"
              rows={1}
              style={{ minHeight: '56px', maxHeight: '180px' }}
              placeholder="询问任意法考知识点... (Shift + Enter 换行)"
              value={inputValue}
              onChange={(event) => {
                setInputValue(event.target.value);
                event.target.style.height = 'auto';
                event.target.style.height = `${Math.min(event.target.scrollHeight, 180)}px`;
              }}
              onKeyDown={handleKeyDown}
            />
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || messages[messages.length - 1]?.status === 'generating' || messages[messages.length - 1]?.status === 'searching'}
              className="absolute bottom-2.5 right-2.5 rounded-xl bg-blue-600 p-2 text-white shadow-sm transition-colors hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none"
            >
              <Send size={18} className="translate-x-[1px] translate-y-[1px]" />
            </button>
          </div>
          <div className="mt-4 flex items-center justify-center gap-1.5 text-center text-xs font-medium text-gray-400 opacity-80">
            检索结果和模型回答仅供学习参考，涉及法条、司法解释和真题结论时请以官方资料为准。
          </div>
        </div>
      </div>

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={settings}
        onSave={setSettings}
      />

      <AnnouncementModal
        isOpen={isAnnouncementOpen}
        onClose={() => setIsAnnouncementOpen(false)}
      />
    </div>
  );
}
