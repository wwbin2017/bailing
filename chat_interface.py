import streamlit as st
from bailing.rag import Rag

# 初始化配置
config = {
    "doc_path": "./docs",
    "emb_model": "BAAI/bge-large-en-v1.5",
    "model_name": "llama2",
    "base_url": "http://localhost:11434"
}

# 初始化 RAG 实例
rag = Rag(config)

# 设置页面标题
st.title("Bailing 项目聊天界面")

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 获取用户输入
if prompt := st.chat_input("请输入你的问题"):
    # 显示用户消息
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用 RAG 模型获取回答
    try:
        response = rag.query(prompt)
    except Exception as e:
        response = f"出现错误: {str(e)}"

    # 显示助手消息
    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

