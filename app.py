import streamlit as st
from google.generativeai import GenerativeModel, configure
import PIL.Image  # 引入Pillow库用于处理图片
import io # 用于处理二进制数据

# 页面配置
st.set_page_config(
    page_title="Gemini AI 多模态聊天",
    page_icon="🤖",
    layout="wide"
)

# 标题和说明
st.title("🤖 Gemini AI 多模态聊天助手")
st.caption("基于 Google Gemini API，支持文本、图片和代码文件输入")

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("🔧 配置")
    # 1. 配置 Gemini API Key
    try:
        # 优先从 Streamlit secrets 获取 API Key
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("已成功加载 API Key！")
    except (KeyError, FileNotFoundError):
        st.warning("未找到 secrets.toml 中的 GEMINI_API_KEY，请手动输入。")
        api_key = st.text_input("请输入你的 Google Gemini API Key", type="password")

    st.caption("API Key 可从 [Google AI Studio](https://aistudio.google.com/) 获取")

    # 2. 模型选择
    models = [
        "gemini-1.5-pro-latest", # 强大的多模态模型
        "gemini-1.5-flash-latest", # 快速的多模态模型
        "gemini-pro-vision", # 专门的视觉模型
        "gemini-pro" # 纯文本模型
    ]
    # 过滤掉不含 'vision' 或 '1.5' 的模型，因为它们不支持多模态
    # selected_model = st.selectbox("选择模型", [m for m in models if 'vision' in m or '1.5' in m], index=0)
    selected_model = st.selectbox("选择模型", models, index=0)
    st.info("提示：请选择支持多模态输入的模型（如 gemini-1.5-pro, gemini-1.5-flash）以使用文件上传功能。")


    # 3. 清空聊天记录按钮
    if st.button("🗑️ 清空聊天记录"):
        st.session_state.messages = []
        st.session_state.uploaded_files_info = {} # 同时清空文件记录
        st.rerun()

# --- 主聊天界面 ---

# 初始化聊天记录 (更复杂的结构以支持多模态)
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # 根据消息内容类型来决定如何展示
        if isinstance(msg["content"], str):
            st.markdown(msg["content"])
        elif isinstance(msg["content"], list):
            for part in msg["content"]:
                if part["type"] == "text":
                    st.markdown(part["data"])
                elif part["type"] == "image":
                    st.image(part["data"], caption=part.get("caption", "上传的图片"), use_column_width=True)
                elif part["type"] == "file":
                    st.info(f"📄 已上传文件: `{part['name']}`")
                    # 可选：显示代码文件内容
                    # with st.expander(f"查看 `{part['name']}` 内容"):
                    #     st.code(part['data'], language=part['name'].split('.')[-1])


# 检查 API Key 是否配置
if api_key:
    # 配置 Gemini API
    try:
        configure(api_key=api_key)
        model = GenerativeModel(selected_model)
    except Exception as e:
        st.error(f"API Key 配置失败，请检查你的 Key 是否正确: {e}")
        st.stop() # 配置失败则停止运行

    # --- 文件上传和聊天输入框 ---
    # 使用 st.container 将上传和输入框包裹起来，样式更统一
    with st.container():
        # 1. 文件上传器
        uploaded_files = st.file_uploader(
            "✨ 上传附件（图片、代码等）",
            accept_multiple_files=True,
            type=['jpg', 'jpeg', 'png', 'gif', 'py', 'txt', 'md', 'json', 'html', 'css', 'js']
        )
        # 2. 用户输入框
        user_input = st.chat_input("请输入你的问题...")

    if user_input or uploaded_files:
        # --- 构造用户消息 ---
        user_message_content = []
        display_message_content = []

        # 处理上传的文件
        if uploaded_files:
            for uploaded_file in uploaded_files:
                # 读取文件字节
                bytes_data = uploaded_file.getvalue()
                # 判断文件类型
                if uploaded_file.type.startswith('image/'):
                    try:
                        img = PIL.Image.open(io.BytesIO(bytes_data))
                        # 添加到 API 请求列表
                        user_message_content.append(img)
                        # 添加到显示列表
                        display_message_content.append({
                            "type": "image",
                            "data": img,
                            "caption": uploaded_file.name
                        })
                    except Exception as e:
                        st.error(f"无法处理图片文件 {uploaded_file.name}: {e}")
                else: # 其他文件视为文本/代码
                    try:
                        file_content = bytes_data.decode('utf-8')
                        # 构造一个更清晰的上下文提示给模型
                        formatted_content = f"这是用户上传的文件 `{uploaded_file.name}` 的内容:\n\n```\n{file_content}\n```"
                        user_message_content.append(formatted_content)
                        # 添加到显示列表
                        display_message_content.append({
                            "type": "file",
                            "name": uploaded_file.name,
                            "data": file_content
                        })
                    except Exception as e:
                        st.error(f"无法读取文件 {uploaded_file.name}: {e}")

        # 处理文本输入
        if user_input:
            user_message_content.append(user_input)
            display_message_content.append({"type": "text", "data": user_input})

        # --- 显示并存储用户消息 ---
        if display_message_content:
            st.session_state.messages.append({"role": "user", "content": display_message_content})
            with st.chat_message("user"):
                for part in display_message_content:
                    if part["type"] == "text":
                        st.markdown(part["data"])
                    elif part["type"] == "image":
                        st.image(part["data"], caption=part.get("caption", "上传的图片"), width=200) # 预览图缩小
                    elif part["type"] == "file":
                        st.info(f"📄 已上传文件: `{part['name']}`")


        # --- 生成 AI 响应 ---
        if user_message_content:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                try:
                    # 调用 Gemini API (流式响应)
                    # 注意：generate_content 可以直接处理包含文本和图片对象的列表
                    response = model.generate_content(user_message_content, stream=True)
                    for chunk in response:
                        # 检查 chunk 是否有 text 属性，以及处理可能的安全设置导致的空响应
                        if hasattr(chunk, 'text') and chunk.text:
                            full_response += chunk.text
                            message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                    # 存储 AI 响应
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    # st.rerun() # 可以在接收到完整回复后刷新，但可能会导致输入框失去焦点，看个人喜好
                except Exception as e:
                    st.error(f"API 调用失败：{e}")
                    # 同样存储错误信息，方便调试
                    st.session_state.messages.append({"role": "assistant", "content": f"API 调用失败: {e}"})

else:
    # 未输入 API Key 时提示
    st.info("👈 请在左侧边栏配置你的 Google Gemini API Key 以开始聊天")
    st.chat_input("请先在侧边栏输入 Gemini API Key", disabled=True)if "messages" not in st.session_state:
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
    st.info("👈 请在左侧边栏配置你的 Google Gemini API Key 以开始聊天")
    st.chat_input("请先在侧边栏输入 Gemini API Key", disabled=True)
