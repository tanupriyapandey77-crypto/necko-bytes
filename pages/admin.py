import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ✅ Firebase setup — safe single init
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Necko Bytes Admin", page_icon="🔐")
st.title("🔐 Necko Bytes Admin Dashboard")

password = st.text_input("Enter admin password", type="password")

# ✅ BUG 1 FIXED — st.stop() prevents any content flashing on wrong/empty password
if not password:
    st.info("Enter the admin password to continue.")
    st.stop()

if password != st.secrets["admin"]["password"]:
    st.error("Wrong password!! 🚫")
    st.stop()

# Only reaches here if password is correct
st.success("Welcome boss!! 😏")

chats = list(db.collection("chats").stream())
st.write(f"Total sessions: {len(chats)}")

if len(chats) == 0:
    st.warning("No chats found in Firebase yet!!")
    st.stop()

# ✅ BONUS — Delete individual session from admin panel
for chat in chats:
    session_id = chat.id
    col1, col2 = st.columns([8, 1])
    with col1:
        st.subheader(f"👤 Session: {session_id[:8]}...")
    with col2:
        if st.button("🗑️", key=f"del_{session_id}", help="Delete this session"):
            msgs_ref = db.collection("chats").document(session_id).collection("messages")
            for doc in msgs_ref.stream():
                doc.reference.delete()
            db.collection("chats").document(session_id).delete()
            st.toast("Session deleted! ✅")
            st.rerun()

    messages = list(
        db.collection("chats")
        .document(session_id)
        .collection("messages")
        .order_by("timestamp")
        .stream()
    )
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