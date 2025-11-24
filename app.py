import streamlit as st
import base64
from google.generativeai import GenerativeModel, configure

# ------------------------------
# 页面 & 侧边栏配置
# ------------------------------
st.set_page_config(page_title="Gemini AI 聊天", page_icon="🤖", layout="wide")

st.title("🤖 Gemini AI 聊天助手")
st.caption("基于 Google Gemini API 的简单聊天工具 — 保持 chat_input（置底 + 自动高度），右侧添加附件按钮")

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

    st.write("---")
    send_file_contents = st.checkbox("发送文件内容给 Gemini（将把文件 base64 编码随消息发送）", value=False)
    st.caption("关闭则仅保存文件名作为元数据；开启将把小文件内容随消息发送（注意隐私与大小）")

    if st.button("🗑️ 清空聊天记录"):
        st.session_state.pop("messages", None)
        st.session_state.pop("pending_attachments", None)
        st.experimental_rerun()

# ------------------------------
# 初始化会话状态
# ------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# pending_attachments 存储为 list of dict: {"name": ..., "data": bytes, "type": mime}
if "pending_attachments" not in st.session_state:
    st.session_state["pending_attachments"] = []

# ------------------------------
# 显示历史聊天记录
# ------------------------------
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        content = msg.get("content", "")
        # 如果有附件元数据，显示文件名并提供下载按钮
        attachments = msg.get("attachments", [])
        if attachments:
            # 显示正文 + 附件清单
            st.markdown(content)
            st.markdown("**附件：**")
            for idx, att in enumerate(attachments):
                att_name = att.get("name")
                att_bytes = att.get("data")  # bytes or None
                if att_bytes:
                    st.download_button(
                        label=f"下载 {att_name}",
                        data=att_bytes,
                        file_name=att_name,
                        key=f"dl_{msg['role']}_{idx}_{att_name}"
                    )
                else:
                    st.markdown(f"- {att_name}")
        else:
            st.markdown(content)

st.markdown("---")

# ------------------------------
# 浮动附件上传按钮（定位到聊天输入框附近）
# ------------------------------
# 我们用一个可见但小的 file_uploader，然后用 CSS 定位它到右下（靠近 chat_input）。
# (注意：不同 Streamlit 版本 的 DOM 细节会有差异，必要时调整 right/bottom 值)
file_uploader = st.file_uploader(
    label="",
    accept_multiple_files=True,
    key="floating_uploader",
    label_visibility="collapsed"
)

st.markdown(
    """
    <style>
    /* 将 file_uploader 固定到右下靠近 chat_input 的位置，调整 right/bottom 以适配你的主题 */
    div[data-testid="stFileUploader"] {
        position: fixed;
        right: 160px;   /* 根据你的页面调整，让它紧贴发送按钮 */
        bottom: 92px;   /* 大致值：使按钮在 chat_input 的左侧/上方 */
        z-index: 9999;
        width: 44px;    /* 控制可视大小 */
        height: 44px;
        overflow: visible;
    }
    /* 隐藏文件上传默认文字（保持图标或小输入）*/
    div[data-testid="stFileUploader"] > label {
        display: none;
    }
    /* 调整文件选择按钮的实际样式（可能需要根据 streamlit 版本微调） */
    div[data-testid="stFileUploader"] > div {
        padding: 0;
        margin: 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 当用户在 file_uploader 选择了文件，我们把文件保存在 session_state.pending_attachments（bytes），但不自动发送
if file_uploader:
    # file_uploader 可能是列表（accept_multiple_files=True）
    files = file_uploader if isinstance(file_uploader, list) else [file_uploader]
    new_added = []
    for f in files:
        # avoid duplicate if same file object already stored (by name+size)
        try:
            f_bytes = f.read()
        except Exception:
            f_bytes = None
        fingerprint = (f.name, len(f_bytes) if f_bytes is not None else -1)
        existed = False
        for existing in st.session_state["pending_attachments"]:
            if (existing.get("name"), existing.get("size")) == fingerprint:
                existed = True
                break
        if not existed:
            st.session_state["pending_attachments"].append({
                "name": f.name,
                "data": f_bytes,
                "size": len(f_bytes) if f_bytes is not None else None,
                "type": getattr(f, "type", None)
            })
            new_added.append(f.name)
    if new_added:
        st.toast_text = f"已添加附件: {', '.join(new_added)}"  # 仅作反馈（非标准 API；若无效可删除）

# 显示当前待发送附件（并提供清除按钮）
if st.session_state["pending_attachments"]:
    cols = st.columns([0.9, 0.1])
    pending_names = ", ".join([p["name"] for p in st.session_state["pending_attachments"]])
    cols[0].markdown(f"**待发送附件：** {pending_names}")
    if cols[1].button("✖ 清除附件"):
        st.session_state["pending_attachments"] = []

# ------------------------------
# 聊天输入（保持 chat_input 固有特性）
# ------------------------------
if api_key:
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    # 当用户提交输入（chat_input 会固定在页面底部并自动调整高度）
    user_input = st.chat_input("请输入你的问题...")
    if user_input:
        # 构造附件元数据（默认只发送名字；如侧边栏勾选则同时附带 base64 内容）
        attachments_payload = []
        for att in st.session_state.get("pending_attachments", []):
            payload_item = {"name": att["name"]}
            if send_file_contents and att.get("data") is not None:
                # base64 encode bytes to string
                b64 = base64.b64encode(att["data"]).decode("utf-8")
                payload_item["data_base64"] = b64
                payload_item["size"] = att.get("size")
                payload_item["type"] = att.get("type")
            attachments_payload.append(payload_item)

        # 把用户消息加入会话（包括附件元数据）
        st.session_state["messages"].append({
            "role": "user",
            "content": user_input,
            "attachments": attachments_payload
        })
        with st.chat_message("user"):
            display_text = user_input
            if attachments_payload:
                display_text += "\n\n**附件:** " + ", ".join([a["name"] for a in attachments_payload])
            st.markdown(display_text)

        # 清除 pending（已加入消息的附件从 pending 中移除）
        st.session_state["pending_attachments"] = []

        # ------------------------------
        # 调用 Gemini 生成回复（尝试流式，如果 SDK 不支持则回退）
        # ------------------------------
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            try:
                # 优先尝试流式接口（若你的 SDK 支持 stream=True）
                response = model.generate_content(user_input, stream=True)
                # 若返回可迭代流，则逐块拼接
                try:
                    for chunk in response:
                        # chunk 结构可能不同：尝试多种访问方式
                        text_piece = None
                        if hasattr(chunk, "text"):
                            text_piece = getattr(chunk, "text")
                        elif isinstance(chunk, dict):
                            text_piece = chunk.get("text") or chunk.get("output_text") or str(chunk)
                        else:
                            text_piece = str(chunk)
                        if text_piece:
                            full_response += text_piece
                            placeholder.markdown(full_response + "▌")
                    placeholder.markdown(full_response)
                except TypeError:
                    # response 不能被迭代，视为非流式结果
                    # 继续后面作为非流式处理
                    raise Exception("stream returned non-iterable")
            except Exception:
                # 回退到非流式调用（兼容旧 SDK）
                try:
                    response = model.generate_content(user_input)
                    # 尝试提取文本字段
                    text = None
                    if hasattr(response, "text"):
                        text = getattr(response, "text")
                    elif isinstance(response, dict):
                        # 常见结构尝试
                        text = response.get("text") or response.get("output_text")
                        # 有些返回在 candidates 列表中
                        if not text:
                            candidates = response.get("candidates") or response.get("outputs") or []
                            if candidates and isinstance(candidates, list):
                                first = candidates[0]
                                if isinstance(first, dict):
                                    # 可能在 content/text 字段
                                    text = first.get("content") or first.get("text") or first.get("output_text")
                                else:
                                    text = str(first)
                    # 最终回退：转为 str
                    if not text:
                        text = str(response)
                    full_response = text
                    placeholder.markdown(full_response)
                except Exception as e2:
                    # 报错时给出提示
                    st.error(f"调用 Gemini 出错：{e2}")
                    full_response = "[错误：无法获得模型响应]"

            # 保存 AI 响应
            st.session_state["messages"].append({
                "role": "assistant",
                "content": full_response
            })
else:
    st.chat_input("请先在侧边栏输入 Gemini API Key", disabled=True)
    st.warning("请在侧边栏配置你的 Google Gemini API Key 以开始聊天")
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
