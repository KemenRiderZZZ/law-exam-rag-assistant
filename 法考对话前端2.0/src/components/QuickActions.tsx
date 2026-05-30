import React from 'react';
import { Network, Wand2, Layers, BookOpenCheck } from 'lucide-react';

interface QuickActionsProps {
  onActionSelect: (action: string) => void;
}

export function QuickActions({ onActionSelect }: QuickActionsProps) {
  const actions = [
    { icon: <BookOpenCheck className="w-3.5 h-3.5" />, label: "转为背诵提纲", text: "请将上面的解析精简为适合直接背诵的口诀或提纲形式。" },
    { icon: <Network className="w-3.5 h-3.5" />, label: "易混考点对比", text: "这个考点容易和哪些知识点混淆？请用表格形式做个对比辨析。" },
    { icon: <Wand2 className="w-3.5 h-3.5" />, label: "改变条件怎么判？", text: "如果本案中，行为人没有收钱，而是接受了性贿赂，定性有变化吗？" },
    { icon: <Layers className="w-3.5 h-3.5" />, label: "展开底层逻辑", text: "请详细讲讲这个判断背后的法理基础是什么？" },
  ];

  return (
    <div className="flex flex-wrap gap-2 pl-12">
      {actions.map((action, i) => (
        <button
          key={i}
          onClick={() => onActionSelect(action.text)}
          className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-full text-xs font-medium text-slate-600 hover:border-blue-300 hover:text-blue-700 hover:bg-blue-50/50 transition-colors shadow-sm"
        >
          {action.icon}
          {action.label}
        </button>
      ))}
    </div>
  );
}
