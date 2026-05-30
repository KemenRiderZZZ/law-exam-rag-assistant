import React from 'react';
import { BellRing, X } from 'lucide-react';

interface AnnouncementModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const usageNotes = [
  '本页面适合法考知识点问答、概念区分、法条理解和题目解析。',
  '页面会尽量直接输出结论和要点，不主动展示资料来源或内部参考说明。',
  '如果暂时没有填写模型配置，系统会优先返回当前可直接展示的法条依据和整理结果。',
];

const usageSteps = [
  '点击左上角菜单按钮，先展开侧边栏。',
  '在侧边栏底部点击“设置”，填写模型接口、API Key 和模型名称。',
  '先点“链接测试”，确认模型接口可用后再保存。',
  '保存后直接提问，建议一次只问一个清晰问题。',
  '如果答案还不够理想，可以继续追问“展开”“区分”“举例”“总结”等补充指令。',
];

const deepSeekGuide = [
  '第一步：打开 DeepSeek 开放平台 `https://platform.deepseek.com/`，登录你自己的账号。',
  '第二步：在平台后台找到 API Key 管理页面，新建一个 Key 并复制保存。API Key 只会完整显示一次，建议立即保存到记事本或密码管理器。',
  '第三步：回到本页面，点击左上角菜单按钮，展开侧边栏后，再点击底部“设置”。',
  '模型接口示例：`https://api.deepseek.com`',
  '模型名称示例：`deepseek-v4-flash`。如果你使用的是其他模型，请按你自己的平台控制台显示内容填写。',
  'API Key：粘贴你刚才在平台生成的 Key。',
  '填写完成后，先点击“链接测试”。如果提示模型接口连接成功，再点击保存设置。',
  '如果你使用的是 OpenAI 兼容接口，通常不需要自己再补 `/chat/completions`，页面会按标准兼容方式发起请求。',
];

const safetyTips = [
  'API Key 是你自己的模型调用凭证，不要发给别人，也不要截图外传。',
  '如果怀疑 Key 泄露，请回到对应模型平台删除旧 Key，再重新生成一个新 Key。',
  '如果你使用任何第三方模型 API，相关套餐、充值、扣费和账单都由你与对应平台自行结算，与本项目无关。本项目只提供模型填写入口，不参与代充、代扣或转售。',
  '本页面不需要你自己填写检索接口地址，普通用户直接使用当前页面内置能力即可。',
];

const changeLog = [
  { date: '2026-05-24', text: '修正公告中的设置入口说明，改为与当前左侧菜单和侧边栏设置入口一致。' },
  { date: '2026-05-24', text: '补充以 DeepSeek 为例的 API 获取与填写教程，方便首次配置。' },
  { date: '2026-05-22', text: '新增公告入口，可集中查看使用说明、配置方法和后续通知。' },
  { date: '2026-05-22', text: '新增模型链接测试，支持直接验证 Base URL、API Key 和模型名称。' },
];

function renderInlineCode(text: string) {
  const parts = text.split(/(`[^`]+`)/g);

  return parts.map((part, index) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return (
        <code key={`${part}-${index}`} className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[12px] text-slate-700">
          {part.slice(1, -1)}
        </code>
      );
    }

    return <React.Fragment key={`${part}-${index}`}>{part}</React.Fragment>;
  });
}

export function AnnouncementModal({ isOpen, onClose }: AnnouncementModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
              <BellRing size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">公告与说明</h2>
              <p className="text-sm text-gray-500">这里集中放使用说明、配置方法和后续变更通知。</p>
            </div>
          </div>

          <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-5 px-6 py-5">
          <section className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <h3 className="text-sm font-semibold text-gray-900">使用说明</h3>
            <div className="mt-3 space-y-2 text-sm leading-6 text-gray-700">
              {usageNotes.map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-blue-200 bg-blue-50 p-4">
            <h3 className="text-sm font-semibold text-slate-900">使用方法</h3>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-700">
              {usageSteps.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          </section>

          <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <h3 className="text-sm font-semibold text-slate-900">以 DeepSeek 为例：API 获取与填写教程</h3>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-700">
              {deepSeekGuide.map((item) => (
                <li key={item}>{renderInlineCode(item)}</li>
              ))}
            </ol>
          </section>

          <section className="rounded-xl border border-amber-200 bg-amber-50 p-4">
            <h3 className="text-sm font-semibold text-slate-900">安全提醒</h3>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-slate-700">
              {safetyTips.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <h3 className="text-sm font-semibold text-gray-900">后续变更通知</h3>
            <div className="mt-3 space-y-3">
              {changeLog.map((item) => (
                <div key={`${item.date}-${item.text}`} className="rounded-lg border border-gray-200 bg-white px-3 py-2">
                  <p className="text-xs font-medium text-amber-700">{item.date}</p>
                  <p className="mt-1 text-sm leading-6 text-gray-700">{item.text}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
