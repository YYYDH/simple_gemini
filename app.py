# app.py — 完整、已修正版本（确保所有 widget 都有唯一 key）
import streamlit as st
import base64
from google.generativeai import GenerativeModel, configure

# ------------------------------
# 页面配置（必须最先调用）
# ------------------------------
st.set_page_config(page_title="Gemini AI 聊天", page_icon="🤖", layout="wide")

# ------------------------------
# 兼容性：安全重载（支持旧版和新版 Streamlit）
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
    # 无法自动刷新时给用户提示（不抛异常）
    st.warning("无法自动刷新页面，请手动刷新浏览器以应用更改。")

# ------------------------------
# 初始化 session_state（尽早）
# ------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "pending_attachments" not in st.session_state:
    st.session_state["pending_attachments"] = []

# ------------------------------
# 页面主标题与说明（只渲染一次）
# ------------------------------
st.title("🤖 Gemini AI 聊天助手")
st.caption("保留 chat_input（置底 + 自动高度），右下角浮动 📎 附件按钮 — 上传不自动发送")

# ------------------------------
# 侧边栏（所有控件都带 key，避免重复 id）
# ------------------------------
with st.sidebar:
    st.header("🔧 配置")
    api_key = st.text_input("请输入你的 Google Gemini API Key", type="password", key="api_key_input")
    st.caption("API Key 可从 Google AI Studio 获取")

    models = [
        "gemini-2.5-pro",
        "gemini-2.5-pro-latest",
        "gemini-1.5-pro",
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

    # 清空聊天记录（使用唯一 key）
    if st.button("🗑️ 清空聊天记录", key="clear_chat_btn"):
        st.session_state["messages"] = []
        st.session_state["pending_attachments"] = []
        safe_rerun()

# ------------------------------
# 渲染历史消息（从 session_state）
# ------------------------------
for i, msg in enumerate(st.session_state["messages"]):
    # msg["role"] 应为 "user" 或 "assistant"
    role = msg.get("role", "assistant")
    with st.chat_message(role):
        st.markdown(msg.get("content", ""))
        attachments = msg.get("attachments", []) or []
        if attachments:
            st.markdown("**附件：**")
            for j, att in enumerate(attachments):
                name = att.get("name")
                data = att.get("data")  # bytes or None
                # 下载按钮也要 unique key（含索引）
                if data:
                    st.download_button(
                        label=f"下载 {name}",
                        data=data,
                        file_name=name,
                        key=f"dl_{i}_{j}_{name}"
                    )
                else:
                    # 仅显示文件名（没有内容）
                    st.markdown(f"- {name}")

st.markdown("---")

# ------------------------------
# 浮动 📎 附件上传（file_uploader），显式 key 避免冲突
# ------------------------------
files = st.file_uploader("", accept_multiple_files=True, key="floating_uploader", label_visibility="collapsed")

# CSS：把 file_uploader 定位成浮动图标（与原先相同）
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

# 把新上传的文件去重后存入 session_state["pending_attachments"]
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

# 显示待发送附件，并提供清除按钮（按钮带 key）
if st.session_state["pending_attachments"]:
    cols = st.columns([0.88, 0.12])
    pending_names = ", ".join([p["name"] for p in st.session_state["pending_attachments"]])
    cols[0].markdown(f"**待发送附件：** {pending_names}")
    if cols[1].button("✖ 清除附件", key="clear_pending_btn"):
        st.session_state["pending_attachments"] = []

# ------------------------------
# 聊天输入（唯一 st.chat_input，带 key）
# ------------------------------
if api_key:
    # 配置并实例化模型（包裹异常防止 SDK 崩溃）
    try:
        configure(api_key=api_key)
        model = GenerativeModel(selected_model)
    except Exception as e:
        st.error(f"无法初始化 Gemini 模型：{e}")
        model = None

    user_input = st.chat_input("请输入你的问题...", key="main_chat_input")
    if user_input:
        # 构造附件元数据（可选择把内容做 base64）
        attachments_payload = []
        for att in st.session_state.get("pending_attachments", []):
            item = {"name": att["name"]}
            if send_file_contents and att.get("data") is not None:
                item["data_base64"] = base64.b64encode(att["data"]).decode("utf-8")
                item["size"] = att.get("size")
                item["type"] = att.get("type")
            # 同时保留 bytes 以便后续下载
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

        # 清空 pending 附件（已随消息保存）
        st.session_state["pending_attachments"] = []

        # 调用模型：优先尝试流式，失败回退到同步
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            if model is None:
                st.error("模型未正确初始化，无法生成回复。")
                full = "[错误：模型未初始化]"
            else:
                try:
                    # 有的 SDK 版本支持 stream=True，有的则不支持
                    response = model.generate_content(user_input, stream=True)
                    try:
                        for chunk in response:
                            # 支持多种 chunk 结构
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
                        # 非迭代型 stream 返回 -> 触发同步回退
                        raise Exception("stream returned non-iterable")
                except Exception:
                    # 回退到同步模式，并尽力解析响应结构
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

            # 把 assistant 响应写入 session_state
            st.session_state["messages"].append({
                "role": "assistant",
                "content": full
            })
else:
    # 没有 API Key 时只显示引导信息（此处不会创建第二个 text_input）
    st.info("请在侧边栏输入 Gemini API Key 以开始聊天", icon="ℹ️")
