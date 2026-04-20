import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from collections import Counter
import re

# ✅ Firebase setup — safe single init
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Necko Bytes Analytics", page_icon="📊", layout="wide")
st.title("📊 Necko Bytes — Analytics Dashboard")

# ── Password gate ──────────────────────────────────────────────
password = st.text_input("Enter admin password", type="password")
if not password:
    st.info("Enter the admin password to continue.")
    st.stop()
if password != st.secrets["admin"]["password"]:
    st.error("Wrong password!! 🚫")
    st.stop()

st.success("Welcome boss!! 😏")
st.divider()

# ── Pull all data from Firebase ────────────────────────────────
@st.cache_data(ttl=60)  # refreshes every 60 seconds
def load_all_data():
    rows = []
    chats = db.collection("chats").stream()
    for chat in chats:
        session_id = chat.id
        messages = (
            db.collection("chats")
            .document(session_id)
            .collection("messages")
            .order_by("timestamp")
            .stream()
        )
        for msg in messages:
            data = msg.to_dict()
            rows.append({
                "session_id": session_id,
                "role": data.get("role", "unknown"),
                "content": data.get("content", ""),
                "timestamp": data.get("timestamp", None),
            })
    return pd.DataFrame(rows)

with st.spinner("Loading data from Firebase... 🔥"):
    df = load_all_data()

if df.empty:
    st.warning("No chat data found yet!! Go talk to Necko Bytes first 😏")
    st.stop()

# ── Clean up timestamps ────────────────────────────────────────
df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
df["date"] = df["timestamp"].dt.date
df["hour"] = df["timestamp"].dt.hour

# ── STAT 1 — Quick numbers ─────────────────────────────────────
st.subheader("⚡ Quick Stats")
col1, col2, col3, col4 = st.columns(4)
col1.metric("💬 Total Messages", len(df))
col2.metric("👤 Total Sessions", df["session_id"].nunique())
col3.metric("🙋 User Messages", len(df[df["role"] == "user"]))
col4.metric("🐱 Necko Replies", len(df[df["role"] == "assistant"]))

st.divider()

# ── CHART 1 — Messages per day ─────────────────────────────────
st.subheader("📅 Messages Per Day")
daily = df.groupby("date").size().reset_index(name="messages")
daily["date"] = daily["date"].astype(str)
st.line_chart(daily.set_index("date")["messages"])

st.divider()

# ── CHART 2 — User vs Necko ratio ─────────────────────────────
st.subheader("🐱 User vs Necko Bytes — Message Split")
role_counts = df["role"].value_counts().reset_index()
role_counts.columns = ["role", "count"]
role_counts = role_counts[role_counts["role"].isin(["user", "assistant"])]
role_counts["role"] = role_counts["role"].replace({"assistant": "Necko Bytes"})
st.bar_chart(role_counts.set_index("role")["count"])

st.divider()

# ── CHART 3 — Most active sessions ────────────────────────────
st.subheader("🏆 Most Active Sessions")
session_counts = (
    df[df["role"] == "user"]
    .groupby("session_id")
    .size()
    .reset_index(name="user_messages")
    .sort_values("user_messages", ascending=False)
    .head(10)
)
session_counts["session_id"] = session_counts["session_id"].str[:8] + "..."
st.bar_chart(session_counts.set_index("session_id")["user_messages"])

st.divider()

# ── CHART 4 — Busiest hours of the day ────────────────────────
st.subheader("🕐 Busiest Hours of the Day")
hourly = df.groupby("hour").size().reset_index(name="messages")
hourly["hour"] = hourly["hour"].astype(str) + ":00"
st.bar_chart(hourly.set_index("hour")["messages"])

st.divider()

# ── CHART 5 — Most common words users ask ─────────────────────
st.subheader("💬 Most Common Words Users Ask")

STOPWORDS = {
    "the","a","an","is","it","in","on","at","to","of","and","or","but",
    "i","you","me","my","your","we","he","she","they","this","that","was",
    "are","be","for","with","do","did","can","have","has","what","how",
    "why","when","where","who","just","so","if","not","no","yes","please",
    "ok","okay","hi","hey","hello","like","get","got","make","will","use",
    "im","dont","its","about","from","also","some","any","more","up","out",
    "than","then","them","their","there","here","now","all","been","would",
    "could","should","which","very","much","too","one","know","think","want"
}

user_text = " ".join(df[df["role"] == "user"]["content"].dropna().tolist()).lower()
words = re.findall(r'\b[a-z]{3,}\b', user_text)
filtered = [w for w in words if w not in STOPWORDS]
word_freq = Counter(filtered).most_common(20)

if word_freq:
    word_df = pd.DataFrame(word_freq, columns=["word", "count"])
    st.bar_chart(word_df.set_index("word")["count"])
else:
    st.info("Not enough data yet for word analysis!!")

st.divider()

# ── Raw data table ─────────────────────────────────────────────
with st.expander("🗃️ View Raw Data Table"):
    display_df = df[["session_id", "role", "content", "timestamp"]].copy()
    display_df["timestamp"] = display_df["timestamp"].astype(str)
    display_df["session_id"] = display_df["session_id"].str[:8] + "..."
    st.dataframe(display_df.sort_values("timestamp", ascending=False), use_container_width=True)