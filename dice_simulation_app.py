import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# --- Page Configuration ---
st.set_page_config(page_title="Dice Simulation Platform", layout="wide")

# --- User Database Simulation ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = {} 

if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None

# --- Authentication Gateway ---
def auth_gateway():
    st.title("🔐 Production Simulation Gateway")
    auth_mode = st.radio("Select Mode:", ["Login", "Signup"], horizontal=True)
    
    user_id = st.text_input("User ID (Unique Username)")
    pwd = st.text_input("Password", type="password")
    
    if auth_mode == "Signup":
        st.info("Your User ID must be unique. You can only sign up once.")
        if st.button("Create Account"):
            if user_id in st.session_state.user_db:
                st.error(f"User ID '{user_id}' is already taken.")
            elif user_id and pwd:
                st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": []}
                st.success("Account created! Please switch to Login mode.")
            else:
                st.warning("Fields cannot be empty.")
                
    elif auth_mode == "Login":
        if st.button("Sign In"):
            if user_id in st.session_state.user_db:
                if st.session_state.user_db[user_id]["password"] == pwd:
                    st.session_state.authenticated_user = user_id
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            else:
                st.error("User ID not found.")

if st.session_state.authenticated_user is None:
    auth_gateway()
    st.stop()

# --- Access Current User's Data ---
current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]

# --- Sidebar: User Controls ---
st.sidebar.header(f"👤 Active: {current_user}")
if st.sidebar.button("🚪 Logout & Exit"):
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Data Management")
if st.sidebar.button("🗑️ Clear Whole History"):
    user_record["history"] = []
    user_record["stations"] = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Simulation Settings")
num_members = st.sidebar.number_input("Workstations", min_value=2, value=8)
num_days = st.sidebar.number_input("Days", min_value=1, value=1000)

members = [chr(64 + i) for i in range(1, num_members + 1)]
dice_configs = {m: st.sidebar.slider(f"Dice for {m}", 1, 20, (1, 6)) for m in members}
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]

initial_wip = {k: st.sidebar.number_input(k, min_value=0, value=4) for k in wip_keys}

def calculate_entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# --- Application Tabs ---
tab1, tab2, tab3 = st.tabs(["🚀 Live Operations Console", "📊 Strategic Performance Analytics", "📖 Methodology"])

with tab1:
    st.title("🚀 Live Operations Console")
    
    if st.sidebar.button("▶ Run & Save Simulation"):
        # 1. Capacity Generation
        dice_rolls = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
        df_dice = pd.DataFrame(dice_rolls)
        df_dice.index = range(1, num_days + 1)
        df_dice.index.name = "Day"

        # 2. Simulation Logic
        wip_buffers = initial_wip.copy()
        history = []
        total_fg = 0
        st_output = defaultdict(list)
        st_wip_trend = defaultdict(list)

        for day in df_dice.index:
            day_rolls = df_dice.loc[day]
            daily_fg_out = 0
            for i, m in enumerate(members):
                roll = day_rolls[m]
                if i == 0:
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    wip_buffers[nxt] += roll
                    st_output[m].append(roll)
                elif i == len(members) - 1:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    daily_fg_out = move
                    total_fg += move
                    st_output[m].append(move)
                else:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    wip_buffers[nxt] += move
                    st_output[m].append(move)

            for k, v in wip_buffers.items():
                st_wip_trend[k.replace("WIP_", "")].append(v)

            history.append({
                "Day": day, 
                **wip_buffers.copy(), 
                "Daily_Total_WIP": sum(wip_buffers.values()), 
                "Day Wise Total FG": daily_fg_out
            })

        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative FG"] = results_df["Day Wise Total FG"].cumsum()
        sum_total_wip = int(results_df["Daily_Total_WIP"].sum())

        st.subheader("🎲 Table of Dice Rolls (Capacity)")
        st.dataframe(df_dice, use_container_width=True)

        st.subheader("📦 Work-In-Progress (WIP) History")
        st.dataframe(results_df, use_container_width=True)

        scen_id = len(user_record["history"]) + 1
        st.subheader(f"🏁 Scenario #{scen_id} Results")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Finished Goods", int(total_fg))
        c2.metric("Throughput Rate (TR)", round(total_fg / num_days, 2))
        c3.metric("Total WIP (Sum)", sum_total_wip)

        st.subheader("📈 Performance Trends")
        st.line_chart(results_df[["Daily_Total_WIP", "Cumulative FG"]])

        # --- Logging Logic ---
        scen_label = "Base-Run" if not user_record["history"] else f"Scenario #{len(user_record['history'])}"
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}={v}" for k, v in initial_wip.items()])
        dice_info = ", ".join([f"{m}:{dice_configs[m][0]}-{dice_configs[m][1]}" for m in members])
        
        user_record["history"].append({
            "Scenarios": scen_label,
            "Days, Initial WIP & Dice Range": f"Days={num_days} | {wip_summary} | {dice_info}",
            "Total Finished Goods": int(total_fg),
            "Throughput Rate (TR)": round(total_fg / num_days, 2),
            "Total WIP (W)": sum_total_wip,
            "Lead Time (L = W / TR)": round(sum_total_wip / (total_fg/num_days), 2) if total_fg > 0 else 0,
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(st_output[m]) for m in members]), 3),
            "Entropy Spread σH": round(np.std([calculate_entropy(st_output[m]) for m in members]), 3)
        })

        for m in members:
            pair = next((k.replace("WIP_", "") for k in wip_keys if k.endswith(m)), m)
            if pair == "A":
                continue
                
            h_val = calculate_entropy(st_output[m])
            user_record["stations"].append({
                "Scenario": scen_label, "Station": f"Station {pair}", "Dice Range": f"{dice_configs[m][0]}-{dice_configs[m][1]}",
                "Tot Output": sum(st_output[m]), "Avg WIP": round(np.mean(st_wip_trend[pair]), 2) if pair in st_wip_trend else 0,
                "Entropy Hi": round(h_val, 3), "Interpretation": "Variable" if h_val > 2.4 else "Stable"
            })

with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_record["history"]:
        df_table_a = pd.DataFrame(user_record["history"]).set_index("Scenarios")
        
        s_df = pd.DataFrame(user_record["stations"])
        metrics = ["Dice Range", "Tot Output", "Avg WIP", "Entropy Hi", "Interpretation"]
        rows = []
        for scen in s_df['Scenario'].unique():
            for i, metric in enumerate(metrics):
                row_data = {"Scenario": scen if i == 0 else "", "Metric": metric}
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    row_data[s_label] = subset[metric].values[0] if not subset.empty else ""
                rows.append(row_data)
        
        df_table_b = pd.DataFrame(rows).set_index(["Scenario", "Metric"])

        st.subheader("Table A: Summary History")
        st.table(df_table_a)
        
        st.markdown("---")
        st.subheader("Table B: Station-Level Flow Diagnostics (Buffers Only)")
        st.table(df_table_b)

        st.markdown("---")
        st.subheader("📥 Export Analytics")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_table_a.to_excel(writer, sheet_name='Summary History')
            df_table_b.reset_index().to_excel(writer, sheet_name='Station Diagnostics', index=False)
        excel_data = output.getvalue()
        st.download_button(label="Download Analytics as Excel", data=excel_data, file_name=f"Simulation_Analytics_{current_user}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("No recorded history found for this User ID.")

# --- PAGE 3: METHODOLOGY ---
with tab3:
    st.title("📖 Simulation Methodology & Logic")
    st.markdown("""
    This page pulls back the curtain on the simulation engine. It explains how **dependency** and **fluctuation** (the core of the Dice Game/Theory of Constraints) are calculated.
    """)

    # --- Section 1: Visual Process Flow ---
    st.header("🔄 The Flow Logic (Station A ➔ Buffer ➔ Station B)")
    
    st.markdown("### System Architecture")
    st.markdown("The simulation follows a linear production chain where each station is linked by an inventory buffer:")
    
    # Visualizing the chain for students
    st.success("🏭 **Station A** (Source) $\longrightarrow$ 📦 **Buffer AB** (WIP) $\longrightarrow$ ⚙️ **Station B** (Processor) $\longrightarrow$ 📦 **Buffer BC** (WIP) $\longrightarrow$ ⚙️ **Station C**...")

    

    st.info("""
    **The Student's Guide to Movement Logic:**
    Imagine a relay race. Even if the second runner is the fastest in the world (high dice roll), they cannot run if the first runner hasn't handed them the baton (low buffer). 
    
    **The rule is always:** The actual work done is the **minimum** of your ability (Dice) and your availability (Buffer).
    """)

    st.latex(r"\text{Movement}_{B} = \min(\text{Dice Roll}_{B}, \text{Buffer}_{A \to B})")

    st.markdown("---")

    # --- Section 2: Table A Calculations ---
    st.header("📊 Table A: Summary History")
    st.markdown("These formulas aggregate the daily data into strategic performance indicators.")

    col1, col2 = st.columns(2)
    with col1:
        st.write("### Throughput Rate ($TR$)")
        st.markdown("The average rate at which the system generates finished goods.")
        st.latex(r"TR = \frac{\sum_{day=1}^{n} \text{Daily FG}}{n}")

        st.write("### Average System Entropy ($\bar{H}$)")
        st.markdown("The mean level of uncertainty across the entire plant.")
        st.latex(r"\bar{H} = \frac{1}{M} \sum_{i=1}^{M} H_i")
        st.caption("Where M is the number of workstations.")
        
    with col2:
        st.write("### Lead Time ($L$)")
        st.markdown("The average time a unit takes to travel through the entire plant.")
        st.latex(r"L = \frac{\text{Sum of Daily Total WIP}}{TR}")
        st.caption("Derived from Little's Law.")

        st.write("### Entropy Spread ($\sigma H$)")
        st.markdown("Measures the imbalance or variance in stability between stations.")
        st.latex(r"\sigma H = \sqrt{\frac{\sum (H_i - \bar{H})^2}{M}}")

    st.markdown("---")

    # --- Section 3: Table B Calculations ---
    st.header("🔬 Table B: Station-Level Flow Diagnostics")
    st.markdown("""
    This table measures **Entropy ($H$)**, which quantifies the uncertainty or 'chaos' in a station's output.
    """)
    
    

    st.latex(r"H = -\sum P(x) \log_2 P(x)")

    st.markdown("""
    **How to read Table B:**
    * **Avg WIP:** High WIP indicates this station is a **Bottleneck**—it's where work piles up because this station cannot keep up with the one before it.
    * **Entropy ($H_i$):**
        * **Stable (< 2.4):** Predictable output. The station is consistent.
        * **Variable (≥ 2.4):** High 'jitter.' The station is chaotic, making it hard to predict flow.
    """)

    st.info("""
    **Note on 'Interpretation':** The 'Variable' vs 'Stable' tag is a diagnostic to help you identify which station's dice range needs to be tightened (standardized) to improve flow.
    """)
