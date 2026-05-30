import React from 'react';
import { BellRing, X } from 'lucide-react';

interface AnnouncementModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const usageNotes = [
  '本页面适合法考知识点问答、概念区分、法条理解和题目解析。',
  '页面会尽量直接输出结论和要点，不主动展示内部参考说明。',
  '模型未配置时，会优先返回当前可直接展示的结果内容。',
];

const usageSteps = [
  '点击右上角设置，填写模型接口、API Key 和模型名称。',
  '先点“测试链接”，确认模型接口可用后再保存。',
  '保存后直接提问，建议一次只问一个清晰问题。',
  '如果答案不够理想，可以继续追问“展开”“区分”“举例”“总结”。',
];

const changeLog = [
  { date: '2026-05-22', text: '新增顶部公告入口，可集中查看使用说明、使用方法和后续通知。' },
  { date: '2026-05-22', text: '新增模型链接测试，支持在设置面板里直接验证 Base URL、Key 和模型名。' },
  { date: '2026-05-22', text: '调整回答风格，默认更接近直接作答，不主动暴露内部参考信息。' },
];

export function AnnouncementModal({ isOpen, onClose }: AnnouncementModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-50 text-amber-600">
              <BellRing size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">公告与说明</h2>
              <p className="text-sm text-gray-500">这里集中放使用说明、使用方法和后续变更通知。</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
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

          <section className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <h3 className="text-sm font-semibold text-gray-900">使用方法</h3>
            <ol className="mt-3 space-y-2 pl-5 text-sm leading-6 text-gray-700 list-decimal">
              {usageSteps.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
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
