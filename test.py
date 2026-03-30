import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

chats = list(db.collection("chats").stream())
print(f"Total sessions found: {len(chats)}")

for chat in chats:
    print(f"Session ID: {chat.id}")
