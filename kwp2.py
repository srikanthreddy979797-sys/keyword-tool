import os
import requests

# Try Streamlit secrets first (for deployment)
try:
    import streamlit as st
    CLIENT_ID = st.secrets["CLIENT_ID"]
    CLIENT_SECRET = st.secrets["CLIENT_SECRET"]
    REFRESH_TOKEN = st.secrets["REFRESH_TOKEN"]
except:
    # Fallback to .env (for local)
    from dotenv import load_dotenv
    load_dotenv()

    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")


TOKEN_URL = "https://oauth2.googleapis.com/token"


def get_access_token():
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }

    response = requests.post(TOKEN_URL, data=payload)

    if response.status_code != 200:
        raise Exception(f"Failed to get access token: {response.text}")

    data = response.json()
    access_token = data.get("access_token")

    if not access_token:
        raise Exception("Access token not found in response")

    return access_token


def main():
    token = get_access_token()
    print("\n✅ Access Token Generated:")
    print(token)


if __name__ == "__main__":
    main()
