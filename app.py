import streamlit as st
from google.generativeai import GenerativeModel, configure
import base64
import io
import os

# 页面配置
st.set_page_config(
    page_title="Gemini AI 聊天",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Gemini AI 聊天助手（含附件）")
st.caption("基于 Google Gemini API 的简单聊天工具，已添加附件上传与管理 UI。")

# 侧边栏：API Key & 模型
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

    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.session_state.attachments = []
        st.rerun()

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []
if "attachments" not in st.session_state:
    # 每个附件存为 dict: {name:, data: bytes, type: mime}
    st.session_state.attachments = []

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Helper: 将附件转换为发送给 Gemini 的结构（示例：base64 编码）
def prepare_attachments_for_gemini(attachments):
    """
    返回一个 attachments 的列表，每项包含 name/mime/base64_content。
    具体字段/结构请根据你所用 Gemini SDK 的要求调整。
    """
    out = []
    for a in attachments:
        b64 = base64.b64encode(a["data"]).decode("utf-8")
        out.append({
            "filename": a["name"],
            "mime": a.get("type", "application/octet-stream"),
            "base64": b64
        })
    return out

# Helper: 发送到 Gemini（占位实现 - 需根据 SDK/版本调整）
def send_to_gemini(model_obj, text, prepared_attachments):
    """
    示例实现：把 text 和 prepared_attachments 打包成一个 dict 发送。
    重要：不同的 SDK/版本参数名不同 —— 请替换这里的实现为你 SDK 的多模态调用方式。
    例如：
      - 有的 SDK 接受 files 参数（requests 风格）
      - 有的需要把附件上传到公开 URL 并在消息里引用 URL
      - 有的接受 base64 编码的 attachments 字段

    本函数尝试多种方式去兼容返回值，但你应该根据实际 SDK 调整请求/解析逻辑。
    """
    # 示例：把所有内容放入一个 input dict（仅作示范）
    payload = {
        "text": text,
        "attachments": prepared_attachments
    }

    # 尝试简单调用（注意：真实 SDK 可能不是这样）
    try:
        resp = model_obj.generate_content(payload)  # <- 很可能需要改这里
    except TypeError:
        # 有些 SDK 的 generate_content 期望不同参数签名；再尝试传入 text 直接调用
        try:
            resp = model_obj.generate_content(text)
        except Exception as e:
            raise e

    # 解析返回（兼顾几种常见返回格式）
    try:
        # 如果返回的是 object 并且有 text 属性
        if hasattr(resp, "text"):
            return resp.text
        # 如果是可迭代流
        if hasattr(resp, "__iter__") and not isinstance(resp, (str, bytes, dict)):
            text_acc = ""
            for chunk in resp:
                if hasattr(chunk, "text"):
                    text_acc += chunk.text
                elif isinstance(chunk, dict) and "text" in chunk:
                    text_acc += chunk["text"]
            return text_acc
        # 如果返回 dict 风格
        if isinstance(resp, dict):
            # 常见字段尝试
            return resp.get("output", "") or resp.get("text", "") or str(resp)
        # fallback
        return str(resp)
    except Exception:
        return str(resp)

# 主输入区：把文本输入、文件上传、发送按钮放同一行（更像聊天平台）
with st.container():
    col_text, col_attach, col_send = st.columns([6, 2, 1])
    with col_text:
        user_input = st.text_input("输入消息...", key="user_input")
    with col_attach:
        uploaded = st.file_uploader(
            "添加附件",
            accept_multiple_files=True,
            type=[
                "png", "jpg", "jpeg", "gif",
                "mp3", "wav", "ogg",
                "mp4", "mov",
                "pdf", "txt", "csv", "docx", "pptx"
            ],
            key="file_uploader"
        )
        if uploaded:
            # uploaded 是 list of UploadedFile
            for f in uploaded:
                already = [a["name"] for a in st.session_state.attachments]
                if f.name not in already:
                    st.session_state.attachments.append({
                        "name": f.name,
                        "data": f.getvalue(),
                        "type": f.type
                    })
    with col_send:
        send_clicked = st.button("发送")

# 显示已选择附件并提供删除
if st.session_state.attachments:
    st.markdown("**已添加的附件：**")
    remove_indices = []
    for i, a in enumerate(st.session_state.attachments):
        cols = st.columns([8, 1])
        with cols[0]:
            st.write(f"- {a['name']} ({a.get('type','')}, {len(a['data'])} bytes)")
            # 预览图片 / 音频 / 视频 / pdf 简单支持
            mime = a.get("type", "")
            if mime.startswith("image/"):
                st.image(a["data"], width=200)
            elif mime.startswith("audio/"):
                st.audio(a["data"])
            elif mime.startswith("video/"):
                st.video(a["data"])
            elif a["name"].lower().endswith(".pdf"):
                st.write("（PDF 文件，无法在此页面完整预览）")
        with cols[1]:
            if st.button("删除", key=f"del_{i}"):
                remove_indices.append(i)
    # 批量删除（从后往前）
    for idx in sorted(remove_indices, reverse=True):
        st.session_state.attachments.pop(idx)

# 当点击发送时：处理并发送
if send_clicked:
    if not api_key:
        st.error("请在侧边栏输入 Gemini API Key 后再发送。")
    elif not user_input and not st.session_state.attachments:
        st.warning("请输入消息或添加附件后再发送。")
    else:
        # 保存用户消息（在 UI 中显示）
        attach_names = [a["name"] for a in st.session_state.attachments]
        user_display = user_input
        if attach_names:
            user_display += "\n\n**附件**: " + ", ".join(attach_names)
        st.session_state.messages.append({"role": "user", "content": user_display})
        with st.chat_message("user"):
            st.markdown(user_display)

        # 配置 Gemini（如果 api_key 存在）
        try:
            configure(api_key=api_key)
            model = GenerativeModel(selected_model)
        except Exception as e:
            st.error(f"无法初始化 Gemini 客户端：{e}")
            model = None

        # 准备附件/调用 API
        if model:
            prepared = prepare_attachments_for_gemini(st.session_state.attachments)
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                try:
                    # 注意：这里的 send_to_gemini 为示例 wrapper，替换成你 SDK 的多模态调用
                    ai_response_text = send_to_gemini(model, user_input, prepared)
                    message_placeholder.markdown(ai_response_text)
                    # 保存 AI 响应
                    st.session_state.messages.append({"role": "assistant", "content": ai_response_text})
                except Exception as e:
                    st.error(f"API 调用失败：{e}")

        # 发送后按需清空输入与附件（这里选择清空）
        st.session_state.attachments = []
        st.session_state.user_input = ""
        # 强制页面刷新以显示新消息
        st.experimental_rerun()

# 当没有 API Key 时提示
if not api_key:
    st.chat_input("请先在侧边栏输入 Gemini API Key", disabled=True)
    st.warning("请在侧边栏配置你的 Google Gemini API Key 以开始聊天")
# ------------------------
# 初始化 SessionState
# ------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_files" not in st.session_state:
    st.session_state.pending_files = []   # 本次准备发送的附件


# ------------------------
# 显示聊天记录
# ------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # 显示附件预览
        if "files" in msg:
            for f in msg["files"]:
                st.caption(f"📎 附件：{f['name']}")
                if f["mime"].startswith("image"):
                    st.image(f["data"], caption=f["name"])
                else:
                    st.download_button(
                        label=f"⬇️ 下载 {f['name']}",
                        data=f["data"],
                        file_name=f["name"]
                    )


# ------------------------
# 附件上传按钮（显示在输入框旁边）
# ------------------------
col1, col2 = st.columns([8, 2])

with col2:
    uploaded_files = st.file_uploader(
        "添加附件",
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

if uploaded_files:
    for f in uploaded_files:
        st.session_state.pending_files.append(f)
    st.success(f"已添加 {len(uploaded_files)} 个文件")


# 显示当前待发送的附件
if st.session_state.pending_files:
    st.info("📎 待发送附件： " + ", ".join([f.name for f in st.session_state.pending_files]))


# ------------------------
# 聊天逻辑
# ------------------------
if api_key:
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    with col1:
        user_input = st.chat_input("输入消息...")

    if user_input or st.session_state.pending_files:
        # ---- 处理用户消息展示 ----
        user_message = {"role": "user", "content": user_input or "(发送了附件)"}

        # 如果有附件，把附件加入消息
        if st.session_state.pending_files:
            file_list = []
            for f in st.session_state.pending_files:
                file_list.append({
                    "name": f.name,
                    "mime": f.type,
                    "data": f.read()
                })
            user_message["files"] = file_list

        st.session_state.messages.append(user_message)

        # 显示到界面
        with st.chat_message("user"):
            st.markdown(user_message["content"])
            if "files" in user_message:
                for f in user_message["files"]:
                    st.caption(f"📎 附件：{f['name']}")
                    if f["mime"].startswith("image"):
                        st.image(f["data"])
                    else:
                        st.download_button(
                            label=f"⬇️ 下载 {f['name']}",
                            data=f["data"],
                            file_name=f["name"]
                        )

        # ---- 调用 Gemini，构造 content parts ----
        parts = []
        if user_input:
            parts.append(user_input)

        # 附件加入 parts
        if st.session_state.pending_files:
            for f in st.session_state.pending_files:
                parts.append({
                    "mime_type": f.type,
                    "data": f.getvalue()
                })

        # 清空待发送附件
        st.session_state.pending_files = []

        # ---- 调用 API ----
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_text = ""

            try:
                response = model.generate_content(parts, stream=True)
                for chunk in response:
                    if chunk.text:
                        full_text += chunk.text
                        placeholder.markdown(full_text + "▌")
                placeholder.markdown(full_text)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_text
                })

            except Exception as e:
                st.error(f"API 调用失败：{e}")

else:
    st.chat_input("请先配置 API Key", disabled=True)
    st.warning("请在左侧输入 Google Gemini API Key。")
