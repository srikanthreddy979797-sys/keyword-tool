import os
import json
import tempfile

def get_credentials_file() -> str:
    if os.path.exists("sheets_credentials.json"):
        return "sheets_credentials.json"
    try:
        import streamlit as st
        creds_dict = dict(st.secrets["sheets_credentials"])
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(creds_dict, tmp)
        tmp.flush()
        return tmp.name
    except Exception as e:
        raise RuntimeError(f"Could not load credentials: {e}")
