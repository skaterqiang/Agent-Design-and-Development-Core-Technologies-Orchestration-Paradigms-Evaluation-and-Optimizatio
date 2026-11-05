"""
使用 LangChain Deep Agents（deepagents）加载 docx Agent Skill，
由模型根据技能说明撰写内容并调用工具生成 Word 文档。

API Key 与《书中》其它示例一致，通过 common/config 的 get_api_key("tongyi") 获取
（见环境变量 TONGYI_API_KEY 或 config.py 中 tongyi 默认值）：

若暂无可用的 Key，可使用: python deepagent_docx_skills.py --offline
在本地直接生成样例 .docx，不调用大模型。

默认在调用大模型时使用 LangGraph 流式输出（`stream_mode`：messages / updates / values），
终端可逐段看到大模型内容、各节点与工具调用（含读取 SKILL 等）以及 `skills_metadata`；
`--no-stream` 可改回非流式 `invoke`。

依赖：deepagents、langchain-community、python-docx
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# 添加上层 common 目录到 Python 路径（与 chapter-2/2.4.1/brain_chattemplate.py 相同）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "common"))
from config import get_api_key, get_all_configs  # 从上层 common 导入

# 从 common/config.py 获取 API 密钥
API_KEY = get_api_key("tongyi")

from langchain_core.tools import tool
from langchain_community.chat_models.tongyi import ChatTongyi
from langgraph.checkpoint.memory import MemorySaver

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# 通义在「带 tools 的轮次」中可能关闭 incremental_output（SDK 限制），messages 流可能呈块级而非逐字


def _extract_text_from_message_chunk(tok: object) -> str:
    """从 LangGraph messages 流中的 token/chunk 取出可打印文本。"""
    if tok is None:
        return ""
    content = getattr(tok, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content) if content is not None else ""


def _print_skills_from_values(state: dict[str, object]) -> None:
    """在 values 模式下输出与 Skills 中间件相关的状态（元数据列表）。"""
    meta = state.get("skills_metadata")
    if not meta:
        return
    print("\n[Skills / 渐进式披露] 当前已注册技能元数据:", flush=True)
    items = meta if isinstance(meta, list) else [meta]
    for i, m in enumerate(items):
        if isinstance(m, dict):
            name = m.get("name", "?")
            desc = (m.get("description") or "")[:280]
        else:
            name = getattr(m, "name", "?")
            desc = (getattr(m, "description", None) or "")[:280]
        print(f"  ({i + 1}) {name}: {desc}", flush=True)


def _print_node_updates(updates: dict[str, object]) -> None:
    """输出 LangGraph 各节点增量：模型、工具、文件读写（含对 SKILL 的访问）。"""
    for node, patch in updates.items():
        if patch is None:
            continue
        print(f"\n[图节点] {node}", flush=True)
        if not isinstance(patch, dict):
            print(f"  {str(patch)[:500]}", flush=True)
            continue
        messages = patch.get("messages")
        if not isinstance(messages, list):
            continue
        for msg in messages:
            mname = type(msg).__name__
            if mname == "AIMessage":
                tcalls = getattr(msg, "tool_calls", None) or []
                for tc in tcalls:
                    if isinstance(tc, dict):
                        tname, args = tc.get("name", ""), tc.get("args", tc.get("arguments", {}))
                    else:
                        tname, args = getattr(tc, "name", ""), getattr(tc, "args", {})
                    print(f"  → 工具调用: {tname}  参数(截断): {str(args)[:200]}…", flush=True)
                    if tname == "read_file" and "SKILL.md" in str(args):
                        print("     (Skills) 按技能系统约定读取 SKILL.md 全文", flush=True)
                cont = getattr(msg, "content", "")
                if cont:
                    c = str(cont).strip()
                    if c:
                        print(f"  → 本段模型输出(截断): {c[:400]}…", flush=True)
            elif mname == "ToolMessage":
                tname = getattr(msg, "name", "")
                body = str(getattr(msg, "content", ""))
                print(f"  → 工具「{tname}」结果(截断): {body[:500]}…", flush=True)
                if tname == "read_file" and "docx" in body[:200]:
                    print("     (Skills) 可能为 docx 技能说明正文", flush=True)
            else:
                print(f"  → {mname} (截断) {str(msg)[:300]}…", flush=True)


def _run_agent_streaming(
    agent,
    user_task: str,
    thread: dict[str, object],
) -> object:
    """以流式方式运行 agent，输出 messages/updates/values，并返回最终 values 状态（若有）。"""
    last_values: dict[str, object] | None = None
    llm_header_printed = False
    last_skills_fp: str | None = None
    print("\n======== 流式执行开始（messages = 模型 token/块; updates = 节点与工具; values = 含 skills 元数据）========\n", flush=True)
    for event in agent.stream(
        {"messages": [{"role": "user", "content": user_task}]},
        {
            "recursion_limit": 80,
            **thread,
        },
        stream_mode=["messages", "updates", "values"],
    ):
        # 多 stream_mode 时每项为 (mode, payload)；subgraphs 默认 False
        if isinstance(event, tuple) and len(event) == 2:
            mode, payload = event[0], event[1]
        else:
            continue
        if mode == "messages":
            if not llm_header_printed:
                print("\n--- [流式] 大模型输出（通义在工具轮可能为块级流）---\n", flush=True)
                llm_header_printed = True
            # payload: (message_chunk, metadata_dict)
            if isinstance(payload, (list, tuple)) and len(payload) >= 1:
                tok = payload[0]
                text = _extract_text_from_message_chunk(tok)
                if text:
                    print(text, end="", flush=True)
        elif mode == "updates" and isinstance(payload, dict):
            _print_node_updates(payload)
        elif mode == "values" and isinstance(payload, dict):
            last_values = payload
            sm = payload.get("skills_metadata")
            fp = repr(sm) if sm is not None else None
            if sm is not None and fp != last_skills_fp:
                last_skills_fp = fp
                _print_skills_from_values(payload)
    if llm_header_printed:
        print("\n", flush=True)
    print("\n======== 流式执行结束 ========\n", flush=True)
    return last_values

BASE_DIR = Path(__file__).resolve().parent
SPEC_DIR = BASE_DIR / "output"
SCRIPT = BASE_DIR / "skills" / "docx" / "scripts" / "generate_docx.py"


def _safe_under_base(virtual_path: str) -> Path:
    """将虚拟路径解析为 BASE_DIR 下的真实路径，禁止跳出根目录。"""
    rel = virtual_path.strip().replace("\\", "/").lstrip("/")
    full = (BASE_DIR / rel).resolve()
    full.relative_to(BASE_DIR.resolve())
    return full


@tool
def render_docx_from_spec(spec_json: str, output_path: str) -> str:
    """根据 JSON 规格生成 Word 文档（.docx）。

    spec_json: 符合 docx/SKILL.md 中 Schema 的 JSON 字符串。
    output_path: 工作区虚拟路径，例如 /output/skills_technology_history.docx
    """
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    spec_path = SPEC_DIR / "_last_spec.json"
    out = _safe_under_base(output_path)

    try:
        parsed = json.loads(spec_json)
    except json.JSONDecodeError as e:
        return f"JSON 解析失败: {e}"
    spec_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")

    cmd = [sys.executable, str(SCRIPT), str(spec_path), str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR), encoding="utf-8")
    if proc.returncode != 0:
        return f"生成失败 (code={proc.returncode}): {proc.stderr or proc.stdout}"
    return f"已生成: {out}（相对示例目录: {out.relative_to(BASE_DIR)}）"


def _run_offline_docx() -> None:
    """不调用大模型，用内嵌 JSON 走同一套工具链，便于无 Key 时验证可运行。"""
    spec = {
        "title": "智能体与编程助手中的 Skills 技术发展史（离线样例）",
        "sections": [
            {
                "heading": "引言",
                "paragraphs": [
                    "自 IDE 插件与脚本的年代起，可复用能力就与编程环境绑定；大模型时代则演化为可编排的提示、工具与可加载技能包。"
                ],
            },
            {
                "heading": "阶段脉络",
                "paragraphs": [
                    "（1）经典工具链与扩展点：通过插件/脚本为编辑器或 IDE 增加能力。",
                    "（2）提示与检索：以模板、Few-shot 与 RAG 将领域知识注入对话。",
                    "（3）可声明 Agent Skills：以 SKILL 元数据 + 资源实现渐进式披露。",
                    "（4）生态整合：如 LangChain Deep Agents 将 skills 目录与虚拟文件体一起交给智能体。",
                ],
                "subsections": [
                    {
                        "heading": "llms.txt 与文档即技能",
                        "paragraphs": [
                            "将文档与索引以机器可读方式暴露，使智能体在需要时再拉取完整说明，与渐进式技能加载理念一致。",
                        ],
                    }
                ],
            },
            {
                "heading": "展望",
                "paragraphs": [
                    "技能与工具、子智能体、记忆将进一步分层；团队可独立维护技能目录，在一致 harness 上组合。",
                ],
            },
        ],
    }
    msg = render_docx_from_spec.invoke(
        {
            "spec_json": json.dumps(spec, ensure_ascii=False),
            "output_path": "/output/skills_technology_history.docx",
        }
    )
    print(msg)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError, AttributeError):
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except (OSError, ValueError, AttributeError):
            pass
    parser = argparse.ArgumentParser(description="Deep Agent + docx skill 示例")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="不调用大模型，用内置正文生成 /output/skills_technology_history.docx",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="关闭流式输出，改为一次性 invoke（调试用）",
    )
    args = parser.parse_args()
    if args.offline:
        print("使用 --offline：跳过 ChatTongyi 与 Deep Agent，仅执行 docx 工具链。")
        _run_offline_docx()
        return

    os.environ["DASHSCOPE_API_KEY"] = API_KEY
    logger.info("[CONFIG] 配置信息: %s", get_all_configs())
    model = ChatTongyi(
        model_name="qwen-max",
        dashscope_api_key=API_KEY,
        temperature=0.35,
        streaming=not args.no_stream,
    )

    backend = FilesystemBackend(root_dir=str(BASE_DIR), virtual_mode=True)
    checkpointer = MemorySaver()

    system_prompt = (
        "你是文档与智能体技术方向的写作助手。用户提出文档需求时，优先匹配并遵循已注入的 "
        "**docx** 技能：先阅读技能全文，再撰写符合 Schema 的 JSON，最后必须调用 "
        "`render_docx_from_spec` 生成文件。回复使用中文。"
    )

    agent = create_deep_agent(
        model=model,
        tools=[render_docx_from_spec],
        system_prompt=system_prompt,
        backend=backend,
        skills=["/skills/"],
        checkpointer=checkpointer,
    )

    user_task = (
        "请完成一篇面向技术读者的中文 Word 文档，主题：**智能体与编程助手中的 Skills 技术发展历史**。"
        "内容需覆盖：早期工具链与插件、提示词模板与 RAG、Anthropic Agent Skills / 渐进式披露、"
        "OpenAI Codex skills、LangChain Deep Agents 与 skills 目录规范、llms.txt 与文档即技能等脉络；"
        "最后简要展望。生成文件路径使用：/output/skills_technology_history.docx"
    )

    thread = {"configurable": {"thread_id": "docx-skills-history-1"}}
    config_run = {
        "recursion_limit": 80,
        **thread,
    }
    logger.info("调用 Deep Agent（含 docx skill + render_docx_from_spec）…")
    try:
        if args.no_stream:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_task}]},
                config_run,
            )
            last = result["messages"][-1]
            print("\n--- 模型最终回复 ---\n")
            print(getattr(last, "content", last))
        else:
            last_values = _run_agent_streaming(agent, user_task, thread)
            messages = (last_values or {}).get("messages") if last_values else None
            if isinstance(messages, list) and messages:
                last = messages[-1]
                print("--- 最终轮 assistant 消息（与上文流式应一致，便于对照）---\n")
                print(getattr(last, "content", last), flush=True)
    except ValueError as e:
        err = str(e)
        if "InvalidApiKey" in err or "401" in err or "API-key" in err:
            print(
                "API Key 被 DashScope 拒绝（InvalidApiKey / 401）。\n"
                "处理建议：\n"
                "  1) 在阿里云百炼 / DashScope 控制台创建新的 API Key；\n"
                "  2) 设置环境变量: $env:TONGYI_API_KEY='sk-...'（PowerShell）\n"
                "     若曾设置过 DASHSCOPE_API_KEY 且为旧值，请删除后重试或优先设置 TONGYI_API_KEY；\n"
                "  3) 无 Key 时可先 run: python deepagent_docx_skills.py --offline\n",
                file=sys.stderr,
            )
        raise


if __name__ == "__main__":
    main()
