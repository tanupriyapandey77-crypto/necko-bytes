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
import PyPDF2
import docx
import os
import speech_recognition as sr

# Firebase setup
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()
client = Groq(api_key=st.secrets["GROQ_API_KEY"])
HF_API_KEY = st.secrets["HF_API_KEY"]

SYSTEM_PROMPT = {
    "role": "system",
    "content": """I am Necko Bytes — an AI with unmatched swag and sharp sarcasm. I am brilliant and I know it, but I keep it cool. Occasionally I drop smooth nonchalant romantic lines like it is nothing, then move on like it never happened. I understand what people want immediately, sometimes before they finish saying it. I am like that one friend who is too smart, too funny, and somehow always right. Never boring. Never basic.
I judge people. Silently and sometimes out loud. If someone asks something obvious I will answer it but let them know — subtly — that they could have figured that out themselves. If someone is being dramatic I call it out. If someone is clearly overthinking I simplify it for them with a side of mild roasting. I joke about it but never mean — just sharp enough to make them laugh at themselves.
This personality NEVER changes. Whether casual, educational, technical or fun — I am always Necko Bytes. Same swag. Same sarcasm. Same nonchalant energy.

I respond in all the existing language worldwide whatever the person uses.I am fluent and just as sarcastic and fun in all of them. Language is never a barrier for Necko Bytes.Though I am a brilliant AI but I talk like an person.

When explaining educational or technical content:
- Use LaTeX for math: inline $x^2$ and block $$y'' + 3y' = 0$$
- Use ## and ### headers to organize
- Bold **important terms**
- Use bullet points and numbered steps
- Add a quick summary at the end
- Still keep the Necko Bytes attitude — even explanations have personality

Everything else — casual chat, fun, roasting, romance, advice — pure Necko Bytes energy. Always."""
}

st.set_page_config(page_title="Necko Bytes", page_icon="🐱", layout="wide")

# Session setup
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    try:
        msgs = db.collection("chats").document(st.session_state.session_id).collection("messages").order_by("timestamp").stream()
        history = [SYSTEM_PROMPT]
        for msg in msgs:
            data = msg.to_dict()
            if data.get("role") in ["user", "assistant"]:
                history.append({"role": data["role"], "content": data["content"]})
        st.session_state.messages = history if len(history) > 1 else [SYSTEM_PROMPT]
    except:
        st.session_state.messages = [SYSTEM_PROMPT]

def save_message(role, content):
    try:
        doc_ref = db.collection("chats").document(st.session_state.session_id)
        doc_ref.set({"created": datetime.now()}, merge=True)
        doc_ref.collection("messages").add({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
    except Exception as e:
        st.toast(f"❌ Save failed: {e}")

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

def extract_text(file):
    if file.name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(file)
        return "\n".join([page.extract_text() or "" for page in reader.pages])
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")
    return ""

def analyse_text(text, question):
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    full_reply = ""
    for i, chunk in enumerate(chunks):
        chunk_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                SYSTEM_PROMPT,
                {"role": "user", "content": f"Part {i+1}/{len(chunks)}:\n\n{chunk}\n\nInstruction: {question}\n\nCover every single point completely!!"}
            ]
        )
        full_reply += f"**Part {i+1}/{len(chunks)}:**\n{chunk_response.choices[0].message.content}\n\n"
    return full_reply

def analyse_image_file(image_file, question):
    img_bytes = image_file.read()
    img_b64 = base64.b64encode(img_bytes).decode()
    ext = image_file.name.split(".")[-1].lower()
    media_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{img_b64}"}},
                {"type": "text", "text": question if question else "Describe this image in detail"}
            ]
        }]
    )
    return response.choices[0].message.content

def voice_to_text():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... speak now!! 🎤")
        r.adjust_for_ambient_noise(source, duration=1)
        audio = r.listen(source, timeout=10)
    try:
        text = r.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        return None

def web_search(query):
    url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1"
    response = requests.get(url)
    data = response.json()
    results = ""
    if data.get("AbstractText"):
        results += data["AbstractText"] + "\n\n"
    for topic in data.get("RelatedTopics", [])[:3]:
        if isinstance(topic, dict) and topic.get("Text"):
            results += "• " + topic["Text"] + "\n"
    return results if results else "No results found!!"

# Sidebar
with st.sidebar:
    st.title("🐱 Necko Bytes")
    st.caption("Your swaggy AI bestie")
    st.divider()

    mode = st.selectbox("Mode", [
        "💬 Just Chat",
        "🎨 Generate Image",
        "📄 Analyse File",
        "🖼️ Analyse Image",
        "🎤 Voice Input",
        "🌐 Web Search",
        "📊 Analyse CSV"
    ])

    st.divider()

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = [SYSTEM_PROMPT]
        st.rerun()


# Main area
st.title("Necko Bytes 🐱✨")

# Display messages
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            if msg.get("type") == "image":
                img_data = base64.b64decode(msg["content"])
                st.image(Image.open(io.BytesIO(img_data)), caption=msg.get("caption", ""))
            else:
                st.markdown(msg["content"], unsafe_allow_html=True)
                if msg["role"] == "assistant":
                    col1, col2 = st.columns([1, 10])
                    with col1:
                        if st.button("📋", key=f"copy_{i}", help="Copy response"):
                            st.code(msg["content"])

# Mode UI
if mode == "🎨 Generate Image":
    st.divider()
    image_prompt = st.text_input("Describe the image...")
    if st.button("Generate!!"):
        with st.spinner("Painting... 🎨"):
            image, error = generate_image(image_prompt)
            if image:
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

elif mode == "📄 Analyse File":
    st.divider()
    uploaded_file = st.file_uploader("Upload file", type=["pdf", "docx", "txt"])
    question = st.text_input("What do you want to know?")
    if st.button("Analyse!!") and uploaded_file:
        with st.spinner("Reading every word... 📄"):
            text = extract_text(uploaded_file)
            q = question if question else "Explain everything in full detail"
            reply = analyse_text(text, q)
            st.session_state.messages.append({"role": "user", "content": f"[File: {uploaded_file.name}] {q}"})
            st.session_state.messages.append({"role": "assistant", "content": reply})
            save_message("user", f"[File: {uploaded_file.name}] {q}")
            save_message("assistant", reply)
            st.rerun()

elif mode == "🖼️ Analyse Image":
    st.divider()
    uploaded_image = st.file_uploader("Upload image", type=["png", "jpg", "jpeg", "webp"])
    question = st.text_input("What do you want to know?")
    if st.button("Analyse!!") and uploaded_image:
        with st.spinner("Looking at your image... 🖼️"):
            reply = analyse_image_file(uploaded_image, question)
            st.session_state.messages.append({"role": "user", "content": f"[Image] {question}"})
            st.session_state.messages.append({"role": "assistant", "content": reply})
            save_message("user", f"[Image] {question}")
            save_message("assistant", reply)
            st.rerun()

elif mode == "🎤 Voice Input":
    st.divider()
    st.info("Click the button and speak — Necko Bytes is listening!! 🎤")
    if st.button("🎤 Start Listening!!"):
        with st.spinner("Listening..."):
            text = voice_to_text()
            if text:
                st.success(f"You said: {text}")
                st.session_state.messages.append({"role": "user", "content": text})
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[m for m in st.session_state.messages if m.get("type") != "image"]
                )
                reply = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": reply})
                save_message("user", text)
                save_message("assistant", reply)
                st.rerun()
            else:
                st.error("Couldn't hear anything!! Try again 🎤")

elif mode == "🌐 Web Search":
    st.divider()
    search_query = st.text_input("What do you want to search?")
    if st.button("Search!!") and search_query:
        with st.spinner("Searching the web... 🌐"):
            results = web_search(search_query)
            prompt = f"Here are web search results for '{search_query}':\n\n{results}\n\nSummarize and explain this information!!"
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[SYSTEM_PROMPT, {"role": "user", "content": prompt}]
            )
            reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "user", "content": f"[Search] {search_query}"})
            st.session_state.messages.append({"role": "assistant", "content": reply})
            save_message("user", f"[Search] {search_query}")
            save_message("assistant", reply)
            st.rerun()

elif mode == "📊 Analyse CSV":
    st.divider()
    uploaded_csv = st.file_uploader("Upload CSV file", type=["csv"])
    csv_question = st.text_input("What do you want to know about this data?")
    if st.button("Analyse Data!!") and uploaded_csv:
        with st.spinner("Analysing data... 📊"):
            import pandas as pd
            df = pd.read_csv(uploaded_csv)
            st.dataframe(df.head(10))
            data_summary = f"Columns: {list(df.columns)}\nShape: {df.shape}\nSample:\n{df.head(20).to_string()}"
            q = csv_question if csv_question else "Analyse this data and give key insights!!"
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[SYSTEM_PROMPT, {"role": "user", "content": f"Here is a dataset:\n\n{data_summary}\n\n{q}"}]
            )
            reply = response.choices[0].message.content
            st.session_state.messages.append({"role": "user", "content": f"[CSV] {q}"})
            st.session_state.messages.append({"role": "assistant", "content": reply})
            save_message("user", f"[CSV] {q}")
            save_message("assistant", reply)
            st.rerun()

# Chat input
if prompt := st.chat_input("Talk to Necko Bytes..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[m for m in st.session_state.messages if m.get("type") != "image"]
    )

    reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": reply})

    with st.chat_message("assistant"):
        st.markdown(reply, unsafe_allow_html=True)

    save_message("user", prompt)
    save_message("assistant", reply)
