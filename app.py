import streamlit as st
from google.generativeai import GenerativeModel, configure
import google.generativeai as genai

# 页面配置
st.set_page_config(
    page_title="Gemini AI 聊天",
    page_icon="🤖",
    layout="wide"
)

# 标题
st.title("🤖 Gemini AI 聊天助手（支持附件）")
st.caption("支持文本 + 多种文件类型（图片、PDF、文档、音频、视频等）")


# ------------------------
# 侧边栏配置
# ------------------------
with st.sidebar:
    st.header("🔧 配置")
    api_key = st.text_input("Google Gemini API Key", type="password")

    models = [
        "gemini-2.5-pro",
        "gemini-2.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro"
    ]
    selected_model = st.selectbox("选择模型", models)

    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()


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
