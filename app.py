import streamlit as st
from google import genai
import google.ai.generativelanguage as glm

# -------------------------------
# Streamlit 页面设置
# -------------------------------
st.set_page_config(
    page_title="Gemini AI Chat",
    page_icon="🤖",
    layout="wide"
)

# 初始化消息记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# -------------------------------
# 侧边栏配置
# -------------------------------
with st.sidebar:
    st.header("🔧 配置")

    # API Key 处理
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("已成功加载 API Key！")
    except Exception:
        st.warning("未找到 GEMINI_API_KEY，请手动输入。")
        api_key = st.text_input("请输入你的 Google Gemini API Key", type="password")

    st.caption("API Key 可从 Google AI Studio 获取")

    # 模型选择（包含 2.5）
    models = [
        "gemini-2.5-pro",
        "gemini-2.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-pro"
    ]

    selected_model = st.selectbox("选择模型", models, index=0)

    # 清空对话
    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()

# 无 API Key 时阻止继续
if not api_key:
    st.info("👈 请在左侧边栏输入 API Key 以开始聊天")
    st.stop()

# -------------------------------
# 初始化 Gemini 客户端
# -------------------------------
client = genai.Client(api_key=api_key)

# -------------------------------
# 主界面标题
# -------------------------------
st.title("🤖 Gemini AI 多模态聊天助手")
st.caption("支持文本、图片、代码文件输入")

# -------------------------------
# 展示历史消息
# -------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], str):
            st.markdown(msg["content"])
        elif isinstance(msg["content"], list):  # 文件 + 文本组合
            for x in msg["content"]:
                if x["type"] == "text":
                    st.markdown(x["text"])
                elif x["type"] == "image":
                    st.image(x["image"], caption="用户上传的图片")


# -------------------------------
# 底部输入框：全页面固定在底部
# -------------------------------
# 上传文件（不自动发送）
uploaded_files = st.file_uploader(
    "📎 上传图片或文件（不会自动发送）",
    type=["png", "jpg", "jpeg", "webp", "gif", "txt", "md", "py", "json"],
    accept_multiple_files=True
)

# 输入框（在页面最底部）
user_text = st.chat_input("请输入你的消息...")

# -------------------------------
# 用户按“发送”后触发
# -------------------------------
if user_text or uploaded_files:
    final_payload = []

    # 添加文本
    if user_text:
        final_payload.append({"type": "text", "text": user_text})

    # 添加图片或其他文件
    for f in uploaded_files or []:
        if f.type.startswith("image/"):
            final_payload.append({
                "type": "image",
                "image": f.read()
            })
        else:
            text = f"（文件：{f.name}）\n\n```\n{f.read().decode('utf-8')}\n```"
            final_payload.append({"type": "text", "text": text})

    # 记录到对话
    st.session_state.messages.append({"role": "user", "content": final_payload})

    # 显示用户消息
    with st.chat_message("user"):
        for item in final_payload:
            if item["type"] == "text":
                st.markdown(item["text"])
            elif item["type"] == "image":
                st.image(item["image"])

    # -------------------------------
    # 调用 Gemini 模型
    # -------------------------------
    with st.chat_message("assistant"):
        msg = client.models.generate_content(
            model=selected_model,
            contents=final_payload,
            generation_config=glm.GenerationConfig(temperature=0.7)
        )

        reply = msg.text
        st.markdown(reply)

        # 保存
        st.session_state.messages.append({
            "role": "assistant",
            "content": reply
        })
