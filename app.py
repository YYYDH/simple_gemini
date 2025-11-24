import streamlit as st
import base64
from google.generativeai import GenerativeModel, configure

# ------------------------------
# 🔐 页面密码保护
# ------------------------------
PAGE_PASSWORD = "112234ydh"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔐 请输入访问密码")
    pwd = st.text_input("密码", type="password")

    if pwd == PAGE_PASSWORD:
        st.session_state["authenticated"] = True
        st.rerun()
    else:
        if pwd != "":
            st.error("密码错误，请重试")
    st.stop()  # 终止后续代码执行

# ------------------------------
# 页面 & 侧边栏
# ------------------------------
st.set_page_config(page_title="Gemini AI 聊天", page_icon="🤖", layout="wide")
st.title("🤖 Gemini AI 聊天助手")
st.caption("保留 chat_input（置底 + 自动高度），右下角浮动 📎 附件按钮 — 上传不自动发送")

with st.sidebar:
    st.header("🔧 配置")

    # ⭐ 默认 API KEY （可覆盖）
    api_key = st.text_input(
        "Google Gemini API Key",
        type="password",
        value="AIzaSyD0HjQ57wfOtNxbbWqAlAIeRaQueZ9TjPk",
    )

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
    send_file_contents = st.checkbox(
        "发送文件内容给 Gemini（将把小文件 base64 编码随消息发送）",
        value=False
    )
    st.caption("关闭则仅保存文件名作为元数据；开启会把文件 base64 一并发送（注意隐私与大小）")

    if st.button("🗑️ 清空聊天记录"):
        st.session_state.pop("messages", None)
        st.session_state.pop("pending_attachments", None)
        st.experimental_rerun()

# 初始化状态
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "pending_attachments" not in st.session_state:
    st.session_state["pending_attachments"] = []

# 显示历史消息
for i, msg in enumerate(st.session_state["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content", ""))
        attachments = msg.get("attachments", [])
        if attachments:
            st.markdown("**附件：**")
            for j, att in enumerate(attachments):
                name = att.get("name")
                data = att.get("data")
                if data:
                    st.download_button(
                        label=f"下载 {name}",
                        data=data,
                        file_name=name,
                        key=f"dl_{i}_{j}_{name}"
                    )
                else:
                    st.markdown(f"- {name}")

st.markdown("---")

# ------------------------------
# 📎 浮动 ChatGPT 风格附件按钮
# ------------------------------
files = st.file_uploader("", accept_multiple_files=True, key="floating_upload", label_visibility="collapsed")

st.markdown(
    """
    <style>
    div[data-testid="stFileUploader"] {
        position: fixed;
        right: 160px;
        bottom: 92px;
        z-index: 9999;
        width: 48px;
        height: 48px;
        padding: 0;
    }
    div[data-testid="stFileUploader"] > label { display: none !important; }
    div[data-testid="stFileUploader"] > div { height: 0px !important; overflow: visible !important; }
    div[data-testid="stFileUploader"]::before {
        content: "📎";
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: #ffffff;
        box-shadow: 0 6px 18px rgba(0,0,0,0.12);
        font-size: 22px;
        position: absolute;
        right: 0;
        bottom: 0;
        pointer-events: none;
    }
    div[data-testid="stFileUploader"] input[type="file"] {
        opacity: 0;
        width: 48px;
        height: 48px;
        position: absolute;
        right: 0;
        bottom: 0;
        z-index: 1000;
        cursor: pointer;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 保存附件
if files:
    for f in (files if isinstance(files, list) else [files]):
        data = f.read()
        st.session_state["pending_attachments"].append({
            "name": f.name,
            "data": data,
            "type": getattr(f, "type", None),
            "size": len(data)
        })
    st.success("附件已添加")

# 显示 pending
if st.session_state["pending_attachments"]:
    cols = st.columns([0.9, 0.1])
    cols[0].markdown("**待发送附件：** " + ", ".join(a["name"] for a in st.session_state["pending_attachments"]))
    if cols[1].button("✖ 清除附件"):
        st.session_state["pending_attachments"] = []

# ------------------------------
# 聊天（唯一的 chat_input）
# ------------------------------
if api_key:
    configure(api_key=api_key)
    model = GenerativeModel(selected_model)

    user_input = st.chat_input("请输入你的问题...")
    if user_input:
        attachments_payload = []
        for att in st.session_state["pending_attachments"]:
            item = {"name": att["name"], "data": att["data"]}
            if send_file_contents:
                item["data_base64"] = base64.b64encode(att["data"]).decode("utf-8")
            attachments_payload.append(item)

        st.session_state["messages"].append({
            "role": "user",
            "content": user_input,
            "attachments": attachments_payload
        })
        with st.chat_message("user"):
            t = user_input
            if attachments_payload:
                t += "\n\n**附件:** " + ", ".join(a["name"] for a in attachments_payload)
            st.markdown(t)

        st.session_state["pending_attachments"] = []

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            try:
                response = model.generate_content(user_input, stream=True)
                for chunk in response:
                    if hasattr(chunk, "text") and chunk.text:
                        full += chunk.text
                        placeholder.markdown(full + "▌")
                placeholder.markdown(full)
            except:
                # fallback
                r = model.generate_content(user_input)
                full = r.text if hasattr(r, "text") else str(r)
                placeholder.markdown(full)

        st.session_state["messages"].append({
            "role": "assistant",
            "content": full
        })
else:
    st.warning("请先输入 API Key")
