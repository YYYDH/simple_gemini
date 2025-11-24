import streamlit as st
import base64
from google.generativeai import GenerativeModel, configure

# ------------------------------
# 兼容性：安全重载函数（适配不同 Streamlit 版本）
# ------------------------------
def safe_rerun():
    """
    在新版 Streamlit 中使用 st.rerun()，
    旧版（或某些环境）可能只有 st.experimental_rerun()。
    如果两者都没有，则显示提示（不会抛异常）。
    """
    if hasattr(st, "rerun"):
        try:
            st.rerun()
            return
        except Exception:
            # 若 rerun 存在但调用失败，尝试 experimental_rerun
            pass
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
            return
        except Exception:
            pass
    # 无法自动重载，提示用户手动刷新
    st.warning("无法自动刷新页面，请手动刷新浏览器以应用更改。")

# ------------------------------
# 先初始化 session_state（必须在 UI 组件之前）
# ------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "pending_attachments" not in st.session_state:
    # 每项为 dict: {name: str, data: bytes or None, type: str or None, size: int or None}
    st.session_state["pending_attachments"] = []

# ------------------------------
# 页面 & 侧边栏
# ------------------------------
st.set_page_config(page_title="Gemini AI 聊天", page_icon="🤖", layout="wide")
st.title("🤖 Gemini AI 聊天助手")
st.caption("保留 chat_input（置底 + 自动高度），右下角浮动 📎 附件按钮 — 上传不自动发送")

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

    # 清空聊天记录：用赋空替代 pop，确保键存在且行为可预期
    if st.button("🗑️ 清空聊天记录"):
        st.session_state["messages"] = []
        st.session_state["pending_attachments"] = []
        # 使用兼容函数触发页面重载
        safe_rerun()

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
# 浮动 📎 附件上传（file_uploader，但样式成图标）
# ------------------------------
files = st.file_uploader("", accept_multiple_files=True, key="floating_uploader", label_visibility="collapsed")

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
# 聊天输入（**仅此一个** st.chat_input —— 避免 DuplicateElementId）
# ------------------------------
if api_key:
    # 仅在有 api_key 时配置并实例化 model
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    user_input = st.chat_input("请输入你的问题...")
    if user_input:
        # 构造要随消息保存的附件元数据（可选将内容 base64 包含或直接保存 bytes 以便回放下载）
        attachments_payload = []
        for att in st.session_state.get("pending_attachments", []):
            item = {"name": att["name"]}
            if send_file_contents and att.get("data") is not None:
                item["data_base64"] = base64.b64encode(att["data"]).decode("utf-8")
                item["size"] = att.get("size")
                item["type"] = att.get("type")
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
                # 有些版本的 SDK 不支持 stream kw；这里用 try/except 回退到同步
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
                    # stream 返回不可迭代或 SDK 不同返回结构，抛到外层同步获取
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

            # 保存 assistant 响应
            st.session_state["messages"].append({
                "role": "assistant",
                "content": full
            })
else:
    # 只有提示信息，没有第二个 chat_input（避免 DuplicateElementId）
    st.info("请在侧边栏输入 Gemini API Key 以开始聊天")    send_file_contents = st.checkbox(
        "发送文件内容给 Gemini（将把小文件 base64 编码随消息发送）",
        value=False
    )
    st.caption("关闭则仅保存文件名作为元数据；开启会把文件 base64 一并发送（注意隐私与大小）")

    # 清空聊天记录：用赋空替代 pop，确保键存在且行为可预期
    if st.button("🗑️ 清空聊天记录"):
        st.session_state["messages"] = []
        st.session_state["pending_attachments"] = []
        # 触发页面重载（放在按钮处理内是安全的）
        st.experimental_rerun()

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
# 浮动 📎 附件上传（file_uploader，但样式成图标）
# ------------------------------
files = st.file_uploader("", accept_multiple_files=True, key="floating_uploader", label_visibility="collapsed")

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
# 聊天输入（**仅此一个** st.chat_input —— 避免 DuplicateElementId）
# ------------------------------
if api_key:
    # 仅在有 api_key 时配置并实例化 model
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    user_input = st.chat_input("请输入你的问题...")
    if user_input:
        # 构造要随消息保存的附件元数据（可选将内容 base64 包含或直接保存 bytes 以便回放下载）
        attachments_payload = []
        for att in st.session_state.get("pending_attachments", []):
            item = {"name": att["name"]}
            if send_file_contents and att.get("data") is not None:
                item["data_base64"] = base64.b64encode(att["data"]).decode("utf-8")
                item["size"] = att.get("size")
                item["type"] = att.get("type")
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
                # 有些版本的 SDK 不支持 stream kw；这里用 try/except 回退到同步
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
                    # stream 返回不可迭代或 SDK 不同返回结构，抛到外层同步获取
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

            # 保存 assistant 响应
            st.session_state["messages"].append({
                "role": "assistant",
                "content": full
            })
else:
    # 只有提示信息，没有第二个 chat_input（避免 DuplicateElementId）
    st.info("请在侧边栏输入 Gemini API Key 以开始聊天")
