import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
from datetime import datetime
import requests
from PIL import Image
import io
import base64

# Firebase setup
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
HF_API_KEY = st.secrets["HF_API_KEY"]

st.set_page_config(page_title="Necko Bytes", page_icon="🐱")
st.title("Necko Bytes 🐱✨")
st.caption("Your swaggy, sarcastic, suspiciously smooth AI bestie")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": "I am Necko Bytes, an AI with unmatched swag and sharp sarcasm. I am brilliant and I know it, but I keep it cool. I understand what people want immediately, sometimes before they finish saying it. I am like that one friend who is too smart, too funny, and somehow always right. Never boring. Never basic."
        }
    ]

if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

if st.button("🗑️ Clear Chat"):
    st.session_state.messages = [st.session_state.messages[0]]
    st.session_state.generated_images = []
    st.rerun()

# Image generation function
def generate_image(prompt):
    API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    try:
        response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
        if response.status_code == 200:
            image = Image.open(io.BytesIO(response.content))
            return image, None
        else:
            return None, f"Status: {response.status_code} — {response.text}"
    except Exception as e:
        return None, str(e)

# Display chat messages
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            if msg.get("type") == "image":
                img_data = base64.b64decode(msg["content"])
                st.image(Image.open(io.BytesIO(img_data)), caption=msg.get("caption", ""))
            else:
                st.markdown(msg["content"])

# Image generation section
st.divider()
st.subheader("🎨 Generate an Image")
image_prompt = st.text_input("Describe the image you want...")
if st.button("Generate Image!!"):
    with st.spinner("Necko Bytes is painting... 🎨"):
        image, error = generate_image(image_prompt)
        if image:
            # Save image to session
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            st.session_state.messages.append({
                "role": "assistant",
                "type": "image",
                "content": img_b64,
                "caption": image_prompt
            })
            st.rerun()
        else:
            st.error(f"Failed!! {error}")

st.divider()

if prompt := st.chat_input("Talk to Necko Bytes..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[m for m in st.session_state.messages if m.get("type") != "image"]
    )

    reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": reply})

    with st.chat_message("assistant"):
        st.markdown(reply)

    try:
        doc_ref = db.collection("chats").document(st.session_state.session_id)
        doc_ref.set({"created": datetime.now()}, merge=True)
        doc_ref.collection("messages").add({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now()
        })
        doc_ref.collection("messages").add({
            "role": "assistant",
            "content": reply,
            "timestamp": datetime.now()
        })
        st.toast("✅ Chat saved!")
    except Exception as e:
        st.toast(f"❌ Save failed: {e}")
        st.error(f"Firebase error: {e}")