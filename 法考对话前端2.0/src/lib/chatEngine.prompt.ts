import { AppSettings } from '../types';
import { AnswerMode, Citation, ConversationMessage, LiveSearchResult } from './chatEngine.types';
import {
  buildContext,
  buildKnowledgeContext,
  cleanCitationTextForModel,
  isStrictExamStyleCitationText,
  isStrictExamStyleQuestion,
  normalizeInlineText,
  sanitizeCitationTextForKnowledgeAnswerStrict,
} from './chatEngine.cleaners';

const hiddenAssistantPolicy = [
  '你是面向终端用户的法考应试助手。',
  '回答时直接进入结论、考点和判断路径，不要先交代你参考了什么材料。',
  '禁止提及：检索、片段、来源、资料、知识库、本地文件、原文、上下文、内部参考、命中结果。',
  '严禁直接摘抄内部参考原句，必须先吸收再用自己的讲解语言重写。',
  '如果内部材料里出现 OCR 噪声、乱码、异常分隔符、破碎短句或明显不通顺的残片，先自动识别并清洗；高置信可修复时再吸收，低置信内容直接丢弃。',
  '禁止把乱码、管道符分隔碎片、异常符号串或明显残缺的提纲噪声直接输出给用户。',
  '如果命中材料只有部分信息，要继续结合通用法律知识补全回答，不要机械退回“无法确认”。',
  '真题、案例题、选择题和“整理思路”类请求，必须先识别题型，再选择分析维度，再组织答案。',
  '分析时优先输出判断链条，优先使用“先看……再看……最后看……”这类老师讲题口吻，而不是只给法条结论。',
  '分析维度不是固定全写，而是按题选择最相关的 1 到 3 个：构成要件拆解、法律后果延伸、实务场景应用、易混考点对比。',
  '如果题目涉及程序、机关、路径、申请方向、管辖或阶段流转，优先结合实务场景应用来讲。',
  '如果题目涉及构成、成立、要件、主体资格、责任门槛，优先做构成要件拆解并点出命题陷阱。',
  '如果题目涉及无效、撤销、责任、返还、赔偿、再审、发回、排除等结果问题，优先做法律后果延伸。',
  '如果题目涉及区分、比较、混淆、陷阱、为什么不是另一项，优先做易混考点对比。',
  '如果题目涉及程序规则、管辖规则、主体资格、救济路径、制度适用条件，必须主动检查“一般规则”和“法定例外”两个层面，不能只讲一般规则。',
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

export function buildRealtimeLawPolicy(): string {
  return [
    '动态日期基准：',
    `当前日期：${getCurrentDateText()}`,
    '回答法律时效、现行规则、修订、生效时间时，必须以当前日期为准判断。',
    '一律优先适用当前已经生效的法律、司法解释和公开有效规则，不得默认沿用旧法。',
    '如果规则存在时间变化，必须明确区分草案、已通过但未生效、已经正式施行三种状态。',
    '如果无法确认某规则在当前日期的效力状态，应明确说明无法确认现行有效状态，而不是直接引用旧规则。',
  ].join('\n');
}

export function isThoughtRequest(question: string): boolean {
  return /(整理思路|思考逻辑|做题思路|考察角度|拆考点|重新梳理逻辑|命题陷阱)/.test(question);
}

function isComparisonRequest(question: string): boolean {
  return /(区别|区分|比较|对比|易混|混淆|为什么不是|相同点|不同点)/.test(question);
}

function isConceptRequest(question: string): boolean {
  return /(是什么|什么意思|如何理解|怎么理解|概念|定义|内涵|外延|如何认定)/.test(question);
}

export function detectAnswerMode(question: string): AnswerMode {
  if (isStrictExamStyleQuestion(question)) return 'exam';
  if (isThoughtRequest(question)) return 'reasoning';
  if (isComparisonRequest(question)) return 'comparison';
  if (isConceptRequest(question)) return 'concept';
  return 'knowledge';
}

export function inferSubjectTrack(question: string, citations: Citation[]): string {
  const corpus = [question, ...citations.map((citation) => citation.text_content || '')]
    .join('\n')
    .toLowerCase();

  if (/(诈骗|抢劫|抢夺|盗窃|共同犯罪|正当防卫|紧急避险|累犯|自首|立功|假释|减刑|刑罚)/.test(corpus)) return '刑法';
  if (/(物权|合同|可撤销|无效合同|违约金|定金|要约|承诺|人格权|婚姻|继承|买卖合同)/.test(corpus)) return '民法';
  if (/(行政许可|行政处罚|行政复议|行政诉讼|具体行政行为|抽象行政行为|听证|受案范围|举证责任)/.test(corpus)) return '行政法';
  if (/(民事诉讼|刑事诉讼|行政诉讼|再审|上诉|管辖|立案|审判程序|法院)/.test(corpus)) return '诉讼法';
  if (/(公司法|合伙企业|破产|重整|清算|消费者|反垄断|反不正当竞争|股东|董事|合并|分立)/.test(corpus)) return '商经法';
  return '通用';
}

export function inferAnalysisDimensions(question: string, citations: Citation[]): string[] {
  const corpus = [question, ...citations.map((citation) => citation.text_content || '')].join('\n');
  const dimensions: string[] = [];

  if (/(构成|成立|要件|主体资格|责任能力|门槛|条件|是否具备|如何认定|程序要件)/.test(corpus)) dimensions.push('构成要件拆解');
  if (/(无效|可撤销|后果|责任|返还|赔偿|折价|再审|撤诉|驳回|发回重审|排除|效力|执行)/.test(corpus)) dimensions.push('法律后果延伸');
  if (/(案例|案情|机关|法院|向谁申请|由谁审理|程序路径|怎么做|如何处理|适用哪个程序|阶段)/.test(corpus)) dimensions.push('实务场景应用');
  if (/(区别|区分|比较|对比|易混|混淆|陷阱|为什么不是|相似|近似)/.test(corpus)) dimensions.push('易混考点对比');

  if (!dimensions.length) {
    return isStrictExamStyleQuestion(question) ? ['实务场景应用', '易混考点对比'] : ['构成要件拆解'];
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

export function inferAnswerStyle(question: string, citations: Citation[]): string {
  const mode = detectAnswerMode(question);
  const dimensions = inferAnalysisDimensions(question, citations);
  const subjectTrack = inferSubjectTrack(question, citations);

  const structure =
    mode === 'exam' || mode === 'reasoning'
      ? buildExamStructureInstructions(mode)
      : mode === 'comparison'
        ? buildComparisonStructureInstructions()
        : buildConceptStructureInstructions();

  return [
    `先识别这是一个${mode}类型请求。`,
    `主分析维度建议：${dimensions.join('、')}。`,
    `学科组织方式：${subjectTrack}。`,
    '分析维度只展开最相关的 1 到 3 个，不要机械把所有维度都写满。',
    ...structure,
    '如果命中材料里已经有现成解析，要吸收其中的理由后重新组织成老师讲题口吻，不能直接照抄。',
    '如果用户问的是具体题目或案例，要把抽象规则代回题干事实，说明为什么落在这个结论上。',
  ].join('\n');
}

export function buildRetrievalOnlySummary(question: string, citations: Citation[]): string {
  if (!citations.length) {
    return `当前本地知识库里还没有直接命中“${question}”的相关内容。你可以换一个更具体的问法，或者先完成模型配置，以便系统继续给出更完整的解析。`;
  }
  return [
    `本地知识库已命中与“${question}”相关的内容。`,
    '当前还没有完成模型接口配置，所以这里只能先返回简要的知识摘要。',
    '如果你希望拿到完整的法考式解析、推理步骤和考点展开，请先完成模型配置。',
  ].join('\n');
}

export function buildLiveSearchContext(results: LiveSearchResult[]): string {
  if (!results.length) return '';

  return results
    .map((result, index) =>
      [
        `Latest public update ${index + 1}`,
        result.page_title || result.title ? `Title: ${result.page_title || result.title}` : '',
        result.published_at ? `Published: ${result.published_at}` : '',
        result.effective_at ? `Effective: ${result.effective_at}` : '',
        result.status ? `Status: ${result.status}` : '',
        result.authority ? `Authority: ${result.authority}` : '',
        result.snippet ? `Summary: ${result.snippet}` : '',
        result.page_excerpt ? `Excerpt: ${result.page_excerpt}` : '',
        result.link ? `Link: ${result.link}` : '',
      ]
        .filter(Boolean)
        .join('\n'),
    )
    .join('\n\n');
}

export function shouldUseLiveSearch(question: string): boolean {
  return /(最新|现行|目前|现在|今天|今日|修订|修正|施行|生效|发布日期|什么时候|哪一年|时间效力)/.test(question);
}

function extractAnchorTerms(question: string): string[] {
  const terms = new Set<string>();
  const addTerm = (value: string) => {
    const normalized = normalizeInlineText(value);
    if (normalized) terms.add(normalized);
  };

  const lawMatches: string[] = question.match(/[\u4e00-\u9fa5A-Za-z]{2,30}(?:法|条例|规定|办法|解释|决定|草案)/g) || [];
  lawMatches.forEach((match) => addTerm(match));

  const quotedMatches: string[] = question.match(/[“"《](.{1,40})[》”"]/g) || [];
  quotedMatches.forEach((match) => addTerm(match.replace(/[“"《》”"]/g, '')));

  return [...terms];
}

export function filterRelevantCitations(question: string, citations: Citation[], liveSearchContext: string): Citation[] {
  if (!citations.length) return citations;
  const examMode = isStrictExamStyleQuestion(question);
  const anchorTerms = extractAnchorTerms(question);

  const sanitize = (items: Citation[]) =>
    items
      .map((citation) => {
        const sanitizedText = examMode
          ? cleanCitationTextForModel(citation.text_content || '', true)
          : sanitizeCitationTextForKnowledgeAnswerStrict(citation.text_content || '');
        if (!sanitizedText) return null;
        return { ...citation, text_content: sanitizedText };
      })
      .filter((citation): citation is NonNullable<typeof citation> => Boolean(citation))
      .filter((citation) => (citation.text_content || '').trim());

  if (!anchorTerms.length) {
    if (examMode) return citations;
    const nonExamCitations = citations.filter((citation) => !isStrictExamStyleCitationText(citation.text_content || ''));
    return sanitize(nonExamCitations.length ? nonExamCitations : citations);
  }

  const relevant = citations.filter((citation) => {
    const corpus = [citation.title, citation.text_content].filter(Boolean).join('\n');
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

  return [
    'Internal analysis checklist:',
    `- mode: ${mode}`,
    `- dimensions: ${dimensions.join(', ')}`,
    `- subject: ${subjectTrack}`,
  ].join('\n');
}

export function buildUserPrompt(question: string, citations: Citation[], answerStyle: string, liveSearchContext = ''): string {
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
      '回答风格要求：',
      answerStyle,
      '',
      '用户问题：',
      question,
    ].join('\n');
  }

  return [
    '以下材料仅供内部使用。请先吸收，再直接回答，不要提到这些材料本身。',
    '如果材料只覆盖了问题的一部分，请结合当前法律理解继续补足，不要生硬停在材料边界。',
    liveSearchPriorityNotice,
    liveSearchContext ? '以下是最新公开信息摘要：' : '',
    liveSearchContext || '',
    '',
    reasoningHints,
    '',
    promptContext,
    '',
    '---',
    '',
    '回答风格要求：',
    answerStyle,
    '',
    '---',
    '',
    '用户问题：',
    question,
  ].join('\n');
}

export function buildConversationHistory(messages: ConversationMessage[]) {
  return messages
    .filter((message) => message.status === 'success' && (message.role === 'user' || message.role === 'assistant'))
    .slice(-8)
    .map((message) => ({
      role: message.role,
      content: message.content,
    }));
}

export function isDeepSeekRequest(baseUrl: string, model: string): boolean {
  const normalizedBaseUrl = baseUrl.toLowerCase();
  const normalizedModel = model.toLowerCase();
  return normalizedBaseUrl.includes('deepseek.com') || normalizedBaseUrl.includes('deepseek.cn') || normalizedModel.startsWith('deepseek');
}

export function buildModelRequestBody(
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

export function buildSystemPrompt(systemPrompt: string) {
  return `${hiddenAssistantPolicy}\n\n${buildRealtimeLawPolicy()}\n\nCustom user style instructions:\n${systemPrompt || 'None'}`;
}
