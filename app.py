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

# 1. 配置 Gemini API Key（用户需在侧边栏输入）
with st.sidebar:
    st.header("🔧 配置")
    api_key = st.text_input("请输入你的 Google Gemini API Key", type="password")
    st.caption("API Key 可从 [Google AI Studio](https://aistudio.google.com/) 获取")

    # 模型选择下拉框（默认 gemini-2.5-pro）
    models = [
        "gemini-2.5-pro",
        "gemini-2.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro"
    ]
    selected_model = st.selectbox("选择模型", models, index=0)  # index=0 设为默认

    # 清空聊天记录按钮
    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()

# 2. 初始化聊天记录（用 Streamlit 会话状态存储，页面刷新不丢失）
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. 显示历史聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 4. 处理用户输入和 AI 响应
if api_key:
    # 配置 Gemini API
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    # 用户输入框
    user_input = st.chat_input("请输入你的问题...")
    if user_input:
        # 添加用户消息到会话状态
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # 生成 AI 响应
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            # 调用 Gemini API（流式响应，实时显示）
            try:
                response = model.generate_content(user_input, stream=True)
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")  # 加载动画
                message_placeholder.markdown(full_response)  # 最终响应
                # 保存 AI 响应到会话状态
                st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"API 调用失败：{str(e)}")
else:
    # 未输入 API Key 时提示
    st.chat_input("请先在侧边栏输入 Gemini API Key", disabled=True)
    st.warning("请在侧边栏配置你的 Google Gemini API Key 以开始聊天")
