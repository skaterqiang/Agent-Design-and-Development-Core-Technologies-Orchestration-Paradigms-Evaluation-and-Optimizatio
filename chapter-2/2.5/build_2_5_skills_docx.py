# -*- coding: utf-8 -*-
"""生成第 2 章「2.5 Skills」书稿节 Word 文件。"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _set_run_font(run, name: str, size_pt: float | None = None) -> None:
    run.font.name = name
    r = run._element.rPr
    if r is None:
        r = OxmlElement("w:rPr")
        run._element.insert(0, r)
    rfonts = r.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        r.set(qn("w:eastAsia"), name)
        r.append(rfonts)
    rfonts.set(qn("w:eastAsia"), name)
    if size_pt is not None:
        run.font.size = Pt(size_pt)


def _para(doc: Document, text: str, *, bold: bool = False) -> None:
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = bold
    for rr in p.runs:
        _set_run_font(rr, "宋体", 10.5)


def _bullets(doc: Document, items: list[str]) -> None:
    for t in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = None
        r = p.add_run(t)
        _set_run_font(r, "宋体", 10.5)


def _mono_para(doc: Document, text: str, size: float = 9) -> None:
    """等宽小字，用于路径、命令与代码片段（便于与正文区分）。"""
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.name = "Courier New"


def build() -> Document:
    doc = Document()
    t = doc.add_heading("2.5 Skills：从工具调用到可编排的技能体系", level=0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in t.runs:
        _set_run_font(run, "黑体", 16)

    intro = (
        "在 2.2.3 节中，我们曾将 RAG 与 Skills 并置讨论：二者都通过「把外部信息注入生成过程」来增强大模型，"
        "但侧重点并不相同。前两节已系统介绍了提示工程、思维链与 RAG 的技术路线；"
        "从本节开始，我们将「Skills」单列为智能体技术栈中的独立构件——它既是工具能力的组织方式，"
        "也是领域知识与操作流程的「可复用包装」。掌握 Skills 的设计与装载方式，是从「会调 API」"
        "走向「可维护、可演进的智能体系统」的重要一步。本节将说明 Skills 的概念边界、与 RAG/工具调用的关系、"
        "渐进式披露等关键机制；2.5.5 节与仓库目录 chapter-2/2.5 中的主程序、技能包与流式输出代码逐项对照，读者应结合源文件阅读。"
    )
    _para(doc, intro)

    # 2.5.1
    h1 = doc.add_heading("2.5.1 概念与定位：技能包与「手脚」的再组织", level=1)
    for run in h1.runs:
        _set_run_font(run, "黑体", 14)
    _para(
        doc,
        "若将大模型比作智能体的「大脑」、将单次函数调用比作「伸一次手」，那么 Skills 试图回答的问题是："
        "如何将一组与某类任务相关的说明、约定、资源甚至脚本，打包成模型可按需加载的「技能单元」，"
        "而不是在系统提示中一次性塞满所有细节。",
    )
    _para(doc, "1. 与 Function Calling、MCP 的关系", bold=True)
    _bullets(
        doc,
        [
            "Function Calling：定义「单步动作」的接口与参数，解决的是模型如何触发计算或查询。",
            "MCP 等工具总线：解决的是工具如何被发现、鉴权与传输，偏连接与治理层。",
            "Skills：在二者之上，强调「完成某类任务时应遵循的流程、术语与资源」的封装，常以外置目录、"
            "元数据 + 正文的形态存在，使同一智能体可在不同任务上加载不同技能包。",
        ],
    )
    _para(doc, "2. 典型形态", bold=True)
    _bullets(
        doc,
        [
            "行业/岗位技能包：如「写财报摘要」「做代码评审清单」的说明与样例。",
            "产品技能包：如对接本企业 API 的字段约定、错误码说明与最小示例。",
            "与「手脚」2.1.3 节呼应：工具仍是原子能力，Skills 是围绕任务场景对工具、提示与材料的有序编组。",
        ],
    )

    # 2.5.2
    h1 = doc.add_heading("2.5.2 核心机制：渐进式披露与可附带资源", level=1)
    for run in h1.runs:
        _set_run_font(run, "黑体", 14)
    _para(
        doc,
        "为节约上下文并减少无关指令干扰，业界广泛采用与文档「llms.txt」思想相近的「渐进式披露」策略："
        "先只向模型展示技能的摘要（例如名称、适用场景、一两句描述），当用户任务与某技能匹配时，"
        "再读取该技能的完整说明及附属文件。这样，智能体既不会遗漏专长，又不会在每一轮都携带全部长文档。",
    )
    _para(doc, "1. 常见工程约定", bold=True)
    _bullets(
        doc,
        [
            "以 SKILL 说明文件为入口，配合 YAML/Frontmatter 描述名称、description、许可与兼容性。",
            "同目录可附带：脚本、参考手册片段、版式模板等；由技能说明中点名路径与使用时机。",
            "在具备虚拟文件或工作区能力的环境中，智能体通过 read 类工具按路径加载，从而与具体框架解耦。",
        ],
    )
    _para(doc, "2. 与 2.1.2「记忆」的对比", bold=True)
    _para(
        doc,
        "向量化记忆侧重「相似度检索到的片段」；Skills 更侧重「可执行的、结构化的操作说明与任务边界」。"
        "二者可并存：RAG 提供事实素材，Skills 提供「怎么用好这些素材与工具」的领域流程。",
    )

    # 2.5.3
    h1 = doc.add_heading("2.5.3 与 RAG 的对照及适用边界", level=1)
    for run in h1.runs:
        _set_run_font(run, "黑体", 14)
    _para(
        doc,
        "2.2.3 节指出：RAG 与 Skills 都可在广义上视为给生成阶段「加餐」。为便于在项目中做架构选型，"
        "可按下表从检索对象、更新方式与评价指标三方面加以区分。",
    )
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "维度"
    hdr[1].text = "RAG"
    hdr[2].text = "Skills（技能包）"
    row2 = table.add_row().cells
    row2[0].text = "检索/加载对象"
    row2[1].text = "文档片段、知识库条目，偏静态文本与向量相似度"
    row2[2].text = "技能元数据、任务流程与附属资源，偏结构化说明与路径引用"
    row3 = table.add_row().cells
    row3[0].text = "更新与维护"
    row3[1].text = "增删改文档、重切分、重索引、评测检索命中率等"
    row3[2].text = "修订 SKILL 文本与配套脚本、在仿真任务上回归"
    row4 = table.add_row().cells
    row4[0].text = "适用侧重"
    row4[1].text = "事实性问答、长文档依有据引用"
    row4[2].text = "可重复流程、对输出格式/步骤有强约束的专业任务"
    _para(
        doc,
        "当业务既需要企业知识又需要强流程时，推荐「RAG 提供材料 + Skills 约束步骤与工具使用顺序」的混合架构。",
    )

    # 2.5.4
    h1 = doc.add_heading("2.5.4 在主流技术栈中的落点", level=1)
    for run in h1.runs:
        _set_run_font(run, "黑体", 14)
    _bullets(
        doc,
        [
            "LangChain 生态中的 Deep Agents 等：支持将 skills 目录作为来源，在运行时与任务规划、"
            "文件类工具、子智能体等能力组合。",
            "开源社区与「Agent Skills」类规范：强调 SKILL 描述文件、渐进式阅读与可审计的资源引用。",
            "与 2.4.1、2.4.2 的框架叙述一致：高代码路线便于把 Skills 与图编排、检查点、观测深度整合；"
            "低代码/平台型产品则常将「技能/插件/知识库」以产品化菜单呈现，抽象层级不同、目标一致。",
        ],
    )

    # 2.5.5 — 与本书代码逐块对照
    h1 = doc.add_heading("2.5.5 与本书代码对照：chapter-2/2.5 工程导读", level=1)
    for run in h1.runs:
        _set_run_font(run, "黑体", 14)
    _para(
        doc,
        "以下小节与仓库目录 chapter-2/2.5 中的源文件一一对应，建议读者打开工程同步阅读。运行前请按第 2.3.4、2.3.5 节"
        "配置通义/百炼 API Key；本节额外依赖见同目录下 requirements.txt（deepagents、langchain-community、python-docx 等）。",
    )

    _para(doc, "（1）目录与文件职责", bold=True)
    _bullets(
        doc,
        [
            "deepagent_docx_skills.py：主入口。创建 ChatTongyi、FilesystemBackend、create_deep_agent，注册技能路径与 "
            "render_docx_from_spec 工具，支持流式/非流式与离线模式。",
            "skills/docx/SKILL.md：docx 技能的说明与元数据（Frontmatter 中的 name、description 供 Skills 中间件做「匹配」；"
            "正文约定 JSON Schema 与对 render_docx_from_spec 的调用方式）。",
            "skills/docx/scripts/generate_docx.py：用 python-docx 将 JSON 规格写成真正 .docx 文件，由工具在子进程中调用。",
            "output/：虚拟路径 /output/... 经 _safe_under_base 落盘到本目录下，如 skills_technology_history.docx。",
            "build_2_5_skills_docx.py：独立脚本，用 python-docx 直接生成本节书稿（含表格），与智能体无运行时耦合，"
            "便于定稿与排版。",
        ],
    )

    _para(doc, "（2）与第二章前文一致的密钥注入方式", bold=True)
    _para(
        doc,
        "主程序用与 2.4.1 节 brain_chattemplate 相同方式把 code/common 加入 sys.path，并执行 get_api_key(\"tongyi\")、"
        "get_all_configs()，将 API_KEY 赋给环境变量 DASHSCOPE_API_KEY 与 ChatTongyi，从而与 2.3.5 节通义调用示例保持同一套配置习惯。",
    )
    _mono_para(
        doc,
        "sys.path.insert(0, os.path.join(os.path.dirname(__file__), \"../..\", \"common\"))\n"
        "API_KEY = get_api_key(\"tongyi\")",
    )

    _para(doc, "（3）Deep Agent 装配：虚拟盘、技能来源与检查点", bold=True)
    _para(
        doc,
        "FilesystemBackend(root_dir=本节目录, virtual_mode=True) 将磁盘根映射为以 / 开头的虚拟路径，与 Deep Agents 对 skills 约定一致。"
        "create_deep_agent 传入 skills=[\"/skills/\"]，运行时会扫描该目录下子文件夹中的 SKILL.md，把各技能的摘要注入系统提示，"
        "需要时再经内置 read_file 等工具拉取完整正文，这正是上一小节所述的「渐进式披露」在实现层的体现。",
    )
    _mono_para(
        doc,
        "backend = FilesystemBackend(root_dir=str(BASE_DIR), virtual_mode=True)\n"
        "create_deep_agent(..., skills=[\"/skills/\"], tools=[render_docx_from_spec], checkpointer=MemorySaver(), ...)",
    )
    _para(
        doc,
        "checkpointer=MemorySaver() 为 LangGraph 提供线程级检查点，便于多轮/重入（本示例的 thread_id 在 configurable 中给出）。",
    )

    _para(doc, "（4）自定义业务工具与渲染脚本解耦", bold=True)
    _para(
        doc,
        "Deep Agent 在普通文件系统后端上不会向宿主开放任意 shell 执行，因此将「写 Word」实现为 @tool 装饰的 render_docx_from_spec："
        "在宿主进程内 json.loads 校验后，用 subprocess 调用同目录下 generate_docx.py，把规格 JSON 与目标路径作为命令行参数。"
        "输出路径使用虚拟形式（如 /output/xxx.docx），由 _safe_under_base 防路径穿越。技能 SKILL.md 中明确要求模型最终必须调用此工具，"
        "与 2.1.3 节「规划—请求—执行—回写结果」的工具闭环一致。",
    )

    _para(doc, "（5）流式执行：在终端「看见」Skills 与模型", bold=True)
    _para(
        doc,
        "默认不传入 --no-stream 时，模型以 streaming=True 工作，主循环通过 agent.stream(..., stream_mode=["
        "\"messages\", \"updates\", \"values\"]) 消费事件：values 中首次出现的 skills_metadata 会列出已注册技能（如 docx）的 name、description；"
        "updates 中可看到各图节点上 AIMessage 的 tool_calls及 ToolMessage 结果，例如对 read_file 且路径含 SKILL.md 的调用，"
        "与书中「先匹配摘要、再读全文」的叙述相互印证；messages 分支则流式输出通义返回的正文。通义在带 tools 的轮次上可能为块级输出，"
        "主程序文件头注释已说明此限制。",
    )

    _para(doc, "（6）命令行参数与可运行性", bold=True)
    _bullets(
        doc,
        [
            "默认：需要有效 Key，全链路执行用户任务并流式打印。",
            "--offline：不调用大模型，仅以内置 JSON 调用 render_docx_from_spec，验证无 Key 时工具与 generate_docx.py 仍可用。",
            "--no-stream：改为 agent.invoke，便于与流式输出对照或缩小日志。",
        ],
    )
    _mono_para(doc, "python deepagent_docx_skills.py\npython deepagent_docx_skills.py --offline\npython deepagent_docx_skills.py --no-stream")
    _para(
        doc,
        "若遇 InvalidApiKey/401，应按 2.3.4 节在百炼控制台检查密钥，并优先通过环境变量 TONGYI_API_KEY 提供，与主程序读取逻辑一致。",
    )

    _para(doc, "（7）书稿 Word 的生成", bold=True)
    _para(
        doc,
        "本节讲义的 Word 定稿由 build_2_5_skills_docx.py 生成，输出在 output/2.5_Skills_书稿节.docx；它展示表格、分级标题等排版，"
        "与智能体侧「根据技能拼 JSON 再渲染 docx」是两条线——前者是作者成稿工具，后者是 Skills + 工具链的示例。读者对比二者可理解："
        "技能描述的是「机器可消费的流程与数据形状」，人读书稿时仍用传统排版脚本即可。",
    )

    h1 = doc.add_heading("本节要点回顾", level=1)
    for run in h1.runs:
        _set_run_font(run, "黑体", 14)
    _bullets(
        doc,
        [
            "Skills 是在工具调用之上对「任务型知识与流程」的封装，常与渐进式披露配合使用。",
            "与 RAG 互补：RAG 偏事实检索，Skills 偏如何做、按何种约束做。",
            "工程上需同时关心技能描述质量、资源路径、版本与权限，与 MCP/工具总线的安全要求一致。",
            "对照 chapter-2/2.5 代码时，应串联：技能目录 + create_deep_agent + 业务工具 + 可选的流式观测，形成完整可运行闭环。",
        ],
    )
    return doc


def main() -> None:
    out = Path(__file__).resolve().parent / "output" / "2.5_Skills_书稿节.docx"
    out.parent.mkdir(parents=True, exist_ok=True)
    build().save(str(out))
    print(f"已生成: {out}")


if __name__ == "__main__":
    main()
