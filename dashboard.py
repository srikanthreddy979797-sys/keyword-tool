import streamlit as st
import pandas as pd

from kwp1 import prepare_input_data, validate_input
from kwp2 import get_access_token
from kwp3 import fetch_keyword_ideas
from kwp4 import process_keywords


# ------------------ CONFIG ------------------
st.set_page_config(
    page_title="Keyword Tool",
    page_icon="🚀",
    layout="wide"
)

# ------------------ SESSION ------------------
if "data" not in st.session_state:
    st.session_state["data"] = None

# ------------------ STYLING ------------------
st.markdown("""
<style>
.main {
    background-color: #0E1117;
}
h1 {
    color: #FFFFFF;
    font-size: 40px;
}
.stButton>button {
    background: linear-gradient(90deg, #00C853, #64DD17);
    color: white;
    border-radius: 12px;
    padding: 12px 24px;
    font-size: 16px;
    font-weight: 600;
    border: none;
}
.stDownloadButton>button {
    background-color: #2962FF;
    color: white;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ------------------ COUNTRY ------------------
COUNTRIES = {
    "India": "india",
    "United States": "united states",
    "United Kingdom": "uk",
    "Canada": "canada",
    "Australia": "australia"
}

# ------------------ HEADER ------------------
st.markdown("""
# 🚀 Google Ads Keyword Research Tool
### Discover high-performing keywords with real insights
""")

st.divider()

# ------------------ INPUT ------------------
keyword = st.text_input("Enter Keyword")
country_display = st.selectbox("Select Country", list(COUNTRIES.keys()))
country = COUNTRIES[country_display]

st.divider()

# ------------------ SIDEBAR FILTERS ------------------
st.sidebar.markdown("## 🔍 Filters")
st.sidebar.divider()

min_volume = st.sidebar.number_input("Minimum Volume", value=0)
max_cpc = st.sidebar.number_input("Max CPC", value=1000.0)

intent_filter = st.sidebar.selectbox(
    "Intent",
    ["All", "High", "Research", "Comparison", "Low"]
)

sort_by = st.sidebar.selectbox("Sort By", ["volume", "cpc"])

# ------------------ BUTTON ------------------
if st.button("Get Keywords"):

    if not keyword:
        st.error("Please enter a keyword")
    else:
        try:
            validate_input(keyword, country)
            prepared = prepare_input_data(keyword, country)

            access_token = get_access_token()

            with st.spinner("Fetching keyword data..."):
                api_response = fetch_keyword_ideas(
                    access_token,
                    prepared["keyword"],
                    prepared["geo_target"],
                    prepared["language"]
                )

            # Fallback
            if not api_response.get("results"):
                st.warning("Using mock data (API not approved yet)")

                api_response = {
                    "results": [
                        {
                            "text": "buy " + keyword,
                            "keyword_idea_metrics": {
                                "avg_monthly_searches": 12000,
                                "competition": "HIGH",
                                "low_top_of_page_bid_micros": 50000000
                            }
                        },
                        {
                            "text": "best " + keyword,
                            "keyword_idea_metrics": {
                                "avg_monthly_searches": 8000,
                                "competition": "MEDIUM",
                                "low_top_of_page_bid_micros": 30000000
                            }
                        }
                    ]
                }

            st.session_state["data"] = process_keywords(api_response)

        except Exception as e:
            st.error(f"Error: {str(e)}")


# ------------------ DISPLAY ------------------
if st.session_state["data"]:

    df = pd.DataFrame(st.session_state["data"])

    # Apply filters
    filtered_df = df.copy()
    filtered_df = filtered_df[filtered_df["volume"] >= min_volume]
    filtered_df = filtered_df[filtered_df["cpc"] <= max_cpc]

    if intent_filter != "All":
        filtered_df = filtered_df[filtered_df["intent"] == intent_filter]

    filtered_df = filtered_df.sort_values(by=sort_by, ascending=False)

    st.success("Keyword Data Retrieved")
    st.divider()

    # Summary
    st.subheader("📊 Performance Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Keywords", len(filtered_df))
    col2.metric("Avg CPC", round(filtered_df["cpc"].mean(), 2))
    col3.metric("High Intent", sum(filtered_df["intent"] == "High"))

    st.divider()

    # Table
    st.markdown("### 📋 Keyword Results")
    st.dataframe(filtered_df, use_container_width=True)

    # Download
    csv = filtered_df.to_csv(index=False).encode('utf-8')

    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="keywords.csv",
        mime="text/csv",
    )

# ------------------ EMPTY STATE ------------------
if not keyword:
    st.info("👈 Enter a keyword and click 'Get Keywords'")