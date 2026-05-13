import streamlit as st
from workflow import workflow,retrieve_threads
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage,AIMessage
import uuid

################################ Utility functions##############################
def generate_session_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_session_id()
    st.session_state["thread_id"] = thread_id
    add_thread_id(st.session_state["thread_id"])
    st.session_state["message_history"] = []

def add_thread_id(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

def load_conversation(thread_id):
    messages = workflow.get_state(config={"configurable":{"thread_id":thread_id}}).values.get("messages",[])
    return messages

################################ Session setup ##############################
if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_session_id()

if "chat_threads"not in st.session_state:
    st.session_state["chat_threads"] = retrieve_threads()

add_thread_id(st.session_state["thread_id"])
#message_history = []

################################ Sidebar UI ##############################

st.sidebar.title("Portfolio Valuation")

if st.sidebar.button("New Chat"):
    reset_chat()

st.sidebar.header("My Conversations")

for thread_id in st.session_state.get("chat_threads")[::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state["thread_id"] = thread_id
        messages = load_conversation(thread_id)
        tmp_messages = []
        for msg in messages:
            if isinstance(msg,HumanMessage):
                role = "user"
            else:
                role = "assistant"
            tmp_messages.append({"role":role,"content":msg.content})
        
        st.session_state["message_history"] = tmp_messages

for message in st.session_state["message_history"]:
    with st.chat_message(message.get("role")):
        st.text(message.get("content"))

user_message= st.chat_input('Type here')

if user_message:
    st.session_state["message_history"].append({"role": "user","content": user_message})
    with st.chat_message("user"):
        st.text(user_message)

    with st.chat_message("assistant"):
        #config = {"configurable":{"thread_id":st.session_state.get("thread_id")}}
        config = {"configurable": {"thread_id": st.session_state.get("thread_id")},
                  "metadata" : {"thread_id": st.session_state.get("thread_id")},
                  "run_name": "chat_turn" }
        def ai_only_stream():
            for message_chunk,metadata in workflow.stream(
                    {"messages" : [HumanMessage(content=user_message)]},
                    config=config,stream_mode="messages"
                ):
                if isinstance(message_chunk,AIMessage):
                    yield message_chunk.content
                    
        ai_message = st.write_stream(ai_only_stream())
            
        st.session_state["message_history"].append({"role": "assistant","content": ai_message})