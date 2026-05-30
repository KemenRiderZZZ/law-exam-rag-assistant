import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
import sys
sys.stdout.reconfigure(encoding='utf-8')

text = PROJECT_ROOT / 'OCR原稿' / '柏浪涛真金题.md'.read_text(encoding='utf-8')

# 找每道题的题干首段内容（含考号）
qhead = list(re.finditer(r'\((20\d{2}-\d-\d{1,3}|20\d{2}\s*金题-\d-\d-\d{1,3})', text))
print(f'找到考号 {len(qhead)} 个')
# 把每道题首部输出
for i, m in enumerate(qhead[:60]):
    pos = m.start()
    chunk = text[max(0, pos-200):pos].rstrip()
    lines = chunk.split('\n')
    last = ''
    for ln in reversed(lines):
        if ln.strip():
            last = ln.strip()
            break
    print(f'#{i+1}: {last[:60]} || {m.group(0)}')
