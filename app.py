with st.sidebar:
    st.header("🔧 配置")

    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("已成功加载 API Key！")
    except Exception:
        st.warning("未找到 GEMINI_API_KEY，请手动输入。")
        api_key = st.text_input("请输入你的 Google Gemini API Key", type="password")

    st.caption("API Key 可从 Google AI Studio 获取")

    models = [
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash-latest",
        "gemini-pro-vision",
        "gemini-pro"
    ]

    selected_model = st.selectbox("选择模型", models, index=0)

    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()

# ---------------- 初始化聊天记录 ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- 显示历史消息 ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], str):
            st.markdown(msg["content"])
        else:
            for part in msg["content"]:
                if part["type"] == "text":
                    st.markdown(part["data"])
                elif part["type"] == "image":
                    st.image(part["data"], caption=part.get("caption", "上传的图片"), use_column_width=True)
                elif part["type"] == "file":
                    st.info(f"📄 上传文件 `{part['name']}`")

# ---------------- API 配置 ----------------
model = None
if api_key:
    try:
        configure(api_key=api_key)
        model = GenerativeModel(selected_model)
    except Exception as e:
        st.error(f"API Key 配置失败：{e}")
        model = None

# ---------------- 文件上传（独立于 chat_input） ----------------
uploaded_files = st.file_uploader(
    "✨ 上传附件（图片、文本、代码文件等）",
    accept_multiple_files=True,
    type=['jpg', 'jpeg', 'png', 'gif', 'py', 'txt', 'md', 'json', 'html', 'css', 'js']
)

# ---------------- 输入框放在页面最底部 ----------------
user_input = st.chat_input(
    "请输入你的问题..." if api_key else "请先在左侧输入 API Key",
    disabled=not api_key
)

# 若没 API Key，停止逻辑 —— 输入框仍正常显示在底部
if not api_key:
    st.stop()

# ------------------------------------------------------
# 下面是处理对话逻辑（仅当 API Key 存在时运行）
# ------------------------------------------------------

if user_input or uploaded_files:

    user_msg_for_api = []
    user_msg_display = []

    # 处理文件
    if uploaded_files:
        for file in uploaded_files:
            file_bytes = file.getvalue()

            if file.type.startswith("image/"):
                img = PIL.Image.open(io.BytesIO(file_bytes))
                user_msg_for_api.append(img)
                user_msg_display.append({
                    "type": "image",
                    "data": img,
                    "c    selected_model = st.selectbox("选择模型", models, index=0)

    # 3. 清空聊天记录
    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.rerun()

# ---------------- 初始化聊天记录 ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- 显示历史消息 ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], str):
            st.markdown(msg["content"])
        else:
            for part in msg["content"]:
                if part["type"] == "text":
                    st.markdown(part["data"])
                elif part["type"] == "image":
                    st.image(part["data"], caption=part.get("caption", "上传的图片"), use_column_width=True)
                elif part["type"] == "file":
                    st.info(f"📄 上传文件: `{part['name']}`")

# ---------------- 检查 API Key ----------------
if not api_key:
    st.info("👈 请在左侧边栏输入 API Key 以开始聊天")
    st.chat_input("请先输入 API Key", disabled=True)
    st.stop()

# ---------------- API 配置 ----------------
try:
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)
except Exception as e:
    st.error(f"API Key 配置失败：{e}")
    st.stop()

# ---------------- 输入区域 ----------------
with st.container():
    uploaded_files = st.file_uploader(
        "✨ 上传附件（图片、文本、代码文件等）",
        accept_multiple_files=True,
        type=['jpg', 'jpeg', 'png', 'gif', 'py', 'txt', 'md', 'json', 'html', 'css', 'js']
    )
    user_input = st.chat_input("请输入你的问题...")

# ---------------- 处理用户消息 ----------------
if user_input or uploaded_files:

    user_msg_for_api = []
    user_msg_display = []

    # 处理上传文件
    if uploaded_files:
        for file in uploaded_files:
            file_bytes = file.getvalue()

            if file.type.startswith("image/"):
                try:
                    img = PIL.Image.open(io.BytesIO(file_bytes))
                    user_msg_for_api.append(img)
                    user_msg_display.append({
                        "type": "image",
                        "data": img,
                        "caption": file.name
                    })
                except Exception as e:
                    st.error(f"无法处理图片 {file.name}: {e}")

            else:
                try:
                    text_content = file_bytes.decode("utf-8")
                    formatted_text = f"这是用户上传的文件 `{file.name}` 的内容:\n\n```\n{text_content}\n```"
                    user_msg_for_api.append(formatted_text)
                    user_msg_display.append({
                        "type": "file",
                        "name": file.name,
                        "data": text_content
                    })
                except Exception as e:
                    st.error(f"无法读取文件 {file.name}: {e}")

    # 输入文本
    if user_input:
        user_msg_for_api.append(user_input)
        user_msg_display.append({"type": "text", "data": user_input})

    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": user_msg_display})
    with st.chat_message("user"):
        for part in user_msg_display:
            if part["type"] == "text":
                st.markdown(part["data"])
            elif part["type"] == "image":
                st.image(part["data"], caption=part["caption"], width=200)
            elif part["type"] == "file":
                st.info(f"📄 上传文件: `{part['name']}`")

    # ---------------- 调用 Gemini ----------------
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_reply = ""

        try:
            response = model.generate_content(user_msg_for_api, stream=True)

            for chunk in response:
                if hasattr(chunk, "text") and chunk.text:
                    full_reply += chunk.text
                    placeholder.markdown(full_reply + "▌")

            placeholder.markdown(full_reply)

            st.session_state.messages.append({
                "role": "assistant",
                "content": full_reply
            })

        except Exception as e:
            st.error(f"API 调用失败：{e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"API 调用失败：{e}"
            })
