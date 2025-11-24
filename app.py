import streamlit as st
from google.generativeai import GenerativeModel, configure

# 页面配置
st.set_page_config(
    page_title="Gemini AI 聊天",
    page_icon="🤖",
    layout="wide"
)

# 标题和说明
st.title("🤖 Gemini AI 聊天助手")
st.caption("基于 Google Gemini API 的简单聊天工具，支持多模型选择")

# 初始化附件存储
if "attachments" not in st.session_state:
    st.session_state.attachments = []

# 1. 配置 Gemini API Key（侧边栏输入）
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

# 2. 初始化聊天记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. 显示历史聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ======= 新增：发送按钮旁的“添加附件”按钮 =======
col1, col2 = st.columns([8, 1])

with col2:
    add_file_btn = st.button("📎")

if add_file_btn:
    uploaded = st.file_uploader("上传附件（不自动发送）", accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            st.session_state.attachments.append(f)
        st.success("附件已添加（不会自动发送）")

# 显示已添加的附件列表
if st.session_state.attachments:
    st.caption("📄 已添加附件：")
    for f in st.session_state.attachments:
        st.write("•", f.name)

# ==================================================

# 4. 用户输入 & AI 回复逻辑
if api_key:
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    user_input = col1.chat_input("请输入你的问题...")  # 使输入框与按钮同行

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                response = model.generate_content(user_input, stream=True)
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")

                message_placeholder.markdown(full_response)
                st.session_state.messages.append(
                    {"role": "assistant", "content": full_response}
                )
            except Exception as e:
                st.error(f"API 调用失败：{str(e)}")

else:
    col1.chat_input("请先在侧边栏输入 Gemini API Key", disabled=True)
    st.warning("请在侧边栏配置你的 Google Gemini API Key 以开始聊天")
