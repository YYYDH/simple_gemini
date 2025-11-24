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
        # 也清除待发送附件
        st.session_state.pop("pending_attachments", None)
        st.rerun()

# 2. 初始化聊天记录（用 Streamlit 会话状态存储，页面刷新不丢失）
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. 显示历史聊天记录
for msg in st.session_state.messages:
    # 支持若消息带 attachments 字段则显示文件名
    with st.chat_message(msg["role"]):
        body = msg["content"]
        if msg.get("attachments"):
            body += "\n\n**附件:** " + ", ".join(msg["attachments"])
        st.markdown(body)

# 4. 处理用户输入和 AI 响应
if api_key:
    # 配置 Gemini API
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    # 使用 form 把输入、添加附件按钮和发送按钮放在同一行（尽量模拟“发送旁边有添加附件按钮”的布局）
    with st.form("chat_form", clear_on_submit=False):
        col_text, col_attach, col_send = st.columns([8, 1, 1])
        user_text = col_text.text_input("请输入你的问题...", key="user_input", value="")
        # 这里作为“添加附件”按钮：accept_multiple_files=True，让用户可以一次选多个文件。
        # 不指定 type 参数即接受任意文件类型（图片/音频/视频/文本等）。
        files = col_attach.file_uploader("", accept_multiple_files=True, key="file_uploader", label_visibility="collapsed")
        send = col_send.form_submit_button("发送")

    # 当用户通过 file_uploader 选择文件时，把文件对象存入 session_state，但不要自动发送
    if files:
        # 保留已选附件（UploadedFile 对象列表）
        st.session_state["pending_attachments"] = files

    # 显示当前待发送的附件（如果有）
    if st.session_state.get("pending_attachments"):
        pending = st.session_state["pending_attachments"]
        # 显示文件名和一个清除按钮
        cols = st.columns([0.95, 0.05])
        cols[0].markdown("已选附件: " + ", ".join([f.name for f in pending]))
        if cols[1].button("✖ 清除附件"):
            st.session_state.pop("pending_attachments", None)

    # 当用户点击发送按钮（或表单提交）时，把文本和附件元数据一起加入 messages 并调用模型生成回复
    if send and (user_text or st.session_state.get("pending_attachments")):
        attachments = st.session_state.pop("pending_attachments", [])
        # 保存用户消息（这里把文件名作为附件元数据存储；如果需要把文件二进制发给 Gemini，需要在这里处理）
        st.session_state.messages.append({
            "role": "user",
            "content": user_text,
            "attachments": [f.name for f in attachments] if attachments else []
        })
        with st.chat_message("user"):
            display_text = user_text
            if attachments:
                display_text += "\n\n**附件:** " + ", ".join([f.name for f in attachments])
            st.markdown(display_text)

        # 生成 AI 响应
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            # 调用 Gemini API（流式响应，实时显示）
            try:
                # 注意：若 model.generate_content 的参数接口和你本地 SDK 不同（例如不支持 stream），
                # 需要按你的 SDK 文档调整调用方式。这里保留原来的流式调用示例。
                response = model.generate_content(user_text, stream=True)
                for chunk in response:
                    if getattr(chunk, "text", None):
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
