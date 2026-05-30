import d3Runtime from '../../node_modules/d3/dist/d3.min.js?raw';
import markmapLibRuntime from '../../node_modules/markmap-lib/dist/browser/index.iife.js?raw';
import markmapViewRuntime from '../../node_modules/markmap-view/dist/browser/index.js?raw';

const DEFAULT_TITLE = '思维导图';
const PREVIEW_SESSION_KEY = 'law-mindmap-preview:current';
const PREVIEW_RECORD_PREFIX = 'law-mindmap-preview:record:';
const PREVIEW_LATEST_KEY = 'law-mindmap-preview:latest-id';

interface PreviewSessionPayload {
  id?: string;
  title: string;
  markdown: string;
  updatedAt: number;
}

export interface MindmapSvgPayload {
  svg: string;
  width: number;
  height: number;
}

export interface CanonicalMindmapNode {
  id: string;
  text: string;
  depth: number;
  kind: 'heading' | 'bullet';
  children: CanonicalMindmapNode[];
}

export interface MindmapTreeNode {
  id: string;
  text: string;
  level: number;
  children: MindmapTreeNode[];
}

interface SvgLayoutNode {
  id: string;
  parentId: string | null;
  text: string;
  depth: number;
  kind: 'heading' | 'bullet';
  x: number;
  y: number;
  width: number;
  children: SvgLayoutNode[];
}

interface StackEntry {
  node: CanonicalMindmapNode;
}

export function normalizeMindmapMarkdown(markdownCode: string): string {
  return markdownCode.trim().replace(/^```markdown\s*/i, '').replace(/```$/i, '').trim();
}

export function markdownToPlainOutline(markdown: string): string {
  return normalizeMindmapMarkdown(markdown)
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return '';

      const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
      if (headingMatch) {
        const depth = Math.max(headingMatch[1].length - 1, 0);
        return `${'  '.repeat(depth)}${sanitizeNodeText(headingMatch[2])}`;
      }

      const bulletMatch = line.match(/^(\s*)[-*+]\s+(.*)$/);
      if (bulletMatch) {
        const indent = Math.max(0, Math.floor(bulletMatch[1].length / 2));
        return `${'  '.repeat(indent + 1)}- ${sanitizeNodeText(bulletMatch[2])}`;
      }

      const orderedMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);
      if (orderedMatch) {
        const indent = Math.max(0, Math.floor(orderedMatch[1].length / 2));
        return `${'  '.repeat(indent + 1)}- ${sanitizeNodeText(orderedMatch[2])}`;
      }

      return sanitizeNodeText(trimmed);
    })
    .join('\n')
    .trim();
}

export function safeFilename(text: string): string {
  return (text || 'mind-map')
    .replace(/[\\/:*?"<>|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 40) || 'mind-map';
}

function createPreviewId() {
  const randomPart = Math.random().toString(36).slice(2, 10);
  return `${Date.now().toString(36)}-${randomPart}`;
}

function getPreviewRecordKey(id: string) {
  return `${PREVIEW_RECORD_PREFIX}${id}`;
}

function normalizePreviewPayload(payload: Partial<PreviewSessionPayload> | null): PreviewSessionPayload | null {
  if (!payload?.markdown) return null;
  return {
    id: payload.id,
    title: payload.title || DEFAULT_TITLE,
    markdown: normalizeMindmapMarkdown(payload.markdown),
    updatedAt: payload.updatedAt || Date.now(),
  };
}

function readStoredPreviewRecord(storage: Storage, key: string): PreviewSessionPayload | null {
  const raw = storage.getItem(key);
  if (!raw) return null;
  return normalizePreviewPayload(JSON.parse(raw) as PreviewSessionPayload);
}

export function persistMindmapPreviewSession(title: string, markdown: string) {
  const id = createPreviewId();
  if (typeof window === 'undefined') return;
  const payload = {
    id,
    title: title || DEFAULT_TITLE,
    markdown: normalizeMindmapMarkdown(markdown),
    updatedAt: Date.now(),
  } satisfies PreviewSessionPayload;

  try {
    window.sessionStorage.setItem(PREVIEW_SESSION_KEY, JSON.stringify(payload));
    window.sessionStorage.setItem(getPreviewRecordKey(id), JSON.stringify(payload));
  } catch {
    // Ignore preview session issues.
  }

  try {
    window.localStorage.setItem(PREVIEW_LATEST_KEY, id);
    window.localStorage.setItem(getPreviewRecordKey(id), JSON.stringify(payload));
  } catch {
    // Ignore persistent preview issues.
  }

  return id;
}

export function readMindmapPreviewSession(previewId?: string | null): PreviewSessionPayload | null {
  if (typeof window === 'undefined') return null;
  const idFromUrl = previewId?.trim();

  try {
    if (idFromUrl) {
      const recordKey = getPreviewRecordKey(idFromUrl);
      const sessionRecord = readStoredPreviewRecord(window.sessionStorage, recordKey);
      if (sessionRecord) return sessionRecord;
      const localRecord = readStoredPreviewRecord(window.localStorage, recordKey);
      if (localRecord) return localRecord;
    }

    const sessionRecord = readStoredPreviewRecord(window.sessionStorage, PREVIEW_SESSION_KEY);
    if (sessionRecord) return sessionRecord;

    const latestId = window.localStorage.getItem(PREVIEW_LATEST_KEY);
    if (latestId) {
      const latestRecord = readStoredPreviewRecord(window.localStorage, getPreviewRecordKey(latestId));
      if (latestRecord) return latestRecord;
    }

    return null;
  } catch {
    return null;
  }
}

export function buildMindmapPreviewPath() {
  return '/mindmap-preview';
}

export function openMindmapPreviewWindow(title: string, markdown: string) {
  const previewId = persistMindmapPreviewSession(title, markdown);
  if (typeof window !== 'undefined') {
    const path = previewId ? `${buildMindmapPreviewPath()}?id=${encodeURIComponent(previewId)}` : buildMindmapPreviewPath();
    window.open(path, '_blank', 'noopener,noreferrer');
  }
}

export function detectWeakMindmapBrowser(userAgent?: string) {
  const ua = (userAgent ?? (typeof navigator !== 'undefined' ? navigator.userAgent : '')).toLowerCase();
  if (!ua) return false;
  return /micromessenger|qbwebviewtype|mqqbrowser|qqbrowser|quark|miuibrowser|xiaomi|ucbrowser|huaweibrowser|hihonorbrowser/.test(ua)
    || (/android/.test(ua) && /\bwv\b/.test(ua));
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeXml(text: string): string {
  return escapeHtml(text);
}

function stripInlineMarkdown(text: string): string {
  return text
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/<[^>]+>/g, ' ');
}

function sanitizeNodeText(text: string) {
  return stripInlineMarkdown(text)
    .replace(/[\u0000-\u001f]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim() || DEFAULT_TITLE;
}

function measureTextWidth(text: string): number {
  return Array.from(text).reduce((total, char) => total + (/[\u0000-\u00ff]/.test(char) ? 8 : 14), 0);
}

function truncateLabel(text: string, maxLength = 30): string {
  const content = text.trim();
  if (content.length <= maxLength) return content;
  return `${content.slice(0, maxLength - 1)}...`;
}

function getLevelColor(depth: number): { fill: string; stroke: string } {
  const palette = [
    { fill: '#dbeafe', stroke: '#2563eb' },
    { fill: '#dcfce7', stroke: '#16a34a' },
    { fill: '#fef3c7', stroke: '#d97706' },
    { fill: '#fee2e2', stroke: '#dc2626' },
    { fill: '#ede9fe', stroke: '#7c3aed' },
  ];
  return palette[Math.min(depth, palette.length - 1)];
}

function createNode(id: string, text: string, depth: number, kind: 'heading' | 'bullet'): CanonicalMindmapNode {
  return {
    id,
    text: sanitizeNodeText(text),
    depth,
    kind,
    children: [],
  };
}

function getSourceLines(markdown: string) {
  return normalizeMindmapMarkdown(markdown)
    .replace(/\r/g, '')
    .split('\n')
    .map((line) => line.replace(/\t/g, '  ').replace(/\s+$/, ''));
}

function getNearestHeadingDepth(stack: StackEntry[]) {
  for (let index = stack.length - 1; index >= 0; index -= 1) {
    if (stack[index].node.kind === 'heading') {
      return stack[index].node.depth;
    }
  }
  return 0;
}

export function buildCanonicalMindmapTree(markdown: string, title: string): CanonicalMindmapNode {
  const sourceLines = getSourceLines(markdown).filter((line) => line.trim());
  const root = createNode('root', title || DEFAULT_TITLE, 0, 'heading');
  if (!sourceLines.length) {
    return root;
  }

  let nodeCounter = 0;
  let consumedRootHeading = false;
  const stack: StackEntry[] = [{ node: root }];

  sourceLines.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) return;

    const headingMatch = trimmed.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      const headingLevel = headingMatch[1].length;
      const headingText = sanitizeNodeText(headingMatch[2]);

      if (!consumedRootHeading && headingLevel === 1) {
        root.text = headingText || root.text;
        consumedRootHeading = true;
        stack.length = 1;
        return;
      }

      const depth = Math.max(1, headingLevel - 1);
      while (stack.length > 1 && stack[stack.length - 1].node.depth >= depth) {
        stack.pop();
      }

      const parent = stack[stack.length - 1]?.node ?? root;
      const node = createNode(`node-${nodeCounter += 1}`, headingText, depth, 'heading');
      parent.children.push(node);
      stack.push({ node });
      consumedRootHeading = true;
      return;
    }

    const bulletMatch = line.match(/^(\s*)([-*+]|\d+\.)\s+(.*)$/);
    const indentSpaces = bulletMatch ? bulletMatch[1].length : 0;
    const bulletText = sanitizeNodeText(bulletMatch ? bulletMatch[3] : trimmed);
    const headingDepth = getNearestHeadingDepth(stack);
    const indentLevel = Math.max(0, Math.floor(indentSpaces / 2));
    let depth = headingDepth + 1 + indentLevel;

    while (stack.length > 1 && stack[stack.length - 1].node.depth >= depth) {
      stack.pop();
    }

    const parent = stack[stack.length - 1]?.node ?? root;
    depth = Math.max(parent.depth + 1, depth);
    const node = createNode(`node-${nodeCounter += 1}`, bulletText, depth, 'bullet');
    parent.children.push(node);
    stack.push({ node });
  });

  return root;
}

export function buildMindmapTree(markdown: string): MindmapTreeNode[] {
  const root = buildCanonicalMindmapTree(markdown, DEFAULT_TITLE);
  return [
    {
      id: root.id,
      text: root.text,
      level: 1,
      children: mapTreeChildren(root.children),
    },
  ];
}

function mapTreeChildren(nodes: CanonicalMindmapNode[]): MindmapTreeNode[] {
  return nodes.map((node) => ({
    id: node.id,
    text: node.text,
    level: node.depth + 1,
    children: mapTreeChildren(node.children),
  }));
}

export function buildCompatibilityPreviewModel(markdown: string, title: string) {
  return buildCanonicalMindmapTree(markdown, title || DEFAULT_TITLE);
}

function assignSvgNodeWidth(node: SvgLayoutNode) {
  node.width = Math.max(96, Math.min(360, measureTextWidth(node.text) + 20));
  node.children.forEach(assignSvgNodeWidth);
}

function collectLeafCount(node: SvgLayoutNode): number {
  if (!node.children.length) {
    return 1;
  }
  return node.children.reduce((total, child) => total + collectLeafCount(child), 0);
}

function placeSvgNode(node: SvgLayoutNode, cursor: { value: number }, leftPadding: number, horizontalGap: number, verticalGap: number) {
  node.x = leftPadding + node.depth * horizontalGap;
  if (!node.children.length) {
    node.y = cursor.value;
    cursor.value += verticalGap;
    return;
  }

  node.children.forEach((child) => placeSvgNode(child, cursor, leftPadding, horizontalGap, verticalGap));
  node.y = (node.children[0].y + node.children[node.children.length - 1].y) / 2;
}

function mapToSvgNode(node: CanonicalMindmapNode, parentId: string | null): SvgLayoutNode {
  const svgNode: SvgLayoutNode = {
    id: node.id,
    parentId,
    text: truncateLabel(node.text, node.depth <= 1 ? 34 : 28),
    depth: node.depth,
    kind: node.kind,
    x: 0,
    y: 0,
    width: 0,
    children: [],
  };
  svgNode.children = node.children.map((child) => mapToSvgNode(child, svgNode.id));
  assignSvgNodeWidth(svgNode);
  return svgNode;
}

function flattenSvgNodes(node: SvgLayoutNode, output: SvgLayoutNode[]) {
  output.push(node);
  node.children.forEach((child) => flattenSvgNodes(child, output));
}

export function buildMarkmapLikeSvg(markdown: string, title: string): MindmapSvgPayload {
  const tree = buildCanonicalMindmapTree(markdown, title || DEFAULT_TITLE);
  const root = mapToSvgNode(tree, null);
  collectLeafCount(root);

  const leftPadding = 40;
  const rightPadding = 96;
  const topPadding = 48;
  const horizontalGap = 220;
  const verticalGap = 62;
  const baselineOffset = 5;
  const cursor = { value: topPadding };

  placeSvgNode(root, cursor, leftPadding, horizontalGap, verticalGap);

  const layoutNodes: SvgLayoutNode[] = [];
  flattenSvgNodes(root, layoutNodes);

  const width = Math.max(...layoutNodes.map((node) => node.x + node.width), leftPadding + 360) + rightPadding;
  const height = Math.max(cursor.value + topPadding, 320);
  const nodeMap = new Map(layoutNodes.map((node) => [node.id, node]));

  const connectors = layoutNodes
    .filter((node) => node.parentId)
    .map((node) => {
      const parent = nodeMap.get(node.parentId as string);
      if (!parent) return '';
      const colors = getLevelColor(node.depth);
      const startX = parent.x + parent.width + 10;
      const startY = parent.y;
      const endX = node.x - 10;
      const endY = node.y;
      const controlX = startX + Math.max(42, (endX - startX) * 0.56);
      return `<path d="M ${startX} ${startY} C ${controlX} ${startY}, ${controlX} ${endY}, ${endX} ${endY}" fill="none" stroke="${colors.stroke}" stroke-width="${node.depth <= 2 ? '2.6' : '1.8'}" stroke-linecap="round" opacity="0.82" />`;
    })
    .join('');

  const nodeShapes = layoutNodes
    .map((node) => {
      const colors = getLevelColor(node.depth);
      const fontSize = node.depth === 0 ? 16 : node.depth === 1 ? 15 : node.kind === 'heading' ? 14 : 13;
      const fontWeight = node.kind === 'heading' ? 700 : 500;
      const lineY = node.y + 12;
      const marker = node.depth === 0
        ? `<circle cx="${node.x - 13}" cy="${node.y}" r="5" fill="${colors.stroke}" opacity="0.9" />`
        : node.kind === 'heading'
          ? `<rect x="${node.x - 12}" y="${node.y - 6}" width="8" height="8" rx="2.5" fill="${colors.stroke}" opacity="0.9" />`
          : `<circle cx="${node.x - 8}" cy="${node.y}" r="3.5" fill="#fff" stroke="${colors.stroke}" stroke-width="1.6" />`;
      return `<g>
  ${marker}
  <text x="${node.x}" y="${node.y + baselineOffset}" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif" font-size="${fontSize}" font-weight="${fontWeight}" fill="#0f172a">${escapeXml(node.text)}</text>
  <path d="M ${node.x} ${lineY} L ${node.x + node.width} ${lineY}" fill="none" stroke="${colors.stroke}" stroke-width="${node.kind === 'heading' ? '3' : '2'}" stroke-linecap="round" opacity="0.92" />
</g>`;
    })
    .join('');

  return {
    width,
    height,
    svg: `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeXml(title || tree.text || DEFAULT_TITLE)}">
  <defs>
    <radialGradient id="mindmap-bg" cx="20%" cy="0%" r="88%">
      <stop offset="0%" stop-color="#dbeafe" stop-opacity="0.9" />
      <stop offset="52%" stop-color="#f8fafc" stop-opacity="1" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="1" />
    </radialGradient>
  </defs>
  <rect width="${width}" height="${height}" fill="url(#mindmap-bg)" rx="28" />
  ${connectors}
  ${nodeShapes}
</svg>`,
  };
}

export function buildMindmapSvg(markdown: string, title: string): MindmapSvgPayload {
  return buildMarkmapLikeSvg(markdown, title);
}

function renderCompatibilityNodeHtml(node: CanonicalMindmapNode, siblingIndex: number): string {
  const depthClass = `compat-depth-${Math.min(node.depth, 4)}`;
  const marker = node.kind === 'heading'
    ? `<span class="compat-marker compat-marker-heading">${siblingIndex + 1}</span>`
    : '<span class="compat-marker compat-marker-bullet">•</span>';
  const children = node.children.length
    ? `<div class="compat-children">${node.children.map((child, index) => renderCompatibilityNodeHtml(child, index)).join('')}</div>`
    : '';
  return `<section class="compat-node ${depthClass} compat-kind-${node.kind}">
    <div class="compat-row">
      ${marker}
      <div class="compat-body">
        <div class="compat-title">${escapeHtml(node.text)}</div>
        ${children}
      </div>
    </div>
  </section>`;
}

function buildCompatibilityPreviewHtml(tree: CanonicalMindmapNode) {
  return `<article class="compat-page">
    <header class="compat-header">
      <p class="compat-eyebrow">Compatibility Preview</p>
      <h2 class="compat-root-title">${escapeHtml(tree.text || DEFAULT_TITLE)}</h2>
    </header>
    <div class="compat-content">
      ${tree.children.map((node, index) => renderCompatibilityNodeHtml(node, index)).join('')}
    </div>
  </article>`;
}

export function buildFreemindMm(source: CanonicalMindmapNode | string, title = DEFAULT_TITLE): string {
  const tree = typeof source === 'string' ? buildCanonicalMindmapTree(source, title) : source;
  const renderNode = (node: CanonicalMindmapNode) => {
    const children = node.children.map(renderNode).join('');
    return `<node TEXT="${escapeXml(node.text)}">${children}</node>`;
  };

  return `<?xml version="1.0" encoding="UTF-8"?>
<map version="1.0.1">
  ${renderNode(tree)}
</map>`;
}

function createXmindTimestamp() {
  return Date.now().toString();
}

function buildXmindContentXml(source: CanonicalMindmapNode | string, title = DEFAULT_TITLE) {
  const tree = typeof source === 'string' ? buildCanonicalMindmapTree(source, title) : source;
  const timestamp = createXmindTimestamp();
  const sheetId = `sheet-${tree.id || 'root'}`;

  const renderTopic = (node: CanonicalMindmapNode): string => {
    const children = node.children.length
      ? `<children><topics type="attached">${node.children.map(renderTopic).join('')}</topics></children>`
      : '';
    return `<topic id="${escapeXml(node.id)}" timestamp="${timestamp}"><title>${escapeXml(node.text)}</title>${children}</topic>`;
  };

  return `<?xml version="1.0" encoding="UTF-8"?>
<xmap-content timestamp="${timestamp}" version="2.0" xmlns="urn:xmind:xmap:xmlns:content:2.0" xmlns:fo="http://www.w3.org/1999/XSL/Format" xmlns:svg="http://www.w3.org/2000/svg" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink">
  <sheet id="${escapeXml(sheetId)}" timestamp="${timestamp}">
    ${renderTopic(tree)}
    <title>${escapeXml(title || tree.text || DEFAULT_TITLE)}</title>
  </sheet>
</xmap-content>`;
}

function buildXmindStylesXml() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<xmap-styles version="2.0" xmlns="urn:xmind:xmap:xmlns:style:2.0">
  <styles/>
</xmap-styles>`;
}

function buildXmindCommentsXml() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<comments xmlns="urn:xmind:xmap:xmlns:comments:2.0"></comments>`;
}

function buildXmindManifestXml() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
  <manifest:file-entry manifest:media-type="application/vnd.xmind.workbook" manifest:full-path="/"/>
  <manifest:file-entry manifest:media-type="" manifest:full-path="META-INF/"/>
  <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="content.xml"/>
  <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="styles.xml"/>
  <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="comments.xml"/>
  <manifest:file-entry manifest:media-type="text/xml" manifest:full-path="META-INF/manifest.xml"/>
</manifest:manifest>`;
}

function buildCrc32Table() {
  const table = new Uint32Array(256);
  for (let index = 0; index < 256; index += 1) {
    let value = index;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
    }
    table[index] = value >>> 0;
  }
  return table;
}

const CRC32_TABLE = buildCrc32Table();

function crc32(bytes: Uint8Array) {
  let crc = 0xffffffff;
  for (let index = 0; index < bytes.length; index += 1) {
    crc = CRC32_TABLE[(crc ^ bytes[index]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function createDosDateTime(date = new Date()) {
  const year = Math.max(1980, date.getFullYear());
  const dosTime = ((date.getHours() & 0x1f) << 11) | ((date.getMinutes() & 0x3f) << 5) | Math.floor(date.getSeconds() / 2);
  const dosDate = (((year - 1980) & 0x7f) << 9) | (((date.getMonth() + 1) & 0x0f) << 5) | (date.getDate() & 0x1f);
  return { dosDate, dosTime };
}

function writeUint16LE(view: DataView, offset: number, value: number) {
  view.setUint16(offset, value & 0xffff, true);
}

function writeUint32LE(view: DataView, offset: number, value: number) {
  view.setUint32(offset, value >>> 0, true);
}

function concatUint8Arrays(parts: Uint8Array[]) {
  const totalLength = parts.reduce((total, part) => total + part.length, 0);
  const merged = new Uint8Array(totalLength);
  let cursor = 0;
  parts.forEach((part) => {
    merged.set(part, cursor);
    cursor += part.length;
  });
  return merged;
}

function buildStoredZip(entries: Array<{ name: string; content: string | Uint8Array }>) {
  const encoder = new TextEncoder();
  const localFiles: Uint8Array[] = [];
  const centralDirectory: Uint8Array[] = [];
  const { dosDate, dosTime } = createDosDateTime();
  let localOffset = 0;

  entries.forEach((entry) => {
    const fileName = encoder.encode(entry.name);
    const fileBytes = typeof entry.content === 'string' ? encoder.encode(entry.content) : entry.content;
    const checksum = crc32(fileBytes);

    const localHeader = new Uint8Array(30 + fileName.length);
    const localView = new DataView(localHeader.buffer);
    writeUint32LE(localView, 0, 0x04034b50);
    writeUint16LE(localView, 4, 20);
    writeUint16LE(localView, 6, 0x0800);
    writeUint16LE(localView, 8, 0);
    writeUint16LE(localView, 10, dosTime);
    writeUint16LE(localView, 12, dosDate);
    writeUint32LE(localView, 14, checksum);
    writeUint32LE(localView, 18, fileBytes.length);
    writeUint32LE(localView, 22, fileBytes.length);
    writeUint16LE(localView, 26, fileName.length);
    writeUint16LE(localView, 28, 0);
    localHeader.set(fileName, 30);

    const localRecord = concatUint8Arrays([localHeader, fileBytes]);
    localFiles.push(localRecord);

    const centralHeader = new Uint8Array(46 + fileName.length);
    const centralView = new DataView(centralHeader.buffer);
    writeUint32LE(centralView, 0, 0x02014b50);
    writeUint16LE(centralView, 4, 20);
    writeUint16LE(centralView, 6, 20);
    writeUint16LE(centralView, 8, 0x0800);
    writeUint16LE(centralView, 10, 0);
    writeUint16LE(centralView, 12, dosTime);
    writeUint16LE(centralView, 14, dosDate);
    writeUint32LE(centralView, 16, checksum);
    writeUint32LE(centralView, 20, fileBytes.length);
    writeUint32LE(centralView, 24, fileBytes.length);
    writeUint16LE(centralView, 28, fileName.length);
    writeUint16LE(centralView, 30, 0);
    writeUint16LE(centralView, 32, 0);
    writeUint16LE(centralView, 34, 0);
    writeUint16LE(centralView, 36, 0);
    writeUint32LE(centralView, 38, 0);
    writeUint32LE(centralView, 42, localOffset);
    centralHeader.set(fileName, 46);
    centralDirectory.push(centralHeader);

    localOffset += localRecord.length;
  });

  const centralBytes = concatUint8Arrays(centralDirectory);
  const localBytes = concatUint8Arrays(localFiles);
  const endRecord = new Uint8Array(22);
  const endView = new DataView(endRecord.buffer);
  writeUint32LE(endView, 0, 0x06054b50);
  writeUint16LE(endView, 4, 0);
  writeUint16LE(endView, 6, 0);
  writeUint16LE(endView, 8, entries.length);
  writeUint16LE(endView, 10, entries.length);
  writeUint32LE(endView, 12, centralBytes.length);
  writeUint32LE(endView, 16, localBytes.length);
  writeUint16LE(endView, 20, 0);

  return concatUint8Arrays([localBytes, centralBytes, endRecord]);
}

export function buildXmindBlob(source: CanonicalMindmapNode | string, title = DEFAULT_TITLE) {
  const tree = typeof source === 'string' ? buildCanonicalMindmapTree(source, title) : source;
  const zipBytes = buildStoredZip([
    { name: 'content.xml', content: buildXmindContentXml(tree, title) },
    { name: 'styles.xml', content: buildXmindStylesXml() },
    { name: 'comments.xml', content: buildXmindCommentsXml() },
    { name: 'META-INF/manifest.xml', content: buildXmindManifestXml() },
  ]);
  return new Blob([zipBytes], { type: 'application/vnd.xmind.workbook' });
}

export function buildStandaloneMindmapHtml(markdown: string, title: string): string {
  const safeTitle = title || DEFAULT_TITLE;
  const normalizedMarkdown = normalizeMindmapMarkdown(markdown);
  const markdownJson = JSON.stringify(normalizedMarkdown).replace(/</g, '\\u003c');
  const tree = buildCanonicalMindmapTree(markdown, safeTitle);
  const compatibilityHtml = buildCompatibilityPreviewHtml(tree);
  const outline = escapeHtml(markdownToPlainOutline(markdown) || normalizeMindmapMarkdown(markdown));
  const runtimeScript = `${d3Runtime}\n;${markmapLibRuntime}\n;${markmapViewRuntime}`;

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escapeHtml(safeTitle)}</title>
  <style>
    :root {
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
      background: #eef2ff;
      color: #0f172a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 100%);
      padding: 24px;
    }
    .page {
      max-width: 1200px;
      margin: 0 auto;
      display: grid;
      gap: 20px;
    }
    .preview-card,
    .outline-card,
    .fallback-card {
      border: 1px solid #e2e8f0;
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.92);
      box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
      overflow: hidden;
    }
    .toolbar {
      padding: 20px 22px 0;
    }
    .toolbar h1,
    .toolbar h2 {
      margin: 0;
      font-size: 22px;
      line-height: 1.3;
    }
    .toolbar p {
      margin: 8px 0 0;
      font-size: 13px;
      line-height: 1.7;
      color: #64748b;
    }
    .preview-stage,
    .fallback-stage {
      overflow: auto;
      padding: 20px;
      min-height: 620px;
    }
    .preview-stage .markmap {
      display: block;
      width: 1280px;
      height: 620px;
      max-width: none;
      background: #fff;
    }
    .fallback-card {
      display: none;
    }
    .fallback-note {
      display: none;
      margin: 16px 20px 0;
      border: 1px solid #fde68a;
      border-radius: 16px;
      background: #fffbeb;
      color: #92400e;
      padding: 12px 14px;
      font-size: 13px;
      line-height: 1.7;
    }
    .compat-page {
      margin: 0 auto;
      max-width: 860px;
      border: 1px solid #d8e2f0;
      border-radius: 28px;
      background: #fff;
      box-shadow: 0 22px 50px rgba(15, 23, 42, 0.08);
      padding: 24px 22px;
    }
    .compat-header {
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 16px;
      margin-bottom: 18px;
    }
    .compat-eyebrow {
      margin: 0;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.18em;
      color: #2563eb;
      font-weight: 700;
    }
    .compat-root-title {
      margin: 10px 0 0;
      font-size: 28px;
      line-height: 1.3;
      color: #0f172a;
    }
    .compat-content {
      display: grid;
      gap: 14px;
    }
    .compat-node {
      border-radius: 18px;
      border: 1px solid #e2e8f0;
      background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
      padding: 14px 16px;
    }
    .compat-row {
      display: flex;
      gap: 12px;
      align-items: flex-start;
    }
    .compat-marker {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      min-width: 24px;
      height: 24px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
    }
    .compat-marker-heading {
      background: #2563eb;
      color: #fff;
    }
    .compat-marker-bullet {
      color: #2563eb;
      background: #eff6ff;
    }
    .compat-body {
      min-width: 0;
      flex: 1;
    }
    .compat-title {
      font-size: 15px;
      line-height: 1.8;
      color: #0f172a;
      font-weight: 600;
      word-break: break-word;
    }
    .compat-children {
      display: grid;
      gap: 12px;
      margin-top: 12px;
      padding-left: 14px;
      border-left: 2px solid #dbeafe;
    }
    .compat-depth-2 .compat-title {
      color: #0f766e;
    }
    .compat-depth-3 .compat-title {
      color: #334155;
      font-weight: 600;
    }
    .compat-kind-bullet .compat-title {
      font-weight: 500;
    }
    .outline-card pre {
      margin: 0;
      padding: 20px 22px 24px;
      white-space: pre-wrap;
      word-break: break-word;
      font: 14px/1.85 "SFMono-Regular", Consolas, "Microsoft YaHei", monospace;
      color: #334155;
    }
    @media (max-width: 640px) {
      body { padding: 14px; }
      .toolbar { padding: 16px 16px 0; }
      .preview-stage,
      .fallback-stage { padding: 14px; min-height: 360px; }
      .compat-page { padding: 18px 16px; border-radius: 22px; }
      .compat-root-title { font-size: 22px; }
      .outline-card pre { padding: 16px 16px 20px; }
    }
  </style>
</head>
<body>
  <main class="page">
    <section class="preview-card">
      <div class="toolbar">
        <h1>${escapeHtml(safeTitle)}</h1>
        <p>这是可离线打开的 Markmap 官方风格导图文件，内嵌渲染脚本，不依赖外部 CDN。</p>
      </div>
      <p id="fallback-note" class="fallback-note">当前浏览器未能稳定渲染官方导图，已显示下方兼容预览和完整大纲。</p>
      <div class="preview-stage">
        <svg id="markmap" class="markmap" role="img" aria-label="${escapeHtml(safeTitle)}"></svg>
      </div>
    </section>
    <section id="fallback-card" class="fallback-card">
      <div class="toolbar">
        <h2>兼容预览</h2>
        <p>此预览适合微信、小米和系统 WebView 等弱兼容浏览器，优先保证层级关系清楚。</p>
      </div>
      <div class="fallback-stage">
        ${compatibilityHtml}
      </div>
    </section>
    <section class="outline-card">
      <div class="toolbar">
        <h2>可读大纲</h2>
        <p>即使某些浏览器不支持图形交互，也可以直接阅读下面的大纲内容。</p>
      </div>
      <pre>${outline}</pre>
    </section>
  </main>
  <script>
${runtimeScript}
  </script>
  <script>
    (function () {
      var markdown = ${markdownJson};
      var note = document.getElementById('fallback-note');
      var fallback = document.getElementById('fallback-card');
      var svg = document.getElementById('markmap');

      function hasRenderedNodes() {
        if (!svg) return false;
        var nodeCount = svg.querySelectorAll('g.markmap-node').length;
        var foreignCount = svg.querySelectorAll('foreignObject.markmap-foreign').length;
        var text = (svg.textContent || '').replace(/\\s+/g, '');
        return nodeCount > 0 && (foreignCount > 0 || text.length > 0);
      }

      function showFallback() {
        if (note) note.style.display = 'block';
        if (fallback) fallback.style.display = 'block';
      }

      try {
        var transformer = new window.markmap.Transformer();
        var root = transformer.transform(markdown).root;
        var mm = window.markmap.Markmap.create(svg, {
          autoFit: true,
          duration: 0,
          embedGlobalCSS: true,
          fitRatio: 0.94,
          initialExpandLevel: 6,
          maxInitialScale: 1.2,
          maxWidth: 360,
          nodeMinHeight: 20,
          paddingX: 14,
          pan: true,
          scrollForPan: true,
          spacingHorizontal: 90,
          spacingVertical: 12,
          zoom: true
        }, root);

        var attempts = [80, 300, 800];
        attempts.forEach(function (delay, index) {
          window.setTimeout(function () {
            if (hasRenderedNodes()) {
              try { mm.fit(); } catch (fitError) { showFallback(); }
            } else if (index === attempts.length - 1) {
              showFallback();
            }
          }, delay);
        });
      } catch (error) {
        showFallback();
        console.error(error);
      }
    })();
  </script>
</body>
</html>`;
}
