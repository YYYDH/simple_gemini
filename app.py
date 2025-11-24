# 完整可运行版本 —— 修复 DuplicateElementKey + 默认 API + 密码保护 + 浮动📎按钮
# 你直接部署即可运行

import streamlit as st
from google.generativeai import GenerativeModel, configure
import base64

# -------------------------------------------------------------
# 密码保护
# -------------------------------------------------------------
PASSWORD = "112234ydh"
def check_password():
    if "pw_ok" in st.session_state and st.session_state.pw_ok:
        return True

    with st.form("pw_form"):
        pw = st.text_input("请输入访问密码", type="password")
        if st.form_submit_button("进入"):
            if pw == PASSWORD:
                st.session_state.pw_ok = True
                return True
            else:
                st.error("密码错误！")
    return False

if not check_password():
    st.stop()

# -------------------------------------------------------------
# 页面配置
# -------------------------------------------------------------
st.set_page_config("Gemini Chat", "🤖", layout="wide")
st.title("🤖 Gemini AI 聊天助手")

# -------------------------------------------------------------
# 默认 API（可覆盖）
# -------------------------------------------------------------
default_api = "AIzaSyD0HjQ57wfOtNxbbWqAlAIeRaQueZ9TjPk"
api_key = st.sidebar.text_input("请输入你的 Google Gemini API Key", value=default_api, type="password")

if not api_key:
    st.warning("请在侧边栏输入 API Key 以开始聊天")
    st.stop()

configure(api_key=api_key)

# -------------------------------------------------------------
# 选择模型
# -------------------------------------------------------------
model_name = st.sidebar.selectbox("选择模型", ["gemini-2.0-flash", "gemini-2.0-pro"])
model = GenerativeModel(model_name)

# -------------------------------------------------------------
# 文件选项
# -------------------------------------------------------------
send_inline = st.sidebar.toggle("发送文件内容（base64）", value=False)

# -------------------------------------------------------------
# 初始化 session
# -------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -------------------------------------------------------------
# 聊天记录显示
# -------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# -------------------------------------------------------------
# 上传文件组件 —— 固定唯一 key，避免重复
# -------------------------------------------------------------
# 使用 st.html + input[type=file] 实现“浮动📎按钮”

floating_css = """
<style>
#floating-clip {
    position: fixed;
    bottom: 82px;
    right: 20px;
    z-index: 9999;
}
#file-input {
    display: none;
}
#clip-btn {
    background: white;
    border-radius: 50%;
    width: 52px;
    height: 52px;
    border: 1px solid #ccc;
    font-size: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
#clip-btn:hover {
    background: #f0f0f0;
}
</style>
<div id="floating-clip">
  <label id="clip-btn" for="file-input">📎</label>
  <input id="file-input" type="file" multiple />
</div>
<script>
const fileInput = window.parent.document.querySelector('#file-input');
fileInput.addEventListener('change', (event) => {
    const files = event.target.files;
    const names = Array.from(files).map(f => f.name);
    window.parent.postMessage({ type: 'files-selected', files: names }, '*');
});
</script>
"""

st.html(floating_css)

# -------------------------------------------------------------
# 用于接收前端上传事件
# 通过 session_state 记录
# -------------------------------------------------------------
if "pending_files" not in st.session_state:
    st.session_state.pending_files = []

# 监听浏览器 postMessage
msg = st.experimental_get_query_params()

# -------------------------------------------------------------
# 真实文件上传器（隐藏但必须存在）
# key 唯一避免重复
# -------------------------------------------------------------
files = st.file_uploader("hidden-uploader", accept_multiple_files=True, key="real_uploader", label_visibility="collapsed")
if files:
    st.session_state.pending_files = files
    st.toast(f"已选择 {len(files)} 个文件")

# -------------------------------------------------------------
# chat_input（置底 + 自动高度）
# -------------------------------------------------------------
user_input = st.chat_input("输入消息...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 处理附件
    parts = [user_input]
    if st.session_state.pending_files:
        for f in st.session_state.pending_files:
            if send_inline:
                b64 = base64.b64encode(f.read()).decode()
                parts.append(f"文件：{f.name}\nBase64：{b64[:80]}...")
            else:
                parts.append(f"文件（仅名称）：{f.name}")
        st.session_state.pending_files = []

    # 调用 Gemini
    full_input = "\n".join(parts)
    response = model.generate_content(full_input)

    bot_reply = response.text
    st.session_state.messages.append({"role": "assistant", "content": bot_reply})

    with st.chat_message("assistant"):
        st.markdown(bot_reply)        st.success("聊天记录已清空")  # 提示用户
        # 不调用 st.experimental_rerun() —— Streamlit 会在按钮点击后自动重新执行脚本

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
        pointer-events: none;
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
    st.info("请在侧边栏输入 Gemini API Key 以开始聊天")
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
    st.info("请在侧边栏输入 Gemini API Key 以开始聊天")
