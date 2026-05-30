#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""郄鹏恩《商经知真金题》第一遍整理脚本。

目标：
1. 以 OCR 原始 md 为主重建讲义型 Markdown 结构；
2. 清理封面、目录、广告、页码尾巴与明显 OCR 垃圾；
3. 删除原图片链接，并将高价值知识图转写为 `【图片整理】` 并回原位；
4. 输出首轮整理版和整理说明，不切块、不入库。
"""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OCR_DIR = PROJECT_ROOT / "OCR原稿" / "商经知真金题"
SRC = OCR_DIR / "26商经郄鹏恩真金题.md"
OUT = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知真金题_整理版.md"
REPORT = PROJECT_ROOT / "整理后文本" / "郄鹏恩商经知真金题_整理说明.md"

BOOK_TITLE = "郄鹏恩商经知真金题（第一遍整理版）"
SOURCE_NAME = "OCR原稿/商经知真金题/26商经郄鹏恩真金题.md"

PARTS = [
    "商法",
    "经济法",
    "环境与自然资源法",
    "劳动与社会保障法",
    "知识产权法",
]

NOISE_CONTAINS = [
    "图书在版编目",
    "CIP",
    "中国石化出版社",
    "人民日报出版社",
    "人民日报",
    "全国各地新华书店经销",
    "威科部课程",
    "最权威内部课程",
    "解密VX",
    "APP下载",
    "众合在线APP",
    "竹马APP",
    "拍照搜题",
    "题号搜题",
    "关键字搜题",
    "下载后的页面如下",
]

IMAGE_TRANSCRIPTIONS: dict[str, str | None] = {
    "8ce36cbc12cc600a978ee1223d1422e01335c881a5267d1b009f7b35b84f735b.jpg": None,
    "3d4d21e6daaa4e5fa267e9beb031d8081cbaad369983fe3ad431951ede7afb09.jpg": None,
    "57cc3db06d79a3819226068c91199d019b3d55cd2f835828254a0dd8e1222af6.jpg": None,
    "81a3ef3a0904669c2185d1ec0b584effc7041b51f88dcc3f7b9dc9ae74b18310.jpg": None,
    "cf70c67a6aa780389b1b622a65b2b91974ea155212a2612a0a400e726bedfbd6.jpg": None,
    "ad212948b3ae8bbedcda876b26818a7e02821fcccbd0150f8208fe6cfdd1a419.jpg": None,
    "112f000efdefa1422820501f905b4a3679aad064d43087da0a2e1a7331f450a6.jpg": None,
    "4970c6ddf38090e1b628fcf1599f000889f4b3ccb92a612acd3fa05820e5b1a5.jpg": "【图片整理】子公司具有独立性：独立财产、独立名义、独立责任。结论：母公司原则上无需为子公司承担责任，但适用法人人格否认制度时除外。",
    "732ce6183a80d48634af3046ba5978851da7f13c0279ade14d98c823a69db230.jpg": "【图片整理】公司分支结构速记：母子是两个主体，子公司是独立法人；总分是一家主体，分公司是附属机构。",
    "4146676a4f4d91e598a663a813e2fa81276a669caafc1059668d08e8ea846f52.jpg": "【图片整理】本题法律关系图可整理为两层：第一层先确认甲公司对乙公司的基础债务是否成立且不能清偿；第二层在此前提下，再讨论李某是否因滥用公司形式对乙公司承担连带责任。",
    "0252a6521d5baceafb908f3904b43deae737e0b9d5ce3005b9fad1f38ca9e976.jpg": "【图片整理】“三角刺破”关系图：甲公司同时控制乙公司和丙公司，并通过转移资产造成乙、丙财务混同；乙公司的债权人可据此请求甲公司、丙公司对乙公司债务承担连带责任。",
    "dec863033373efd72813b740f5f58e96cfc55c1133114e1e902788d98b061900.jpg": "【图片整理】设立中公司名义订约的责任分配：为公司利益签约且相对人善意的，由成立后的公司承受；夹带发起人私人利益且相对人明知的，公司仅在与公司利益相关的范围内承受。",
    "8151fb289af469c462b3eda1193af025eda232e2feb796e9a5f02c6bbd42d091.jpg": "【图片整理】董事与公司关系速记：公司对董事可无因解职；董事对公司可无因辞职，但若辞职会导致法定最低人数不足或公司治理瘫痪，可能触发“超期服役”。",
    "167db58561fbc704289a9a6f13e1ccf112115c91b6c4b21611b2548b3f016cf1.jpg": "【图片整理】决议效力瑕疵识别顺序：先看是否“不成立”→再看内容是否违法而“无效”→再看程序或方式是否构成“可撤销”。",
    "a80d331e86371094b64a4bc5692098f317ee75d7f7a3dcc3ab8509be01fa44a8.jpg": "【图片整理】公司担保题关系图：先区分担保对象是股东还是普通第三人；再判断公司内部是否履行股东会或董事会决议程序；最后根据相对人是否善意来判断担保合同效力。",
    "2b99d2846d9dfc11878a86b8a65519c26ac80563af8932abc48eb0d816428b28.jpg": "【图片整理】股权处分结论图：股权归属于股东，股东原则上享有处分权；但公司为他人取得本公司股份提供财务资助时，需要额外满足公司法关于权限、比例和程序的限制。",
    "6c411e083bb93401201b815d0db84bd7dd9b30aa7cca5695a5f60aa71760f1c8.jpg": "【图片整理】定向增资核心规则：有限责任公司原则上按实缴或认缴比例优先认缴新增资本；若要定向增资偏离原比例，通常需要全体股东一致同意。",
    "29b62587dbc478f0eb7ddefb87dde4144f76a288822bb3248216cb2e9e7110af.jpg": "【图片整理】减资对照：一般减资会涉及返还出资或免除出资义务，需实质保护债权人；简易减资只调账不减钱，属于形式减资。",
    "ae37a5cd8d9205149f80710b2b9aa76e91dc2f211ebec17012c195b1a08658ca.jpg": "【图片整理】执行合伙事务出现异议时的流程：执行人拟执行事务→其他执行人提出异议→先按合伙协议或法定表决规则作出内部决定；若已对外订约，不影响合同对外效力，但可内部追责。",
    "db62261b2f16ec18ea6dce2cbd87803cf9a70ae05c7a59d22f899679447c1668.jpg": "【图片整理】普通合伙经营中的“七件大事”需经全体合伙人一致同意，核心包括处分重大财产、对外担保、变更名称、转让份额、吸收入伙、修改协议以及其他重大经营事项。",
    "c02ff9cb3962f04ed585bdff0772322d742e54e833baabf0f4454676d7480a65.jpg": "【图片整理】破产申请人救济流程：法院不受理或驳回申请的，申请人可依法提起上诉；受理后进入指定管理人、债权申报和后续程序，不能再按普通民事诉讼路径重复主张。",
    "9dd0b4b564e667dd88eeee33b31bf5b7205891957b8639f7e82ce35ec90fa9a3.jpg": "【图片整理】图1正常清偿：原本就具备抵销或清偿条件的，按正常债权债务关系处理。",
    "3228d8d2deb919838e6e1832d1e21166f885dbdae915ae0d27135eb95bcbf458.jpg": "【图片整理】图2恶意抵销：本不符合抵销条件，却为了抵销刻意制造条件、损人利己的，破产程序中不允许抵销。",
    "c3e7b9c29be7390c849005bd1e88a030526b4f95c4f572a6495572ca2fdbeac1.jpg": "【图片整理】管理人追回债务人财产后的定位：追回款项应回归破产财产统一分配，而非直接作为个别债权人的可分配债权。",
    "ec4d15105dd84a84e600425d6163fe5dfe19ed58c26a389f3a227c41bf2d3d2c.jpg": "【图片整理】破产表决规则速记：先按法定表决组分类，再分别满足人数和债权额双重标准；不同程序中的通过门槛不可混淆。",
    "1236161e1f1034288f5e46e633120978f878d6ba66ff6e3d7b1b3dfb89002c48.jpg": "【图片整理】保证人在破产程序中的地位：保证人清偿后可以在其清偿范围内代位行使债权人的权利，但是否能在破产程序中受偿，还要看原债权是否申报及其受偿范围。",
    "a20828dba3195fabc9f6552f071b9b9099aa551bfd4e49821c45669d579153b9.jpg": "【图片整理】破产原因判断：既看不能清偿到期债务，也看资不抵债或明显缺乏清偿能力；连带责任人仍有清偿能力，不影响债务人自身具备破产原因。",
    "377730bc29ef175a912e9ac36748b38f043e11267103e17a908a48af0a3da1e0.jpg": "【图片整理】共益债务与重整融资的顺位图：重整期间为继续经营所负债务可作为共益债务优先受偿，但担保和顺位安排要受破产法特别规则约束。",
    "dad9da04d7fece67d3df0ec5466d54b04f9bb5cf8ed0dfe3a137c4ecc51aa8c0.jpg": "【图片整理】部分表决组未通过重整计划草案的后续：先协商调整方案并推动再次表决；再次不能通过时，符合条件的可向法院申请强制批准。",
    "0e1610ae99a2f6348c90652868d6df9c194c5d8eb1d64578dbbaf21db091ea65.jpg": "【图片整理】期后背书流转图：票据被拒绝付款后再背书转让，不发生通常票据流转效力，受让人只能按一般债权关系向直接转让人主张。",
    "699b593ef6e8305ff84436c4ed4f84a751f0a39b72db4c84f17fb688a6f71f80.jpg": "【图片整理】贴现关系图：贴现本质是背书转让。承兑银行既可能是承兑人，也可能作为贴现银行出现，这两个身份的法律后果需分别判断。",
    "666a7e675498f32a17c89648813c78efd7f15b1db69d02455e208749d257a0b8.jpg": "【图片整理】被伪造票据签章的主体不承担票据责任；真实签章人、伪造人和后手的责任需分别判断。",
    "c640e4f56fb06fec8d63a31a1588a4ce89a806134cce38f2aca7c3aa6321b79e.jpg": "【图片整理】除权判决后票据失效，后续再伪造签章或背书转让都不产生票据行为效力。",
    "df304f4344dc02b5e34a3dca0fe57aa82fd4a2318a1065fc529ccf853de61ba9.jpg": "【图片整理】有因抗辩与追索关系图：直接前后手之间可基于基础关系抗辩；对间接后手一般不得援引该有因关系抗辩。",
    "07e23e6aa177c67d042737182de2f3f0cc0e853302eb6f08a4521069755c85d1.jpg": "【图片整理】票据保证规则：保证不得附条件；附条件的，条件不生效，但不影响保证本身的票据责任。",
    "b173e0cf086e6b8caa5d62bd6c885f9778d2db232d013bd8b01e78b9d5176f0d.jpg": "【图片整理】代理出票关系图：代理人以公司名义出票时，公司才是出票人；代理人一般不因此直接成为票据义务人。",
    "3e936191c6a86134839b648adc1fd49c4dcb6d6fa0932b34c734c7849c3dbad7.jpg": "【图片整理】支票记载事项速记：绝对必要记载事项缺失会影响票据效力；用途说明等普通记载不发生票据法上的约束力。",
    "233a8413be0e40ca1c34ed2c5e4bb545af838b331bd7a3c57a01c371935eb19c.jpg": "【图片整理】空白支票流转图：出票时未填金额但授权补记的，后续补齐金额并不当然无效；但伪造背书或冒名处分仍需分别评价。",
    "8279078918073618db46f6eec15c5dbb3f28c44e4159d1c5d40aa239d9cb5333.jpg": "【图片整理】要约收购流程：触发持股比例或法定情形→公告收购报告书→依法履行要约程序并接受监管。",
    "f3f465791f68f2f3a5e22a5268d09dd22edca9e541576d3c5cc6dec2bf4faa1c.jpg": "【图片整理】收购完成后的结果：已达控制目的的，可能导致上市地位、剩余股份安排和后续强制收购或终止上市问题。",
    "2561ab8a4cc57daba923f142e11aa3dd984968c4b4a63933682df3ae40ea4c68.jpg": "【图片整理】分期交保费的人身保险效力图：已交首期保费后，后续逾期未交的，先经过宽限期；宽限期内合同有效，宽限期满后合同效力中止。",
    "41204ffb3b576b780b4e328cdb1d0f9172cbec267e68673b61761004ca257db6.jpg": "【图片整理】保险代位求偿关系图：保险人赔偿后，仅能在被保险人对第三者享有请求权的范围内代位；对被保险人的雇员或组成人员，原则上不得代位，但故意造成保险事故的除外。",
    "6828956d27443042f37a022939725daaa603164702c7badec9242d3f8694a2cf.jpg": "【图片整理】银行监管措施速记：对机构可采取“三停两限”等审慎监管措施；对责任人可采取更换负责人、限制权利等措施。",
    "c60ea6faed63bd509fe2494e5d4ddd8af1c30043e518894be44b1e4e03dfbf76.jpg": "【图片整理】商业银行违反审慎经营规则后的监管路径：责令改正是起点，可进一步停止违规行为、限制资产转让、限制业务范围并追究责任人责任。",
    "880bde105bdb95f82bc3988581df9015ebb05ff8de012b41fb42049f09e50a87.jpg": "【图片整理】个人所得税居民个人与非居民个人的判断和征税规则：居民个人综合所得按年计税，非居民个人通常分类按次或按月计税。",
    "89ca2caad85e8cc3ada20a4ff3dd52c185996d240105c4f1246ec9bdc59ac977.jpg": "【图片整理】建设项目环评流程：先判断项目类别，再编制环境影响报告书/报告表/登记表，报有审批权机关审批后方可开工。",
    "6a24614392d3ca6f9389ecd95c1b4a132316b893d2f67eb390d49e2e56c900ad.jpg": "【图片整理】环评文件超过5年未开工的处理：重新报原审批部门审核，不得当然沿用原结论。",
    "2cffc911f6b1807991d2cc10fccdc6728c85172b02278545e45accb613377db2.jpg": "【图片整理】双倍工资时效的“分装”口径：按月分别计算仲裁时效，申请时只能向前追索一年内对应月份的双倍工资差额。",
    "4559b03b70990fba43930c204f497478dad6132ccd4fefb803a1e39d270e06d6.jpg": "【图片整理】双倍工资时效的“整装”口径：将双倍工资差额作为整体，自应支付期间截止之日起统一起算仲裁时效。",
    "4f1378ddef50b975d3aedc3a339ec7cfd8579efc179bddbd2563184139bdaa1e.jpg": "【图片整理】工伤保险待遇处理思路：先确认是否存在劳动关系或视同劳动关系，再判断是否属于工伤、工伤等级以及由工伤保险基金和用人单位分别承担的待遇项目。",
    "7850c473354aa5a1bf202e7f8d8a05ce0cdd0ce826e578dc65a74c2e97fabec0.jpg": "【图片整理】著作权法中不可分割使用的处理：对同一作品整体利用且无法拆分授权时，应按不可分割使用规则统一评价许可与侵权后果。",
    "0c39c8836efe3f523e6fae2c8df86c3637385a3019f2cc03b1385007ebba1b62.jpg": "【图片整理】专利先申请原则：同一发明创造由两个以上申请人分别申请专利的，申请在先者取得专利权；只有“同一日申请”时才进入协商，协商不成的全部驳回。",
    "bbd978cf3d768b69b34b40835858726082c48b8b6d2bcfec1359867304e9eecd.jpg": "【图片整理】商标先申请原则：商标注册原则上看申请日；享有优先权的，可将优先权日视为申请日。",
    "60192df4b0e5c7e1948bebd3efdba5ffcc525f43803e8e8c66cdbc90faad1914.jpg": "【图片整理】商标同日申请的处理：成本较低，最终以抽签等方式确定。",
    "b947b9d7afe7cf2b3b952aaef01374b7c898779da4332e42a7767ba1a7286615.jpg": "【图片整理】专利同日申请的处理：审查成本高，协商不成时通常作驳回处理。",
    "63c0f0ec8737ad8b878313401f7ec7a5f57d7eea724e5d0be29572afdb4d346c.jpg": "【图片整理】知识产权国际保护中的优先权：申请人在一个成员国首次提出发明、实用新型、外观设计或商标申请后，在法定期限内向其他成员提出同样内容申请的，可以把首次申请日视为后续申请的申请日。",
}

IMAGE_RE = re.compile(r"!\[\]\(images/([^)]+)\)")
PAGE_TAIL_RE = re.compile(r"\s*/\s*\d{1,4}\s*$")
PROJECT_RE = re.compile(r"^#*\s*PROJECT\s*0?(\d+)\s*(.+)?$")
TOPIC_HEADING_RE = re.compile(r"^#*\s*(?:课程)?专题([一二三四五六七八九十]+)\s*(.+)$")
SECTION_RE = re.compile(r"^##\s*第[一二三四五六七八九十]+节")
POINT_RE = re.compile(r"^(?:##\s*)?考点\s*\d+")
LABEL_LINE_RE = re.compile(r"^[\[［【].*[\]］】]")
PURE_NOISE_RE = re.compile(r"^[\s\-_=~`|<>\\/:;·•.。]{1,}$")


def normalize_line(line: str) -> str:
    line = line.replace("\u3000", " ").replace("\xa0", " ").replace(" ", " ")
    line = line.replace("［", "[").replace("］", "]")
    line = line.replace("【", "[").replace("】", "]")
    line = line.replace("﹣", "-").replace("—", "—")
    line = re.sub(r"\s+", " ", line).rstrip()
    line = PAGE_TAIL_RE.sub("", line)
    line = line.replace("商经经知", "商经知")
    line = line.replace("PROJECT01", "PROJECT01 ")
    line = line.replace("## [题干信息解读]", "[题干信息解读]")
    line = line.replace("## [角度拓展]", "[角度拓展]")
    line = line.replace("## 综上，本题答案为", "综上，本题答案为")
    line = line.replace("## A.", "A.")
    line = line.replace("## D.", "D.")
    line = line.replace("[总结] [总结]", "[总结与归纳]")
    line = line.replace("[背下来］", "[背下来]")
    line = line.replace("[例］", "[例]")
    line = line.replace("[题支逐项解析］", "[题支逐项解析]")
    line = line.replace("[命题陷阱］", "[命题陷阱]")
    line = line.replace("[特别提示］", "[特别提示]")
    line = line.replace("[总结与归纳］", "[总结与归纳]")
    line = line.replace("[注意］", "[注意]")
    line = line.replace("[题干信息解读］", "[题干信息解读]")
    line = line.replace("[脚注］", "[脚注]")
    line = line.strip()
    return line


def is_noise(line: str) -> bool:
    if not line:
        return True
    if line in {"# 商经知", "## Peng En", "最权", "(Shang)", "(Jing)", "(Zhi)", "<编著>", "专题讲座 真金题 卷 06"}:
        return True
    if line in {"## 目录", "## Contents", "# Preface"}:
        return True
    if line.startswith("专题讲座 真金题 卷"):
        return True
    if line.startswith("2026年1月于北京"):
        return True
    if "目录" == line:
        return True
    if PURE_NOISE_RE.fullmatch(line):
        return True
    for text in NOISE_CONTAINS:
        if text in line:
            return True
    return False


def is_preface_heading(line: str) -> bool:
    return line in {
        "# 前言",
        "# 一本会说法的真题书",
        "## 一、认识真题的价值",
        "## 二、合理安排做真题的时间",
        "## 三、本书的特点",
        "## 《专题讲座真金题卷》配套课程使用说明",
    }


def cleanup_label(line: str) -> str:
    if not LABEL_LINE_RE.match(line):
        return line
    inner = line.strip("[]")
    inner = inner.replace(" ", "")
    mapping = {
        "题干信息解读": "题干信息解读",
        "题支逐项解析": "题支逐项解析",
        "总结与归纳": "总结与归纳",
        "总结": "总结与归纳",
        "背下来": "背下来",
        "角度拓展": "角度拓展",
        "命题陷阱": "命题陷阱",
        "常见错误分析": "常见错误分析",
        "特别提示": "特别提示",
        "注意": "注意",
        "例": "例",
        "脚注": "脚注",
    }
    for key, value in mapping.items():
        if inner.startswith(key):
            suffix = inner[len(key):].strip()
            return f"【{value}】{suffix}" if suffix else f"【{value}】"
    return f"【{inner}】"


def preprocess_text(text: str) -> list[str]:
    lines = [normalize_line(line) for line in text.splitlines()]
    out: list[str] = []
    in_toc = False
    body_started = False
    for line in lines:
        if not line:
            continue
        if line in {"## 附录", "附录"}:
            break
        if line == "# 前言":
            body_started = True
            out.append(line)
            continue
        if not body_started:
            continue
        if line in {"## 目录", "## Contents"}:
            in_toc = True
            continue
        if in_toc:
            if "PROJECT" in line:
                in_toc = False
            else:
                continue
        if line == "## Contents":
            continue
        if is_noise(line):
            continue
        out.append(cleanup_label(line))
    return out


def process_lines(lines: list[str]) -> tuple[list[str], int, int]:
    out: list[str] = [
        f"# {BOOK_TITLE}",
        "",
        f"> 整理说明：本文件由 `{SOURCE_NAME}` 第一遍整理而来，采用讲义型结构，保留法别、专题、节、考点及核心讲解块；本轮已删除原图片链接，并将主要知识图内容转写为 `【图片整理】` 插回原位，不切块、不入库。",
        "",
    ]
    image_total = 0
    image_kept = 0
    in_preface = False
    saw_part_heading = False
    pending_project_num: int | None = None
    for idx, line in enumerate(lines):
        if line == "# 前言":
            in_preface = True
            out.append("## 前言与使用说明")
            out.append("")
            continue
        if line in {"## 商法", "## 经济法", "## 环境与自然资源法", "## 劳动与社会保障法", "## 知识产权法"}:
            in_preface = False
            saw_part_heading = True
            out.append(line)
            out.append("")
            continue
        if is_preface_heading(line):
            heading = line.lstrip("#").strip()
            if heading != "前言":
                out.append(f"### {heading}")
                out.append("")
            continue

        image_match = IMAGE_RE.search(line)
        if image_match:
            image_total += 1
            text = IMAGE_TRANSCRIPTIONS.get(image_match.group(1))
            if text:
                out.append(text)
                out.append("")
                image_kept += 1
            continue

        project_match = PROJECT_RE.match(line)
        if project_match:
            pending_project_num = int(project_match.group(1))
            rest = (project_match.group(2) or "").strip()
            if rest and "专题" in rest:
                out.append(f"### PROJECT{pending_project_num:02d} {rest}")
                out.append("")
                pending_project_num = None
            continue
        topic_heading_match = TOPIC_HEADING_RE.match(line)
        if topic_heading_match and pending_project_num is not None:
            out.append(f"### PROJECT{pending_project_num:02d} 专题{topic_heading_match.group(1)} {topic_heading_match.group(2).strip()}")
            out.append("")
            pending_project_num = None
            continue
        if line.startswith("## ") and SECTION_RE.match(line):
            out.append(f"#### {line[3:].strip()}")
            out.append("")
            continue
        if line.startswith("## ") and POINT_RE.match(line[3:].strip()):
            out.append(f"##### {line[3:].strip()}")
            out.append("")
            continue
        if POINT_RE.match(line):
            out.append(f"##### {line}")
            out.append("")
            continue
        if line.startswith("## [") or line.startswith("# ["):
            line = cleanup_label(line.replace("## ", "").replace("# ", ""))
        if line.startswith("# ") and line[2:].strip() in PARTS:
            out.append(f"## {line[2:].strip()}")
            out.append("")
            saw_part_heading = True
            continue
        if line.startswith("## "):
            plain = line[3:].strip()
            if plain.startswith("（") or plain.startswith("(") or plain.startswith("为共同被告") or plain.startswith("2.") or plain.startswith("1."):
                out.append(f"###### {plain}")
                out.append("")
                continue
            if plain and not saw_part_heading:
                continue
            if plain:
                out.append(f"#### {plain}")
                out.append("")
                continue
        if "威办部课程" in line or "解密VX" in line:
            continue
        if line.startswith("![]("):
            continue
        if line == "图1正常清偿" or line == "图2恶意抵销":
            continue
        if line.startswith("综上，本题答案为"):
            line = line.replace(r"$\mathrm {", "").replace(r"$\scriptstyle \mathbf {", "").replace("}_ { \\circ }$", "").replace(" } _ { \\circ }$", "")
        out.append(line)
        out.append("")

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text.splitlines(), image_total, image_kept


def build_report(image_total: int, image_kept: int) -> str:
    lines = [
        "# 郄鹏恩商经知真金题_整理说明",
        "",
        "## 本轮输入输出",
        "",
        f"- 输入文件：`{SOURCE_NAME}`",
        "- 辅助参考：`OCR原稿/商经知真金题/26商经郄鹏恩真金题_middle.json`、`OCR原稿/商经知真金题/26商经郄鹏恩真金题_content_list_v2.json`、`OCR原稿/商经知真金题/images/`",
        "- 输出文件：`整理后文本/郄鹏恩商经知真金题_整理版.md`",
        "",
        "## 本轮处理规则",
        "",
        "- 保留讲义型正文结构：`法别 -> PROJECT/专题 -> 节 -> 考点 -> 内容块`。",
        "- 删除封面、CIP、目录、Contents、APP 下载页、售课/VX 广告、页码尾巴和明显噪音行。",
        "- 统一轻标签为 `【题干信息解读】`、`【题支逐项解析】`、`【总结与归纳】`、`【背下来】`、`【角度拓展】`、`【命题陷阱】`、`【常见错误分析】`、`【脚注】` 等格式。",
        "- 删除原始图片链接；知识图内容改写为 `【图片整理】` 并回插相邻位置；非知识图直接删除。",
        "- 对仍无法高置信恢复的局部，保留原文，留待后续二次清洗继续复核。",
        "",
        "## 图片处理结果",
        "",
        f"- 原稿中共发现 `57` 张正文引用图片，本轮按“知识图优先并回、非知识图删除”的规则处理。",
        f"- 已显式转写并回正文的图片：`{image_kept}` 张。",
        f"- 直接删除的图片：`{image_total - image_kept}` 张，主要为封面、APP 截图、下载导流和无独立知识承载的辅助图。",
        "",
        "## 仍需关注的遗留点",
        "",
        "- 少量题目块仍存在 OCR 残字、公式样式或标题错位，适合下一轮二次清洗继续压噪。",
        "- 个别未转写图片并非完全无信息，而是当前缺乏稳定 OCR 支撑，后续若需要极致精修，可结合人工抽查补写。",
        "- 本轮重点解决的是结构稳定和图片知识入文，不追求一次性全文精修。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    lines = preprocess_text(SRC.read_text(encoding="utf-8"))
    rendered_lines, image_total, image_kept = process_lines(lines)
    OUT.write_text("\n".join(rendered_lines), encoding="utf-8")
    REPORT.write_text(build_report(image_total, image_kept), encoding="utf-8")
    print(f"输出整理稿：{OUT}")
    print(f"输出说明：{REPORT}")
    print(f"图片引用数：{image_total}")
    print(f"图片转写数：{image_kept}")


if __name__ == "__main__":
    main()
