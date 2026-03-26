import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from campaign_builder import (
    build_campaign_structure,
    campaign_to_ads_editor_format,
    export_campaign_to_sheets
)

load_dotenv()

st.set_page_config(page_title="Campaign Builder", page_icon="🏗️", layout="wide")

st.title("🏗️ Campaign Template Builder")
st.caption("Build complete Google Ads campaign structures powered by AI")
st.divider()

# ------------------ SESSION STATE ------------------
if "campaign_structure" not in st.session_state:
    st.session_state["campaign_structure"] = None

# ------------------ CHECK FOR KEYWORDS ------------------
if "data" not in st.session_state or not st.session_state.get("data"):
    st.warning("No keyword data found. Go to Keyword Research first and search for keywords.")
    st.stop()

df = pd.DataFrame(st.session_state["data"])

# ------------------ CAMPAIGN SETTINGS ------------------
st.markdown("### Campaign Settings")

col1, col2, col3 = st.columns(3)

with col1:
    seed_keyword = st.text_input("Campaign Topic",
                                  value=df["keyword"].iloc[0].split()[0] if len(df) > 0 else "")
    campaign_goal = st.selectbox("Campaign Goal", [
        "conversions", "leads", "website traffic",
        "brand awareness", "app installs"
    ])

with col2:
    daily_budget = st.number_input("Daily Budget (USD)", value=50.0, min_value=5.0)
    target_country = st.selectbox("Target Country", ["IN", "US", "GB", "AU", "CA", "SG"])

with col3:
    landing_page = st.text_input("Landing Page URL", placeholder="https://yoursite.com/insurance")
    max_keywords_per_group = st.number_input("Max Keywords per Ad Group", value=10, min_value=3)

st.divider()

# ------------------ KEYWORD SELECTION ------------------
st.markdown("### Select Keywords to Include")

filter_intent = st.multiselect(
    "Filter by Intent",
    ["BOFU", "MOFU", "TOFU"],
    default=["BOFU", "MOFU"]
)

if filter_intent and "intent" in df.columns:
    selected_df = df[df["intent"].isin(filter_intent)].copy()
else:
    selected_df = df.copy()

if "opportunity_score" in selected_df.columns:
    selected_df = selected_df.sort_values("opportunity_score", ascending=False)

st.caption(f"Using top {min(50, len(selected_df))} keywords from your research")
st.dataframe(
    selected_df[["keyword", "volume", "cpc", "intent", "opportunity_score"]].head(50)
    if "opportunity_score" in selected_df.columns
    else selected_df[["keyword", "volume", "cpc", "intent"]].head(50),
    use_container_width=True,
    height=200
)

st.divider()

# ------------------ BUILD BUTTON ------------------
if st.button("🏗️ Build Campaign Structure", use_container_width=True):
    with st.spinner("AI is building your campaign structure..."):
        structure = build_campaign_structure(
            keywords_data=selected_df.head(50).to_dict("records"),
            seed_keyword=seed_keyword,
            campaign_goal=campaign_goal,
            daily_budget=daily_budget,
            target_country=target_country
        )
        st.session_state["campaign_structure"] = structure

    if "error" in structure:
        st.error(f"Error: {structure['error']}")
    else:
        st.success("Campaign structure built successfully!")

# ------------------ DISPLAY CAMPAIGN ------------------
if st.session_state.get("campaign_structure") and "error" not in st.session_state["campaign_structure"]:
    structure = st.session_state["campaign_structure"]
    campaign = structure.get("campaign", {})
    ad_groups = structure.get("ad_groups", [])

    st.divider()

    # Campaign summary
    st.markdown("### Campaign Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Campaign Name", campaign.get("name", "")[:20])
    c2.metric("Bid Strategy", campaign.get("bid_strategy", "")[:15])
    c3.metric("Daily Budget", f"${campaign.get('daily_budget', 0)}")
    c4.metric("Ad Groups", len(ad_groups))

    # Budget allocation
    allocation = structure.get("budget_allocation", {})
    if allocation:
        st.markdown("#### Budget Allocation by Intent")
        ac1, ac2, ac3 = st.columns(3)
        ac1.metric("BOFU (High Intent)", f"{allocation.get('BOFU', 0)}%")
        ac2.metric("MOFU (Research)", f"{allocation.get('MOFU', 0)}%")
        ac3.metric("TOFU (Awareness)", f"{allocation.get('TOFU', 0)}%")

    # Recommendations
    recs = structure.get("recommendations", [])
    if recs:
        st.markdown("#### AI Recommendations")
        for rec in recs:
            st.write(f"- {rec}")

    st.divider()

    # Campaign negatives
    camp_negs = structure.get("campaign_negative_keywords", [])
    if camp_negs:
        st.markdown("#### Campaign Negative Keywords")
        st.code(" | ".join(camp_negs))

    st.divider()

    # Ad groups detail
    st.markdown("### Ad Groups")
    intent_tabs = st.tabs([f"{ag.get('intent', '')} — {ag.get('name', '')}" for ag in ad_groups])

    for i, ag in enumerate(ad_groups):
        with intent_tabs[i]:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Keywords:**")
                kw_data = []
                for kw in ag.get("keywords", []):
                    kw_data.append({
                        "Keyword": kw.get("keyword", ""),
                        "Match Type": kw.get("match_type", ""),
                        "Max CPC": ag.get("max_cpc", 0)
                    })
                if kw_data:
                    st.dataframe(pd.DataFrame(kw_data), use_container_width=True)

                st.markdown("**Negative Keywords:**")
                negs = ag.get("negative_keywords", [])
                if negs:
                    st.code(" | ".join(negs))

            with col2:
                st.markdown("**Ad Copy:**")
                for j, ad in enumerate(ag.get("ads", []), 1):
                    with st.expander(f"Ad {j} — {ad.get('headline_1', '')[:30]}"):
                        st.write(f"**H1:** {ad.get('headline_1', '')} ({len(ad.get('headline_1', ''))} chars)")
                        st.write(f"**H2:** {ad.get('headline_2', '')} ({len(ad.get('headline_2', ''))} chars)")
                        st.write(f"**H3:** {ad.get('headline_3', '')} ({len(ad.get('headline_3', ''))} chars)")
                        st.write(f"**D1:** {ad.get('description_1', '')} ({len(ad.get('description_1', ''))} chars)")
                        st.write(f"**D2:** {ad.get('description_2', '')} ({len(ad.get('description_2', ''))} chars)")
                        st.write(f"**URL:** {ad.get('final_url', '')}")

    st.divider()

    # Export section
    st.markdown("### Export Campaign")
    dfs = campaign_to_ads_editor_format(structure)

    ec1, ec2, ec3, ec4 = st.columns(4)

    with ec1:
        kw_csv = dfs["keywords"].to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Keywords CSV",
            kw_csv, "campaign_keywords.csv", "text/csv",
            use_container_width=True
        )

    with ec2:
        ads_csv = dfs["ads"].to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Ads CSV",
            ads_csv, "campaign_ads.csv", "text/csv",
            use_container_width=True
        )

    with ec3:
        neg_csv = dfs["negatives"].to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Negatives CSV",
            neg_csv, "campaign_negatives.csv", "text/csv",
            use_container_width=True
        )

    with ec4:
        if st.button("📊 Export All to Sheets", use_container_width=True):
            from sheets_export import get_sheets_client
            with st.spinner("Exporting to Google Sheets..."):
                client = get_sheets_client()
                sheet_id = os.getenv("SHEETS_MASTER_ID")
                url = export_campaign_to_sheets(structure, client, sheet_id)
            if url.startswith("http"):
                st.success("Exported!")
                st.markdown(f"[Open Sheet]({url})")
            else:
                st.error(url)
