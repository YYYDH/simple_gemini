import streamlit as st
from google.generativeai import GenerativeModel, configure
import PIL.Image
import io

# ---------------- 页面配置 ----------------
st.set_page_config(
    page_title="Gemini AI 多模态聊天",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Gemini AI 多模态聊天助手")
st.caption("基于 Google Gemini API，支持文本、图片和代码文件输入")

# ---------------- 侧边栏配置 ----------------
with st.sidebar:
    st.header("🔧 配置")

    # 加载 API Key（优先 secrets）
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("已成功加载 API Key！")
    except Exception:
        st.warning("未找到 GEMINI_API_KEY，请手动输入。")
        api_key = st.text_input("请输入你的 Google Gemini API Key", type="password")

    st.caption("API Key 可从 Google AI Studio 获取")

    # 可选模型
    models = [
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash-latest",
        "gemini-pro-vision",
        "gemini-pro"
    ]
    selected_model = st.selectbox("选择模型", models, index=0)

    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()


# ---------------- 初始化聊天记录 ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------- 显示聊天记录 ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], str):
            st.markdown(msg["content"])
        else:
            for part in msg["content"]:
                if part["type"] == "text":
                    st.markdown(part["data"])
                elif part["type"] == "image":
                    st.image(part["data"], caption=part.get("caption", "图片"), use_column_width=True)
                elif part["type"] == "file":
                    st.info(f"📄 文件：`{part['name']}`")


# ---------------- 若无 API Key，仅阻止逻辑，不阻止 chat_input ----------------
model = None
if api_key:
    try:
        configure(api_key=api_key)
        model = GenerativeModel(selected_model)
    except Exception as e:
        st.error(f"API Key 配置失败：{e}")
        model = None


# ---------------- 文件上传器（总是显示） ----------------
uploaded_files = st.file_uploader(
    "✨ 上传附件（图片、文本、代码文件等）",
    accept_multiple_files=True,
    type=['jpg', 'jpeg', 'png', 'gif', 'py', 'txt', 'md', 'json', 'html', 'css', 'js']
)


# ===================== 输入框永远固定在最底部 =====================
user_input = st.chat_input(
    "请输入你的问题..." if api_key else "请先在左侧输入 API Key",
    disabled=not api_key
)
# ================================================================


# 无 API Key：停止处理逻辑（但输入框仍在页面底部）
if not api_key:
    st.stop()


# ---------------- 处理消息 ----------------
if user_input or uploaded_files:

    to_model = []        # 发送给 Gemini 的消息
    to_display = []      # 用于界面显示

    # ---- 处理上传文件 ----
    if uploaded_files:
        for f in uploaded_files:
            data = f.getvalue()

            if f.type.startswith("image/"):   # 图片
                img = PIL.Image.open(io.BytesIO(data))
                to_model.append(img)
                to_display.append({
                    "type": "image",
                    "data": img,
                    "caption": f.name
                })
            else:  # 文本 / 代码文件
                text = data.decode("utf-8", errors="ignore")
                formatted = f"这是文件 `{f.name}` 的内容:\n\n```\n{text}\n```"
                to_model.append(formatted)
                to_display.append({
                    "type": "file",
                    "name": f.name,
                    "data": text
                })

    # ---- 处理文本消息 ----
    if user_input:
        to_model.append(user_input)
        to_display.append({"type": "text", "data": user_input})

    # ---- 显示用户消息 ----
    st.session_state.messages.append({"role": "user", "content": to_display})
    with st.chat_message("user"):
        for part in to_display:
            if part["type"] == "text":
                st.markdown(part["data"])
            elif part["type"] == "image":
                st.image(part["data"], caption=part["caption"], width=200)
            elif part["type"] == "file":
                st.info(f"📄 文件 `{part['name']}`")


    # ---------------- Gemini 回复 ----------------
    if model:
        with st.chat_message("assistant"):
            holder = st.empty()
            full = ""

            try:
                response = model.generate_content(to_model, stream=True)
                for chunk in response:
                    if hasattr(chunk, "text") and chunk.text:
                        full += chunk.text
                        holder.markdown(full + "▌")

                holder.markdown(full)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full
                })

            except Exception as e:
                err = f"API 调用失败：{e}"
                st.error(err)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": err
                })
