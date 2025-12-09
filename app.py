# app.py
import streamlit as st
import streamlit.components.v1 as components
import base64
import json
from google.generativeai import GenerativeModel, configure

# ------------------------------
# 页面配置（尽早调用）
# ------------------------------
st.set_page_config(page_title="Gemini AI 聊天", page_icon="🤖", layout="wide")

# ------------------------------
# 兼容性：安全重载（支持 st.rerun 与 st.experimental_rerun）
# ------------------------------
def safe_rerun():
    if hasattr(st, "rerun"):
        try:
            st.rerun()
            return
        except Exception:
            pass
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
            return
        except Exception:
            pass
    st.warning("无法自动刷新页面，请手动刷新浏览器以应用更改。")

# ------------------------------
# localStorage 交互：读取与写入封装（通过 components.html 执行 JS）
# ------------------------------
def read_localstorage_once(key: str, comp_key: str):
    """
    通过 components.html 读取 localStorage[key]，并返回 Python 中的值（字符串或 None）。
    comp_key 用来保证 components 的唯一性。
    """
    js = f"""
    <script>
    (function() {{
        const v = localStorage.getItem({json.dumps(key)});
        // 将值发送回 Python，作为 components.html 的返回值
        window.parent.postMessage({{isStreamlitMessage: true, value: v}}, "*");
    }})();
    </script>
    """
    try:
        val = components.html(js, height=0, key=comp_key)
    except Exception:
        # 某些环境可能抛异常，返回 None 表示无法读取
        val = None
    return val

def write_localstorage(key: str, value: str, comp_key: str):
    """
    将 value（字符串）写入 localStorage[key]。value 必须是字符串（JSON string 推荐）。
    """
    # value 已经是 Python 字符串，我们需要在 JS 源中作为字面量插入 -> 使用 json.dumps 安全转义
    js_value = json.dumps(value)
    js = f"""
    <script>
    (function() {{
        try {{
            localStorage.setItem({json.dumps(key)}, {js_value});
            window.parent.postMessage({{isStreamlitMessage: true, value: "OK"}}, "*");
        }} catch(e) {{
            window.parent.postMessage({{isStreamlitMessage: true, value: "ERR"}}, "*");
        }}
    }})();
    </script>
    """
    try:
        components.html(js, height=0, key=comp_key)
    except Exception:
        pass

# ------------------------------
# 初始化 session_state（尽早）
# ------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "pending_attachments" not in st.session_state:
    st.session_state["pending_attachments"] = []

# 标记：是否已经从 localStorage 恢复过（避免重复覆盖用户操作）
if "local_restored" not in st.session_state:
    st.session_state["local_restored"] = False

# ------------------------------
# 首次加载：尝试从 localStorage 恢复 api key 与 聊天记录
# ------------------------------
if not st.session_state["local_restored"]:
    # 读取 API Key（原样字符串）
    api_key_from_local = read_localstorage_once("gemini_api", comp_key="read_api_key")
    if api_key_from_local:
        # components.html 返回字符串或 JSON 字符串；localStorage 存储时我们存入原始字符串（password），因此直接赋值
        st.session_state["api_key_local"] = api_key_from_local
    else:
        st.session_state["api_key_local"] = ""

    # 读取历史聊天：localStorage 中我们保存为 JSON 字符串（列表），如果存在则解析
    history_raw = read_localstorage_once("gemini_history", comp_key="read_history")
    if history_raw:
        try:
            parsed = json.loads(history_raw)
            # 只在 session 为空时恢复（避免覆盖已存在对话）
            if not st.session_state["messages"]:
                st.session_state["messages"] = parsed if isinstance(parsed, list) else []
        except Exception:
            # 如果解析失败就忽略
            pass

    st.session_state["local_restored"] = True

# ------------------------------
# 页面头与侧边栏（所有 widget 明确 key）
# ------------------------------
st.title("🤖 Gemini AI 聊天助手")
st.caption("保留 chat_input（置底 + 自动高度），右下角浮动 📎 附件按钮 — 上传不自动发送")

with st.sidebar:
    st.header("🔧 配置")
    # 将恢复到 input 的默认值（优先使用 session_state 中恢复的 api_key_local）
    api_key_default = st.session_state.get("api_key_local", "")
    api_key = st.text_input("请输入你的 Google Gemini API Key", type="password", value=api_key_default, key="api_key_input")
    st.caption("API Key 可从 Google AI Studio 获取（此项仅保存在你的浏览器 localStorage，不会上传服务器）")

    models = [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-1.5-flash",
        "gemini-pro"
    ]
    selected_model = st.selectbox("选择模型", models, index=0, key="model_select")

    st.write("---")
    send_file_contents = st.checkbox(
        "发送文件内容给 Gemini（将把小文件 base64 编码随消息发送）",
        value=False,
        key="send_file_contents"
    )
    st.caption("关闭则仅保存文件名作为元数据；开启会把文件 base64 一并发送（注意隐私与大小）")

    # 清空聊天记录并清本地 localStorage 的按钮（提示确认）
    if st.button("🗑️ 清空聊天记录（同时清除本地缓存）", key="clear_all"):
        st.session_state["messages"] = []
        st.session_state["pending_attachments"] = []
        # 清除 localStorage 中的数据
        write_localstorage("gemini_history", "[]", comp_key="clear_history_js")
        write_localstorage("gemini_api", "", comp_key="clear_api_js")
        # 触发刷新
        safe_rerun()

    # 仅清空本地缓存（不清应用内 session）
    if st.button("🧹 清除浏览器本地缓存（保留当前页面对话）", key="clear_local_only"):
        write_localstorage("gemini_history", "[]", comp_key="clear_history_js2")
        write_localstorage("gemini_api", "", comp_key="clear_api_js2")
        st.success("浏览器 localStorage 已清除（刷新后将不会恢复先前的历史）")

# ------------------------------
# 如果 API Key 发生变化，写回 localStorage（保持本地持久化）
# ------------------------------
# 我们把 api_key 保存到 session_state 便于比较和避免重复写入
prev_saved_api = st.session_state.get("api_key_saved", "")
if api_key != prev_saved_api:
    # 保存到 localStorage（写入原始字符串）
    write_localstorage("gemini_api", api_key, comp_key=f"save_api_{hash(api_key) % 100000}")
    st.session_state["api_key_saved"] = api_key

# ------------------------------
# 渲染历史消息（来自 session_state["messages"]）
# ------------------------------
for i, msg in enumerate(st.session_state["messages"]):
    role = msg.get("role", "assistant")
    with st.chat_message(role):
        st.markdown(msg.get("content", ""))
        attachments = msg.get("attachments", []) or []
        if attachments:
            st.markdown("**附件：**")
            for j, att in enumerate(attachments):
                name = att.get("name")
                data = att.get("data")  # bytes or None
                if data:
                    st.download_button(
                        label=f"下载 {name}",
                        data=data,
                        file_name=name,
                        key=f"dl_{i}_{j}_{name}"
                    )
                else:
                    st.markdown(f"- {name}")

st.markdown("---")

# ------------------------------
# 浮动附件上传（file_uploader），显式 key 避免重复 id
# ------------------------------
files = st.file_uploader("", accept_multiple_files=True, key="floating_uploader", label_visibility="collapsed")

# CSS：浮动图标样式
st.markdown(
    """
    <style>
    div[data-testid="stFileUploader"] {
        position: fixed;
        right: 160px;
        bottom: 92px;
        z-index: 9999;
        width: 48px;
        height: 48px;
        padding: 0;
        overflow: visible;
    }
    div[data-testid="stFileUploader"] > label { display: none !important; }
    div[data-testid="stFileUploader"] > div {
        padding: 0 !important;
        margin: 0 !important;
        height: 0px !important;
        overflow: visible !important;
    }
    div[data-testid="stFileUploader"]::before {
        content: "📎";
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: #ffffff;
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
        font-size: 22px;
        position: absolute;
        right: 0;
        bottom: 0;
        z-index: 900;
        pointer-events: none;
    }
    div[data-testid="stFileUploader"] input[type="file"] {
        opacity: 0;
        width: 48px;
        height: 48px;
        position: absolute;
        right: 0;
        bottom: 0;
        z-index: 1000;
        cursor: pointer;
    }
    div[data-testid="stFileUploader"] span,
    div[data-testid="stFileUploader"] p {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 保存上传的文件到 pending_attachments（去重）
if files:
    selected = files if isinstance(files, list) else [files]
    added = []
    for f in selected:
        try:
            b = f.read()
        except Exception:
            b = None
        fingerprint = (f.name, len(b) if b is not None else -1)
        exists = any((p.get("name"), p.get("size")) == fingerprint for p in st.session_state["pending_attachments"])
        if not exists:
            st.session_state["pending_attachments"].append({
                "name": f.name,
                "data": b,
                "type": getattr(f, "type", None),
                "size": len(b) if b is not None else None
            })
            added.append(f.name)
    if added:
        st.success(f"已添加附件: {', '.join(added)}", icon="📎")

# 显示 pending attachments 并支持清除
if st.session_state["pending_attachments"]:
    cols = st.columns([0.88, 0.12])
    pending_names = ", ".join([p["name"] for p in st.session_state["pending_attachments"]])
    cols[0].markdown(f"**待发送附件：** {pending_names}")
    if cols[1].button("✖ 清除附件", key="clear_pending_btn"):
        st.session_state["pending_attachments"] = []

st.markdown("---")

# ------------------------------
# 聊天输入（唯一 st.chat_input，带 key）
# ------------------------------
if api_key:
    # 初始化模型（捕获异常以防 SDK 错误）
    try:
        configure(api_key=api_key)
        model = GenerativeModel(selected_model)
    except Exception as e:
        st.error(f"无法初始化 Gemini 模型：{e}")
        model = None

    user_input = st.chat_input("请输入你的问题...", key="main_chat_input")
    if user_input:
        # 构造附件 payload（含 base64 可选）
        attachments_payload = []
        for att in st.session_state.get("pending_attachments", []):
            item = {"name": att["name"]}
            if send_file_contents and att.get("data") is not None:
                item["data_base64"] = base64.b64encode(att["data"]).decode("utf-8")
                item["size"] = att.get("size")
                item["type"] = att.get("type")
            item["data"] = att.get("data")
            attachments_payload.append(item)

        # 保存用户消息到 session_state
        st.session_state["messages"].append({
            "role": "user",
            "content": user_input,
            "attachments": attachments_payload
        })
        with st.chat_message("user"):
            disp = user_input
            if attachments_payload:
                disp += "\n\n**附件:** " + ", ".join(a["name"] for a in attachments_payload)
            st.markdown(disp)

        # 清空 pending attachments（已经随消息保存）
        st.session_state["pending_attachments"] = []

        # 立刻把最新聊天记录写回 localStorage（以 JSON 字符串形式）
        try:
            history_json = json.dumps(st.session_state["messages"], ensure_ascii=False)
            write_localstorage("gemini_history", history_json, comp_key=f"save_history_{hash(history_json) % 100000}")
        except Exception:
            pass

        # 调用 Gemini：优先流式，失败回退同步
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            if model is None:
                st.error("模型未正确初始化，无法生成回复。")
                full = "[错误：模型未初始化]"
            else:
                try:
                    response = model.generate_content(user_input, stream=True)
                    try:
                        for chunk in response:
                            text_piece = None
                            if hasattr(chunk, "text"):
                                text_piece = getattr(chunk, "text")
                            elif isinstance(chunk, dict):
                                text_piece = chunk.get("text") or chunk.get("output_text")
                            else:
                                text_piece = str(chunk)
                            if text_piece:
                                full += text_piece
                                placeholder.markdown(full + "▌")
                        placeholder.markdown(full)
                    except TypeError:
                        raise Exception("stream returned non-iterable")
                except Exception:
                    try:
                        response = model.generate_content(user_input)
                        text = None
                        if hasattr(response, "text"):
                            text = getattr(response, "text")
                        elif isinstance(response, dict):
                            text = response.get("text") or response.get("output_text")
                            if not text:
                                candidates = response.get("candidates") or response.get("outputs") or []
                                if candidates and isinstance(candidates, list):
                                    first = candidates[0]
                                    if isinstance(first, dict):
                                        text = first.get("content") or first.get("text") or first.get("output_text")
                                    else:
                                        text = str(first)
                        if not text:
                            text = str(response)
                        full = text
                        placeholder.markdown(full)
                    except Exception as e:
                        st.error(f"调用 Gemini 出错：{e}")
                        full = "[错误：无法获得模型响应]"

            # 保存 assistant 响应到 session_state
            st.session_state["messages"].append({
                "role": "assistant",
                "content": full
            })

            # 保存回 localStorage（确保 assistant 回复也持久化）
            try:
                history_json = json.dumps(st.session_state["messages"], ensure_ascii=False)
                write_localstorage("gemini_history", history_json, comp_key=f"save_history_after_{hash(history_json) % 100000}")
            except Exception:
                pass

else:
    # 未输入 API Key 时显示引导（不创建重复控件）
    st.info("请在侧边栏输入 Gemini API Key 以开始聊天", icon="ℹ️")

# ------------------------------
# 额外：提供导出/导入聊天记录（JSON）
# ------------------------------
cols = st.columns([0.7, 0.3])
with cols[0]:
    if st.button("📤 导出聊天记录为 JSON", key="export_json"):
        try:
            out_json = json.dumps(st.session_state["messages"], ensure_ascii=False, indent=2)
            st.download_button("下载聊天记录（JSON）", data=out_json.encode("utf-8"), file_name="gemini_history.json", mime="application/json", key="download_history")
        except Exception as e:
            st.error(f"导出失败：{e}")

with cols[1]:
    uploaded = st.file_uploader("📥 导入聊天记录（JSON）", type=["json"], key="import_history")
    if uploaded is not None:
        try:
            raw = uploaded.read().decode("utf-8")
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                st.session_state["messages"] = parsed
                # 保存到 localStorage
                write_localstorage("gemini_history", json.dumps(parsed, ensure_ascii=False), comp_key="import_save_history")
                st.success("已导入聊天记录并保存到本地缓存。")
                safe_rerun()
            else:
                st.error("导入文件格式不正确：应为消息对象数组（list）")
        except Exception as e:
            st.error(f"导入失败：{e}")
