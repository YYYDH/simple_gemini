# 修复版：只使用一个 file_uploader（唯一 key），只使用一个 st.chat_input()
import streamlit as st
import base64
from google.generativeai import GenerativeModel, configure

# ------------------------------
# 密码保护（简单会话版）
# ------------------------------
PASSWORD = "112234ydh"
if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

if not st.session_state.auth_ok:
    st.title("🔐 请输入访问密码")
    pwd = st.text_input("密码", type="password")
    if st.button("进入"):
        if pwd == PASSWORD:
            st.session_state.auth_ok = True
            st.experimental_rerun()
        else:
            st.error("密码错误")
    st.stop()

# ------------------------------
# 页面 & 侧边栏
# ------------------------------
st.set_page_config(page_title="Gemini AI 聊天", page_icon="🤖", layout="wide")
st.title("🤖 Gemini AI 聊天助手")
st.caption("保留 chat_input（置底 + 自动高度），右下角浮动 📎 附件按钮 — 上传不自动发送")

with st.sidebar:
    st.header("🔧 配置")
    # 默认 API Key（可被覆盖）
    api_key = st.text_input(
        "Google Gemini API Key",
        type="password",
        value="AIzaSyD0HjQ57wfOtNxbbWqAlAIeRaQueZ9TjPk"
    )
    st.caption("示例：请务必不要在公共环境长期暴露你的 Key")

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
        "发送文件内容给 Gemini（base64）",
        value=False
    )
    st.caption("默认关闭：仅保留文件名作为元数据")

    # 清空聊天记录（不要调用 experimental_rerun — 点击后页面会自动重新执行）
    if st.button("🗑️ 清空聊天记录"):
        st.session_state.pop("messages", None)
        st.session_state.pop("pending_attachments", None)
        st.success("已清空聊天记录")

# ------------------------------
# 初始化 session_state
# ------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "pending_attachments" not in st.session_state:
    st.session_state["pending_attachments"] = []  # 每项为 dict {name,data,type,size}

# ------------------------------
# 显示历史消息
# ------------------------------
for i, msg in enumerate(st.session_state["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg.get("content", ""))
        atts = msg.get("attachments", [])
        if atts:
            st.markdown("**附件：**")
            for j, a in enumerate(atts):
                name = a.get("name")
                data = a.get("data")
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
# 单一 file_uploader（唯一 key：'main_uploader'）
# - 通过 CSS 使其看起来像浮动 📎 图标
# - 重要：只能存在这一个 uploader，避免 DuplicateElementKey
# ------------------------------
files = st.file_uploader(
    label="", 
    accept_multiple_files=True, 
    key="main_uploader", 
    label_visibility="collapsed"
)

st.markdown(
    """
    <style>
    /* 调整 uploader 的位置与样式（可按需微调 right/bottom） */
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
    div[data-testid="stFileUploader"] > div { height: 0 !important; overflow: visible !important; }
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
    unsafe_allow_html=True
)

# 处理新选文件并存入 pending_attachments（避免重复）
if files:
    selected = files if isinstance(files, list) else [files]
    added = []
    for f in selected:
        try:
            b = f.read()
        except Exception:
            b = None
        fingerprint = (f.name, len(b) if b is not None else -1)
        exists = any((p.get("name"), p.get("size")) == fingerprint for p in st.session_state["pending_attachments"])
        if not exists:
            st.session_state["pending_attachments"].append({
                "name": f.name,
                "data": b,
                "type": getattr(f, "type", None),
                "size": len(b) if b is not None else None
            })
            added.append(f.name)
    if added:
        st.success(f"已添加附件: {', '.join(added)}")

# 显示 pending attachments 并允许清除
if st.session_state["pending_attachments"]:
    cols = st.columns([0.9, 0.1])
    pending_names = ", ".join([p["name"] for p in st.session_state["pending_attachments"]])
    cols[0].markdown(f"**待发送附件：** {pending_names}")
    if cols[1].button("✖ 清除附件"):
        st.session_state["pending_attachments"] = []

# ------------------------------
# 唯一 chat_input（仅此一个，防止 DuplicateElementId）
# ------------------------------
if api_key:
    try:
        configure(api_key=api_key)
        model = GenerativeModel(selected_model)
    except Exception:
        st.error("API Key 配置失败，请检查 Key 或网络/SDK 是否正确")

    user_input = st.chat_input("请输入你的问题...")
    if user_input:
        # 构造附件元数据（保留 bytes 以便回放下载；可选把 base64 发给模型）
        attachments_payload = []
        for att in st.session_state.get("pending_attachments", []):
            item = {"name": att["name"], "data": att.get("data")}
            if send_file_contents and att.get("data") is not None:
                item["data_base64"] = base64.b64encode(att["data"]).decode("utf-8")
                item["size"] = att.get("size")
                item["type"] = att.get("type")
            attachments_payload.append(item)

        st.session_state["messages"].append({
            "role": "user",
            "content": user_input,
            "attachments": attachments_payload
        })
        with st.chat_message("user"):
            disp = user_input
            if attachments_payload:
                disp += "\n\n**附件:** " + ", ".join(a["name"] for a in attachments_payload)
            st.markdown(disp)

        # 清除 pending（已随消息保存）
        st.session_state["pending_attachments"] = []

        # 调用 Gemini（流式优先）
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            try:
                response = model.generate_content(user_input, stream=True)
                try:
                    for chunk in response:
                        text_piece = None
                        if hasattr(chunk, "text"):
                            text_piece = getattr(chunk, "text")
                        elif isinstance(chunk, dict):
                            text_piece = chunk.get("text") or chunk.get("output_text")
                        else:
                            text_piece = str(chunk)
                        if text_piece:
                            full += text_piece
                            placeholder.markdown(full + "▌")
                    placeholder.markdown(full)
                except TypeError:
                    raise Exception("stream returned non-iterable")
            except Exception:
                try:
                    response = model.generate_content(user_input)
                    text = None
                    if hasattr(response, "text"):
                        text = getattr(response, "text")
                    elif isinstance(response, dict):
                        text = response.get("text") or response.get("output_text")
                    if not text:
                        text = str(response)
                    full = text
                    placeholder.markdown(full)
                except Exception as e:
                    st.error(f"调用 Gemini 出错：{e}")
                    full = "[错误：无法获得模型响应]"

            st.session_state["messages"].append({"role": "assistant", "content": full})
else:
    # 只有提示信息，没有第二个 chat_input（避免重复 ID）
    st.info("请在侧边栏输入 Gemini API Key 以开始聊天")
