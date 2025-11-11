#!/usr/bin/env python3
"""
EU Data Act Compliance Dashboard - Streamlit Application
"""

import streamlit as st
import pandas as pd
import json
import subprocess
import plotly.express as px
from pathlib import Path
from datetime import datetime
import os

# --------------------------------------------------------------
# INITIAL CONFIGURATION
# --------------------------------------------------------------
st.set_page_config(
    page_title="EU Data Act Compliance Dashboard",
    page_icon="⚖️",
    layout="wide",
)

st.title("⚖️ EU Data Act Compliance Dashboard")
st.caption("Automated compliance monitoring under Regulation (EU) 2023/2854")

# --------------------------------------------------------------
# ENVIRONMENT DETECTION
# --------------------------------------------------------------
is_cloud = "STREAMLIT_SERVER_ROOT" in os.environ

base_path = Path(__file__).resolve().parent.parent
contracts_dir = base_path / "compliance-checks" / "contracts"
reports_dir = contracts_dir.parent / "compliance-reports"
example_report = base_path / "compliance-checks" / "example_report.json"
run_script_path = base_path / "compliance-checks" / "run_compliance_check.py"

# --------------------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------------------
def run_compliance_check(script_path: Path):
    """Execute compliance checker script and return console output."""
    result = subprocess.run(
        ["python3", str(script_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result


def load_latest_report(reports_dir: Path):
    """Load the most recent JSON report if available."""
    report_files = sorted(
        reports_dir.glob("*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )
    if not report_files:
        return None, None
    selected_report = report_files[0]
    with open(selected_report, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data, selected_report.name

# --------------------------------------------------------------
# SESSION STATE
# --------------------------------------------------------------
if "data" not in st.session_state:
    st.session_state.data = None
if "report_name" not in st.session_state:
    st.session_state.report_name = None
if "button_clicked" not in st.session_state:
    st.session_state.button_clicked = False

# --------------------------------------------------------------
# MAIN LOGIC
# --------------------------------------------------------------
if is_cloud:
    # 🌐 Cloud mode — use example data
    st.info("🌐 Running in Streamlit Cloud — using example data.")
    with open(example_report, "r", encoding="utf-8") as f:
        data = json.load(f)
    st.session_state.data = data
    st.session_state.report_name = "example_report.json"
    st.session_state.button_clicked = True
else:
    # 💻 Local mode — allow compliance checking
    st.sidebar.header("⚙️ Settings")

    if st.sidebar.button("▶️ Run Compliance Check"):
        with st.spinner("Running compliance checks... please wait ⏳"):
            result = run_compliance_check(run_script_path)
            st.sidebar.success("✅ Compliance check completed.")
            st.session_state.button_clicked = True

        # Load and store latest report
        data, report_name = load_latest_report(reports_dir)
        if data:
            st.session_state.data = data
            st.session_state.report_name = report_name

# --------------------------------------------------------------
# STOP IF NOTHING TO SHOW
# --------------------------------------------------------------
if not st.session_state.button_clicked or not st.session_state.data:
    st.stop()

# --------------------------------------------------------------
# MAIN DASHBOARD CONTENT
# --------------------------------------------------------------
data = st.session_state.data
report_name = st.session_state.report_name
timestamp = datetime.fromisoformat(data["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")

# SIDEBAR: CONTRACT NAVIGATION
st.sidebar.header("📑 Contracts")
contract_names = [r["contract_name"] for r in data["reports"]]
selected_contract = st.sidebar.selectbox(
    "Select a contract:",
    options=["📊 General Summary"] + contract_names,
    index=0,
)
st.sidebar.markdown("---")
st.sidebar.caption(f"🕒 Last updated: {timestamp}")
st.sidebar.caption(f"📁 Report: `{report_name}`")

# --------------------------------------------------------------
# GENERAL SUMMARY VIEW
# --------------------------------------------------------------
if selected_contract == "📊 General Summary":
    st.markdown(f"**📅 Report generated on:** `{timestamp}`")
    st.divider()

    st.header("🚨 Violations Summary")
    st.markdown(
        """
        This report evaluates compliance with selected **EU Data Act** provisions  
        under [Regulation (EU) 2023/2854](https://eur-lex.europa.eu/eli/reg/2023/2854/oj).

        The following key articles are monitored:
        - **Article 4(1)** – User Access Rights *(B2C)*  
        - **Article 8(6)** – Trade Secret Exceptions *(B2B)*  
        - **Article 19(2)(a)** – Competitive Use Prohibition *(B2G)*
        """
    )

    violations_data = []
    for r in data["reports"]:
        for art, check in r["checks"].items():
            if not check["compliant"]:
                for v in check["violations"]:
                    violations_data.append(
                        {
                            "Contract": r["contract_name"],
                            "Type": r["contract_type"],
                            "Article": art,
                            "Article Name": check["article_name"],
                            "Violation Type": v.get("violationType", "Unknown"),
                            "Details": v.get("details", ""),
                        }
                    )

    if violations_data:
        st.subheader("Detected Violations")
        violations_df = pd.DataFrame(violations_data)
        st.dataframe(violations_df, use_container_width=True)
    else:
        st.success("✅ All contracts comply with the monitored articles.")

    st.divider()

    st.header("📊 Compliance Overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Contracts", data["total_contracts"])
    col2.metric("Compliant Contracts", data["compliant_contracts"])
    col3.metric("Non-Compliant", data["total_contracts"] - data["compliant_contracts"])
    col4.metric("Total Violations", data["total_violations"])

    summary_df = pd.DataFrame(
        [
            {"Status": "Compliant", "Count": data["compliant_contracts"]},
            {
                "Status": "Non-Compliant",
                "Count": data["total_contracts"] - data["compliant_contracts"],
            },
        ]
    )
    fig = px.pie(
        summary_df,
        names="Status",
        values="Count",
        title="Overall Compliance Distribution",
        color="Status",
        color_discrete_map={"Compliant": "#2ecc71", "Non-Compliant": "#e74c3c"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.header("📋 Contract Overview")

    contracts = [
        {
            "Contract": r["contract_name"],
            "Type": r["contract_type"],
            "Violations": r["total_violations"],
            "Compliant": "✅ Yes" if r["overall_compliant"] else "❌ No",
        }
        for r in data["reports"]
    ]
    st.dataframe(pd.DataFrame(contracts), use_container_width=True)
    st.divider()

# --------------------------------------------------------------
# INDIVIDUAL CONTRACT VIEW
# --------------------------------------------------------------
else:
    contract = next(r for r in data["reports"] if r["contract_name"] == selected_contract)

    st.markdown(f"### 🧾 {contract['contract_name']}")
    colA, colB, colC = st.columns(3)
    colA.markdown(f"**Type:** `{contract['contract_type']}`")
    colC.markdown(f"**Violations:** `{contract['total_violations']}`")

    st.markdown("#### 📑 Article Checks")
    for article_id, check in contract["checks"].items():
        compliant = check["compliant"]
        article_url = f"https://eur-lex.europa.eu/eli/reg/2023/2854/oj#d1e{article_id.replace('.', '')}"
        header = (
            f"✅ [Article {article_id}: {check['article_name']}]({article_url})"
            if compliant
            else f"❌ [Article {article_id}: {check['article_name']}]({article_url})"
        )
        with st.expander(header, expanded=not compliant):
            if compliant:
                st.success("This article is compliant.")
            else:
                st.error(f"**{len(check['violations'])} violation(s) detected.**")
                for i, v in enumerate(check["violations"], start=1):
                    st.markdown(f"**Violation {i}: {v.get('violationType', 'Unknown')}**")
                    st.write(v.get("details", "No details provided."))

    st.divider()

st.caption("© 2025 - EU Data Act Compliance Toolkit | CC BY-SA 4.0 License")
