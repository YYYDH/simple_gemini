import streamlit as st
from google import genai
from PIL import Image
import io

# ----------------- 页面设置 -----------------
st.set_page_config(page_title="Gemini 多模态聊天", page_icon="🤖", layout="wide")
st.title("🤖 Gemini 多模态聊天助手")
st.caption("支持文本 + 图片 + 文件（google-genai 最新 SDK）")

# ----------------- 侧边栏 -----------------
with st.sidebar:
    st.header("🔧 配置")

    api_key = st.text_input("请输入 Gemini API Key", type="password")

    models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-pro"
    ]
    selected_model = st.selectbox("选择模型", models, index=0)

    if st.button("🗑 清空对话"):
        st.session_state.messages = []
        st.rerun()

# ----------------- 初始化会话状态 -----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ----------------- 展示历史消息 -----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        content = msg["content"]
        if isinstance(content, str):
            st.markdown(content)
        else:
            for part in content:
                if part["type"] == "text":
                    st.markdown(part["data"])
                elif part["type"] == "image":
                    st.image(part["data"], caption=part.get("caption"))
                elif part["type"] == "file":
                    st.info(f"📄 文件: {part['name']}")

# ----------------- 无 API Key 时停止 -----------------
if not api_key:
    st.info("👈 请在左侧输入 API Key")
    st.chat_input("请先输入 API Key", disabled=True)
    st.stop()

# ----------------- 创建 Gemini 客户端 -----------------
client = genai.Client(api_key=api_key)

# ----------------- 上传文件 + 输入框 -----------------
uploaded_files = st.file_uploader(
    "✨ 上传附件（不会自动发送）",
    accept_multiple_files=True,
    type=[
        "jpg", "jpeg", "png", "gif",
        "txt", "md", "json", "py"
    ]
)

user_input = st.chat_input("请输入你的消息...")

# ----------------- 处理用户输入 -----------------
if user_input or uploaded_files:

    display_content = []
    api_payload = []

    # ------ 文件处理 ------
    if uploaded_files:
        for f in uploaded_files:
            data = f.getvalue()

            if f.type.startswith("image"):
                img = Image.open(io.BytesIO(data))
                display_content.append({"type": "image", "data": img, "caption": f.name})
                api_payload.append(img)
            else:
                text = data.decode("utf-8", errors="ignore")
                display_content.append({"type": "file", "name": f.name, "data": text})
                api_payload.append(f"文件 `{f.name}` 内容：\n\n{text}")

    # ------ 文本处理 ------
    if user_input:
        display_content.append({"type": "text", "data": user_input})
        api_payload.append(user_input)

    # 保存用户消息
    st.session_state.messages.append({
        "role": "user",
        "content": display_content
    })

    # 展示用户消息
    with st.chat_message("user"):
        for part in display_content:
            if part["type"] == "text":
                st.markdown(part["data"])
            elif part["type"] == "image":
                st.image(part["data"], width=200)
            elif part["type"] == "file":
                st.info(f"📄 文件: {part['name']}")

    # ----------------- AI 回复 -----------------
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_text = ""

        try:
            # 正确的流式 API（适配 google-genai）
            stream = client.models.generate_content_stream(
                model=selected_model,
                contents=api_payload,
            )

            for chunk in stream:
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
