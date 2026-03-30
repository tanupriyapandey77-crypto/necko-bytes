import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase setup
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Necko Bytes Admin", page_icon="🔐")
st.title("🔐 Necko Bytes Admin Dashboard")

password = st.text_input("Enter admin password", type="password")

if password == "necko-admin-2024":
    st.success("Welcome boss!! 😏")

    chats = list(db.collection("chats").stream())
    st.write(f"Total sessions: {len(chats)}")

    if len(chats) == 0:
        st.warning("No chats found in Firebase yet!!")
    
    for chat in chats:
        session_id = chat.id
        st.subheader(f"👤 Session: {session_id[:8]}...")
        
        messages = list(db.collection("chats").document(session_id).collection("messages").order_by("timestamp").stream())
        st.write(f"Messages: {len(messages)}")
        
        for msg in messages:
            data = msg.to_dict()
            role = data.get("role", "unknown")
            content = data.get("content", "")
            timestamp = data.get("timestamp", "")
            
            if role == "user":
                st.markdown(f"**🙋 User:** {content}")
            else:
                st.markdown(f"**🐱 Necko Bytes:** {content}")
            st.caption(f"{timestamp}")
        
        st.divider()

else:
    if password:
        st.error("Wrong password!! 🚫")