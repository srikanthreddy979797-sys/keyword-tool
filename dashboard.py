import streamlit as st
import pandas as pd
import os
import time
from dotenv import load_dotenv
from data_sources import build_keyword_dataset
from ai_analysis import analyse_keywords_with_ai
from sheets_export import export_to_sheets

load_dotenv()

# Load from Streamlit Secrets if running in cloud
try:
    import streamlit as st
    if hasattr(st, 'secrets'):
        os.environ.setdefault("GROQ_API_KEY",
            st.secrets.get("GROQ_API_KEY", ""))
        os.environ.setdefault("SHEETS_MASTER_ID",
            st.secrets.get("SHEETS_MASTER_ID", ""))
        os.environ.setdefault("PERFORMANCE_SHEET_ID",
            st.secrets.get("PERFORMANCE_SHEET_ID", ""))
except Exception:
    pass

st.set_page_config(page_title="Keyword Intelligence Tool", page_icon="🚀", layout="wide")

# ------------------ SESSION STATE ------------------
if "data" not in st.session_state:
    st.session_state["data"] = None
if "ai_analysis" not in st.session_state:
    st.session_state["ai_analysis"] = None
if "competitor_data" not in st.session_state:
    st.session_state["competitor_data"] = None
if "domain_summary" not in st.session_state:
    st.session_state["domain_summary"] = None

# ------------------ STYLING ------------------
st.markdown("""
<style>
.stMetric { background: #1E1E2E; border-radius: 12px; padding: 12px; }
</style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.title("🚀 Keyword Intelligence Tool")
st.caption("Powered by Google Autocomplete + Trends + DataForSEO + Groq AI")
st.divider()

# ------------------ COUNTRIES ------------------
COUNTRIES = {
    "India": "IN", "United States": "US", "United Kingdom": "GB",
    "Canada": "CA", "Australia": "AU", "Singapore": "SG"
}

# ------------------ INPUT ------------------
col1, col2 = st.columns([3, 1])
with col1:
    keyword = st.text_input("Enter seed keyword",
                            placeholder="e.g. life insurance, running shoes, cloud software")
with col2:
    country_display = st.selectbox("Country", list(COUNTRIES.keys()))
    country = COUNTRIES[country_display]

# ------------------ SIDEBAR ------------------
st.sidebar.markdown("## Filters")
min_volume = st.sidebar.number_input("Min Volume", value=0)
max_cpc = st.sidebar.number_input("Max CPC", value=100.0)
intent_filter = st.sidebar.selectbox("Intent", ["All", "BOFU", "MOFU", "TOFU"])
competition_filter = st.sidebar.selectbox("Competition", ["All", "HIGH", "MEDIUM", "LOW"])
sort_by = st.sidebar.selectbox("Sort By", ["opportunity_score", "volume", "cpc", "trend_score"])
show_rising = st.sidebar.checkbox("Rising keywords only", False)
show_questions = st.sidebar.checkbox("Question keywords only", False)

# ------------------ FETCH BUTTON ------------------
if st.button("🔍 Get Keywords", use_container_width=True):
    if not keyword:
        st.error("Please enter a keyword")
    else:
        with st.spinner("Fetching from Google Autocomplete + Trends..."):
            data = build_keyword_dataset(keyword, country)

        if os.getenv("DATAFORSEO_LOGIN"):
            with st.spinner("Enriching with real volume + CPC from DataForSEO..."):
                from dataforseo_client import enrich_keywords_with_real_data
                data = enrich_keywords_with_real_data(data, country)

        st.session_state["data"] = data
        st.session_state["ai_analysis"] = None
        st.session_state["competitor_data"] = None
        st.session_state["domain_summary"] = None
        st.success(f"Found {len(data)} keywords")

# ------------------ MAIN CONTENT ------------------
if st.session_state["data"]:
    df = pd.DataFrame(st.session_state["data"])

    # ------------------ FILTERS ------------------
    filtered = df.copy()
    filtered = filtered[filtered["volume"] >= min_volume]
    filtered = filtered[filtered["cpc"] <= max_cpc]
    if intent_filter != "All":
        filtered = filtered[filtered["intent"] == intent_filter]
    if competition_filter != "All":
        filtered = filtered[filtered["competition"] == competition_filter]
    if show_rising and "is_rising" in filtered.columns:
        filtered = filtered[filtered["is_rising"] == True]
    if show_questions and "is_question" in filtered.columns:
        filtered = filtered[filtered["is_question"] == True]
    if sort_by in filtered.columns:
        filtered = filtered.sort_values(by=sort_by, ascending=False)

    st.divider()

    # ------------------ METRICS ------------------
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Keywords", len(filtered))
    c2.metric("Avg CPC", f"${round(filtered['cpc'].mean(), 2)}")
    c3.metric("BOFU", len(filtered[filtered['intent'] == 'BOFU']))
    c4.metric("MOFU", len(filtered[filtered['intent'] == 'MOFU']))
    c5.metric("TOFU", len(filtered[filtered['intent'] == 'TOFU']))
    c6.metric("Rising", len(filtered[filtered['is_rising'] == True]) if 'is_rising' in filtered.columns else 0)

    st.divider()

    # ------------------ TABS ------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Keywords",
        "❓ Questions",
        "🤖 AI Analysis",
        "🔍 Competitors",
        "📥 Export"
    ])

    # ------------------ TAB 1: KEYWORDS ------------------
    with tab1:
        st.markdown("### Keyword Results")

        display_cols = ["keyword", "opportunity_score", "volume", "cpc",
                        "low_bid", "high_bid", "competition", "competition_index",
                        "intent", "trend_score", "is_rising", "is_question", "data_source"]
        display_cols = [c for c in display_cols if c in filtered.columns]
        display_df = filtered[display_cols].copy()

        def color_intent(val):
            colors = {"BOFU": "color: #FF4B4B; font-weight: bold",
                      "MOFU": "color: #FFA500; font-weight: bold",
                      "TOFU": "color: #00C853; font-weight: bold"}
            return colors.get(val, "")

        def color_score(val):
            if isinstance(val, (int, float)):
                if val >= 70:
                    return "color: #00C853; font-weight: bold"
                elif val >= 40:
                    return "color: #FFA500"
                else:
                    return "color: #FF4B4B"
            return ""

        def color_competition(val):
            colors = {"HIGH": "color: #FF4B4B",
                      "MEDIUM": "color: #FFA500",
                      "LOW": "color: #00C853"}
            return colors.get(val, "")

        styled = display_df.style \
            .map(color_intent,
                      subset=["intent"] if "intent" in display_cols else []) \
            .map(color_score,
                      subset=["opportunity_score"] if "opportunity_score" in display_cols else []) \
            .map(color_competition,
                      subset=["competition"] if "competition" in display_cols else [])

        st.dataframe(styled, use_container_width=True, height=500)

        if "monthly_searches" in filtered.columns:
            with st.expander("View monthly search trends"):
                trend_df = filtered[["keyword", "monthly_searches"]].copy()
                trend_df = trend_df[trend_df["monthly_searches"] != ""]
                st.dataframe(trend_df, use_container_width=True)

    # ------------------ TAB 2: QUESTIONS ------------------
    with tab2:
        st.markdown("### Question Keywords")
        st.caption("Questions people ask — ideal for DSA campaigns and content targeting")

        if "is_question" in filtered.columns:
            question_df = filtered[filtered["is_question"] == True].copy()
        else:
            question_df = pd.DataFrame()

        if not question_df.empty:
            q_display = ["keyword", "opportunity_score", "volume", "cpc",
                         "competition", "intent", "trend_score", "data_source"]
            q_display = [c for c in q_display if c in question_df.columns]

            qc1, qc2, qc3 = st.columns(3)
            qc1.metric("Total Questions", len(question_df))
            qc2.metric("Avg Volume", int(question_df["volume"].mean()))
            qc3.metric("Avg CPC", f"${round(question_df['cpc'].mean(), 2)}")

            st.dataframe(question_df[q_display], use_container_width=True, height=400)

            csv_q = question_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Question Keywords",
                csv_q, "question_keywords.csv", "text/csv",
                use_container_width=True
            )
        else:
            st.info("No question keywords found. Try a broader seed keyword.")

    # ------------------ TAB 3: AI ANALYSIS ------------------
    with tab3:
        st.markdown("### Groq AI Analysis")
        st.caption("Powered by Llama 3.3 70B — keyword clusters, ad groups, ad copy, negatives")

        if st.session_state["ai_analysis"] is None:
            if st.button("Run AI Analysis", use_container_width=True):
                with st.spinner("Groq AI is analysing your keywords..."):
                    analysis = analyse_keywords_with_ai(
                        filtered.to_dict("records"), keyword
                    )
                    st.session_state["ai_analysis"] = analysis

        if st.session_state["ai_analysis"]:
            analysis = st.session_state["ai_analysis"]

            # Top opportunity
            st.info(f"**Top Opportunity:** {analysis.get('top_opportunity', '')}")

            # Budget recommendation
            if analysis.get("budget_recommendation"):
                st.success(f"**Budget Recommendation:** {analysis.get('budget_recommendation', '')}")

            st.divider()

            # Keyword clusters
            st.markdown("#### Keyword Clusters")
            clusters = analysis.get("clusters", [])
            if clusters:
                for cluster in clusters:
                    intent_icon = {"BOFU": "🔴", "MOFU": "🟡", "TOFU": "🟢"}.get(
                        cluster.get("intent", ""), "⚪")
                    with st.expander(f"{intent_icon} {cluster['name']} — {cluster['theme']}"):
                        col1, col2, col3 = st.columns(3)
                        col1.write(f"**Intent:** {cluster.get('intent', '')}")
                        col2.write(f"**Match Type:** {cluster.get('recommended_match_type', '')}")
                        col3.write(f"**Bid Strategy:** {cluster.get('bid_strategy', '')}")
                        st.write("**Keywords:**", ", ".join(cluster.get("keywords", [])))
            else:
                st.info("No clusters returned — try running analysis again.")

            st.divider()

            # Negative keywords
            st.markdown("#### Negative Keywords")
            negs = analysis.get("negative_keywords", [])
            if negs:
                st.code(" | ".join(negs))

            st.divider()

            # Ad groups
            st.markdown("#### Suggested Ad Groups")
            for ag in analysis.get("ad_groups", []):
                with st.expander(f"Ad Group: {ag['name']} — {ag['theme']}"):
                    st.write("**Keywords:**", ", ".join(ag.get("keywords", [])))
                    mt = ag.get("match_types", {})
                    col1, col2, col3 = st.columns(3)
                    col1.write("**Exact:**")
                    col1.write("\n".join([f"[{k}]" for k in mt.get("exact", [])]))
                    col2.write("**Phrase:**")
                    col2.write("\n".join([f'"{k}"' for k in mt.get("phrase", [])]))
                    col3.write("**Broad:**")
                    col3.write("\n".join(mt.get("broad", [])))

            st.divider()

            # Ad copy
            st.markdown("#### Ad Copy Suggestions")
            copy = analysis.get("ad_copy", {})
            if copy:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Headlines:**")
                    st.write(f"H1: {copy.get('headline_1', '')}")
                    st.write(f"H2: {copy.get('headline_2', '')}")
                    st.write(f"H3: {copy.get('headline_3', '')}")
                with col2:
                    st.markdown("**Descriptions:**")
                    st.write(f"D1: {copy.get('description_1', '')}")
                    st.write(f"D2: {copy.get('description_2', '')}")

    # ------------------ TAB 4: COMPETITORS ------------------
    with tab4:
        st.markdown("### Competitor Research")
        st.caption("Who is ranking organically for your top keywords")

        if st.button("Analyse Competitors", use_container_width=True):
            from competitor_research import get_serp_competitors, analyse_competitor_domains

            top_keywords = filtered.head(5)["keyword"].tolist()
            all_serp = []
            progress = st.progress(0)

            for i, kw in enumerate(top_keywords):
                with st.spinner(f"Checking SERP for: {kw}"):
                    result = get_serp_competitors(kw, country)
                    all_serp.append(result)
                    progress.progress((i + 1) / len(top_keywords))
                    time.sleep(1)

            st.session_state["competitor_data"] = all_serp
            domain_summary = analyse_competitor_domains(all_serp)
            st.session_state["domain_summary"] = domain_summary

        if st.session_state.get("competitor_data"):
            domain_summary = st.session_state["domain_summary"]
            all_serp = st.session_state["competitor_data"]

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Top Organic Competitors")
                org_df = pd.DataFrame(domain_summary["top_organic_domains"])
                if not org_df.empty:
                    st.dataframe(org_df, use_container_width=True)
                else:
                    st.info("No organic data found")

            with col2:
                st.markdown("#### Top Paid Competitors")
                paid_df = pd.DataFrame(domain_summary["top_paid_domains"])
                if not paid_df.empty:
                    st.dataframe(paid_df, use_container_width=True)
                else:
                    st.info("Low paid competition — good opportunity")

            st.divider()
            st.markdown("#### SERP Detail per Keyword")
            for result in all_serp:
                with st.expander(
                    f"🔍 {result['keyword']} — {result['total_organic']} organic results"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**Organic:**")
                        for r in result.get("organic_competitors", []):
                            st.write(f"- **{r['domain']}**")
                            if r.get("snippet"):
                                st.caption(r["snippet"][:100])
                    with c2:
                        st.markdown("**Paid Ads:**")
                        paid = result.get("paid_competitors", [])
                        if paid:
                            for r in paid:
                                st.write(f"- **{r['domain']}**")
                        else:
                            st.caption("No paid ads detected")

    # ------------------ TAB 5: EXPORT ------------------
    with tab5:
        st.markdown("### Export Options")

        col1, col2, col3 = st.columns(3)

        with col1:
            csv = filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download CSV",
                csv, "keywords.csv", "text/csv",
                use_container_width=True
            )

        with col2:
            ads_editor = filtered[["keyword"]].copy()
            ads_editor["Campaign"] = f"Campaign - {keyword.title()}"
            ads_editor["Ad Group"] = keyword.title()
            ads_editor["Match Type"] = filtered["intent"].map(
                {"BOFU": "Exact", "MOFU": "Phrase", "TOFU": "Broad"})
            ads_editor["Max CPC"] = filtered["cpc"]
            ads_editor["Status"] = "Enabled"
            ads_csv = ads_editor.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Google Ads Editor Format",
                ads_csv, "ads_editor_upload.csv", "text/csv",
                use_container_width=True
            )

        with col3:
            if st.button("📊 Export to Google Sheets", use_container_width=True):
                with st.spinner("Creating Google Sheet..."):
                    sheet_url = export_to_sheets(filtered, keyword)
                if sheet_url.startswith("http"):
                    st.success("Sheet created successfully!")
                    st.markdown(f"[Open Google Sheet]({sheet_url})")
                    st.info("Sheet has tabs: Keyword Research + Ads Editor Upload")
                else:
                    st.error(sheet_url)

# ------------------ EMPTY STATE ------------------
if not keyword:
    st.info("Enter a seed keyword above to discover high-intent keywords with AI-powered analysis")
