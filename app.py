import streamlit as st
import base64
from google.generativeai import GenerativeModel, configure

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
# 浮动 📎 附件上传（file_uploader，但样式成图标）
# ------------------------------
# 真实上传控件（负责接收文件），但我们用 CSS 把默认区域隐藏，并绘制一个圆形 📎 图标
files = st.file_uploader("", accept_multiple_files=True, key="floating_uploader", label_visibility="collapsed")

# CSS：把 file_uploader 定位到右下，显示圆形图标（📎），并让 input[type=file] 覆盖图标以接收点击
st.markdown(
    """
    <style>
    /* 定位 file_uploader 容器（靠近 chat_input 的位置） */
    div[data-testid="stFileUploader"] {
        position: fixed;
        right: 160px;   /* 根据需要调整水平位置 */
        bottom: 92px;   /* 根据需要调整垂直位置（使图标靠近发送按钮） */
        z-index: 9999;
        width: 48px;
        height: 48px;
        padding: 0;
        overflow: visible;
    }

    /* 隐藏默认文本/label */
    div[data-testid="stFileUploader"] > label { display: none !important; }

    /* 隐藏默认 drop 区视觉元素，但保留 input 元素以接收文件 */
    div[data-testid="stFileUploader"] > div {
        padding: 0 !important;
        margin: 0 !important;
        height: 0px !important;
        overflow: visible !important;
    }

    /* 绘制圆形图标（伪元素），作为可见的点击目标 */
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
        pointer-events: none; /* 让下面透明 input 捕获点击 */
    }

    /* 使真实的 input[type=file] 覆盖在图标上方以接收点击，且不可见 */
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

    /* 移除额外文本（不同 streamlit 版本可能生成不同层级，尽量隐藏） */
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

            # 保存 assistant 响应
            st.session_state["messages"].append({
                "role": "assistant",
                "content": full
            })
else:
    # 只有提示信息，没有第二个 chat_input（避免 DuplicateElementId）
    st.info("请在侧边栏输入 Gemini API Key 以开始聊天")        "Google Gemini API Key",
        type="password",
        value="AIzaSyD0HjQ57wfOtNxbbWqAlAIeRaQueZ9TjPk",
    )

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

# 初始化状态
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "pending_attachments" not in st.session_state:
    st.session_state["pending_attachments"] = []

# 显示历史消息
for i, msg in enumerate(st.session_state["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content", ""))
        attachments = msg.get("attachments", [])
        if attachments:
            st.markdown("**附件：**")
            for j, att in enumerate(attachments):
                name = att.get("name")
                data = att.get("data")
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
# 📎 浮动 ChatGPT 风格附件按钮
# ------------------------------
files = st.file_uploader("", accept_multiple_files=True, key="floating_upload", label_visibility="collapsed")

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
    }
    div[data-testid="stFileUploader"] > label { display: none !important; }
    div[data-testid="stFileUploader"] > div { height: 0px !important; overflow: visible !important; }
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
    </style>
    """,
    unsafe_allow_html=True,
)

# 保存附件
if files:
    for f in (files if isinstance(files, list) else [files]):
        data = f.read()
        st.session_state["pending_attachments"].append({
            "name": f.name,
            "data": data,
            "type": getattr(f, "type", None),
            "size": len(data)
        })
    st.success("附件已添加")

# 显示 pending
if st.session_state["pending_attachments"]:
    cols = st.columns([0.9, 0.1])
    cols[0].markdown("**待发送附件：** " + ", ".join(a["name"] for a in st.session_state["pending_attachments"]))
    if cols[1].button("✖ 清除附件"):
        st.session_state["pending_attachments"] = []

# ------------------------------
# 聊天（唯一的 chat_input）
# ------------------------------
if api_key:
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    user_input = st.chat_input("请输入你的问题...")
    if user_input:
        attachments_payload = []
        for att in st.session_state["pending_attachments"]:
            item = {"name": att["name"], "data": att["data"]}
            if send_file_contents:
                item["data_base64"] = base64.b64encode(att["data"]).decode("utf-8")
            attachments_payload.append(item)

        st.session_state["messages"].append({
            "role": "user",
            "content": user_input,
            "attachments": attachments_payload
        })
        with st.chat_message("user"):
            t = user_input
            if attachments_payload:
                t += "\n\n**附件:** " + ", ".join(a["name"] for a in attachments_payload)
            st.markdown(t)

        st.session_state["pending_attachments"] = []

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            try:
                response = model.generate_content(user_input, stream=True)
                for chunk in response:
                    if hasattr(chunk, "text") and chunk.text:
                        full += chunk.text
                        placeholder.markdown(full + "▌")
                placeholder.markdown(full)
            except:
                # fallback
                r = model.generate_content(user_input)
                full = r.text if hasattr(r, "text") else str(r)
                placeholder.markdown(full)

        st.session_state["messages"].append({
            "role": "assistant",
            "content": full
        })
else:
    st.warning("请先输入 API Key")
