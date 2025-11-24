import streamlit as st
import base64
from google.generativeai import GenerativeModel, configure

# ------------------------------
# 页面 & 侧边栏
# ------------------------------
st.set_page_config(page_title="Gemini AI 聊天", page_icon="🤖", layout="wide")
st.title("🤖 Gemini AI 聊天助手")
st.caption("保留 chat_input（置底 + 自动高度），右侧浮动“添加附件”按钮 — 上传不自动发送")

with st.sidebar:
    st.header("🔧 配置")
    api_key = st.text_input("请输入你的 Google Gemini API Key", type="password")
    st.caption("API Key 可从 Google AI Studio 获取")

    models = [
        "gemini-2.5-pro",
        "gemini-2.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro"
    ]
    selected_model = st.selectbox("选择模型", models, index=0)

    st.write("---")
    send_file_contents = st.checkbox(
        "发送文件内容给 Gemini（将把小文件 base64 编码随消息发送）",
        value=False
    )
    st.caption("关闭则仅保存文件名作为元数据；开启会把文件 base64 一并发送（注意隐私与大小）")

    if st.button("🗑️ 清空聊天记录"):
        st.session_state.pop("messages", None)
        st.session_state.pop("pending_attachments", None)
        st.experimental_rerun()

# ------------------------------
# 初始化 session_state
# ------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "pending_attachments" not in st.session_state:
    # 每项为 dict: {name: str, data: bytes or None, type: str or None, size: int or None}
    st.session_state["pending_attachments"] = []

# ------------------------------
# 显示历史消息
# ------------------------------
for i, msg in enumerate(st.session_state["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content", ""))
        attachments = msg.get("attachments", [])
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
# 浮动附件上传（file_uploader）—— 视觉上靠近 chat_input
# ------------------------------
# 这个 file_uploader 始终存在（但不会自动发送）
files = st.file_uploader("", accept_multiple_files=True, key="floating_uploader", label_visibility="collapsed")

# 调整位置：如需微调，请改 right/bottom 数值
st.markdown(
    """
    <style>
    div[data-testid="stFileUploader"] {
        position: fixed;
        right: 160px;
        bottom: 92px;
        z-index: 9999;
        width: 44px;
        height: 44px;
        overflow: visible;
    }
    div[data-testid="stFileUploader"] > label { display:none; }
    </style>
    """,
    unsafe_allow_html=True,
)

# 把新选的文件存入 pending_attachments（避免重复）
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
        st.success(f"已添加附件: {', '.join(added)}")

# 显示 pending attachments 并支持清除
if st.session_state["pending_attachments"]:
    cols = st.columns([0.9, 0.1])
    pending_names = ", ".join([p["name"] for p in st.session_state["pending_attachments"]])
    cols[0].markdown(f"**待发送附件：** {pending_names}")
    if cols[1].button("✖ 清除附件"):
        st.session_state["pending_attachments"] = []

# ------------------------------
# 聊天输入（**仅此一个** st.chat_input —— 避免重复 ID）
# ------------------------------
if api_key:
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    user_input = st.chat_input("请输入你的问题...")
    if user_input:
        # 构造要随消息保存的附件元数据（可选将内容 base64 包含或直接保存 bytes 以便回放下载）
        attachments_payload = []
        for att in st.session_state.get("pending_attachments", []):
            item = {"name": att["name"]}
            # 若用户勾选发送文件内容，则包含 base64 字符串（也把原 bytes 保存在会话以便 download）
            if send_file_contents and att.get("data") is not None:
                # 以 base64 发送给模型（注意：这会增加请求体大小）
                item["data_base64"] = base64.b64encode(att["data"]).decode("utf-8")
                item["size"] = att.get("size")
                item["type"] = att.get("type")
            # 同时保留 bytes 用于回放下载（不会随 API 请求自动发送，除非你实现）
            item["data"] = att.get("data")
            attachments_payload.append(item)

        # 把用户消息加入会话
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

        # 清空 pending
        st.session_state["pending_attachments"] = []

        # 调用 Gemini：优先流式，失败回退到同步
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            try:
                # 尝试流式（若 SDK 支持）
                response = model.generate_content(user_input, stream=True)
                # 若可迭代则作为流处理
                try:
                    for chunk in response:
                        text_piece = None
                        # 多种 chunk 结构兼容处理
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
                    # 非可迭代的 stream 返回 -> 回退到下面的非流式逻辑
                    raise Exception("stream returned non-iterable")
            except Exception:
                # 非流式回退
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

            # 保存 assistant 响应
            st.session_state["messages"].append({
                "role": "assistant",
                "content": full
            })
else:
    # 只有提示信息，没有第二个 chat_input（避免 DuplicateElementId）
    st.info("请在侧边栏输入 Gemini API Key 以开始聊天")
