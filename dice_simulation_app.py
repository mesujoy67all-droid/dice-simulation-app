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
                st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": [], "buffer_history": []}
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

# --- Sidebar: User Controls & Settings ---
st.sidebar.header(f"👤 Active: {current_user}")
st.sidebar.header("Simulation Settings")

# Ensure station data structure exists
if "stations" not in user_record: user_record["stations"] = []
if "buffer_history" not in user_record: user_record["buffer_history"] = []

members_list = [chr(64 + i) for i in range(1, 9)] 
dice_configs = {m: st.sidebar.slider(f"Dice for {m}", 1, 20, (1, 6)) for m in members_list}

wip_keys_list = [f"WIP_{members_list[i]}{members_list[i+1]}" for i in range(len(members_list) - 1)]
initial_wip = {k: st.sidebar.number_input(k, min_value=0, value=4) for k in wip_keys_list}

num_days = st.sidebar.number_input("Days", min_value=1, value=1000)
num_members = st.sidebar.number_input("Workstations", min_value=2, value=8, max_value=8)

members = [chr(64 + i) for i in range(1, num_members + 1)]
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]

if st.sidebar.button("▶ Run & Save Simulation"):
    st.session_state.trigger_sim = True
else:
    st.session_state.trigger_sim = False

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear Whole History"):
    user_record["history"] = []
    user_record["stations"] = []
    user_record["buffer_history"] = []
    st.rerun()

if st.sidebar.button("🚪 Logout & Exit"):
    st.session_state.authenticated_user = None
    st.rerun()

# --- Utility Functions ---
def calculate_entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# --- Application Tabs ---
tab1, tab2, tab3 = st.tabs(["🚀 Live Operations Console", "📊 Strategic Performance Analytics", "📖 Methodology"])

with tab1:
    st.title("🚀 Live Operations Console")
    
    if st.session_state.get('trigger_sim', False):
        # 1. Capacity Generation
        dice_rolls = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
        df_dice = pd.DataFrame(dice_rolls)
        df_dice.index = range(1, num_days + 1)
        df_dice.index.name = "Day"

        # 2. Simulation Logic
        wip_buffers = {k: initial_wip[k] for k in wip_keys}
        history = []
        total_fg = 0
        st_output = defaultdict(list)
        st_wip_trend = defaultdict(list)
        pennies_movement_data = defaultdict(list)

        for day in df_dice.index:
            day_rolls = df_dice.loc[day]
            daily_fg_out = 0
            
            for i, m in enumerate(members):
                roll = day_rolls[m]
                
                if i == 0:
                    move_a = roll
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    wip_buffers[nxt] += move_a
                    st_output[m].append(move_a)
                    pennies_movement_data[m].append(move_a)
                elif i == len(members) - 1:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    move_last = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move_last
                    daily_fg_out = move_last
                    total_fg += move_last
                    st_output[m].append(move_last)
                    pennies_movement_data[m].append(move_last)
                else:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    move_mid = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move_mid
                    wip_buffers[nxt] += move_mid
                    st_output[m].append(move_mid)
                    pennies_movement_data[m].append(move_mid)

            for k, v in wip_buffers.items():
                st_wip_trend[k.replace("WIP_", "")].append(v)

            history.append({
                "Day": day, 
                **wip_buffers.copy(), 
                "Daily_Total_WIP": sum(wip_buffers.values()), 
                "Day Wise Total FG": daily_fg_out
            })

        # --- DISPLAY RESULTS ---
        st.subheader("🎲 Table of Dice Rolls (Capacity)")
        st.dataframe(df_dice, use_container_width=True)

        st.subheader("🪙 Day-wise Pennies Movement")
        df_pennies = pd.DataFrame(pennies_movement_data)
        df_pennies.index = range(1, num_days + 1)
        total_output_row = df_pennies.sum().to_frame().T
        total_output_row.index = ["TOTAL OUTPUT"]
        entropy_vals = {m: round(calculate_entropy(pennies_movement_data[m]), 3) for m in members}
        entropy_row = pd.DataFrame([entropy_vals])
        entropy_row.index = ["ENTROPY (H)"]
        df_pennies_final = pd.concat([df_pennies, total_output_row, entropy_row])
        st.dataframe(df_pennies_final, use_container_width=True)

        st.subheader("📦 Work-In-Progress (WIP) History")
        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative FG"] = results_df["Day Wise Total FG"].cumsum()
        st.dataframe(results_df, use_container_width=True)

        # --- LOGGING DATA ---
        scen_label = "Base-Run" if not user_record["history"] else f"Scenario #{len(user_record['history'])}"
        
        # Table A Log
        avg_throughput_rate = total_fg / num_days
        avg_total_wip_per_day = results_df["Daily_Total_WIP"].mean()
        user_record["history"].append({
            "Scenarios": scen_label,
            "Total Finished Goods": int(total_fg),
            "Throughput Rate (TR)": round(avg_throughput_rate, 2),
            "Avg WIP (W_avg)": round(avg_total_wip_per_day, 2),
            "Lead Time (L)": round(avg_total_wip_per_day / avg_throughput_rate, 2) if avg_throughput_rate > 0 else 0
        })

        # Table B Log (Stations A, B, C...)
        for m in members:
            h_val = calculate_entropy(st_output[m])
            user_record["stations"].append({
                "Scenario": scen_label, 
                "Station": f"Station {m}", 
                "Dice Range": f"{dice_configs[m][0]}-{dice_configs[m][1]}",
                "Tot Output": sum(st_output[m]), 
                "Entropy Hi": round(h_val, 3),
                "Interpretation": "Variable" if h_val > 2.4 else "Stable"
            })

        # Table C Log (Buffers AB, BC, CD...)
        for b_key, trend in st_wip_trend.items():
            user_record["buffer_history"].append({
                "Scenario": scen_label,
                "Buffer": b_key,
                "Daily Avg": np.mean(trend)
            })

with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_record["history"]:
        # TABLE A
        st.subheader("Table A: Summary History")
        st.table(pd.DataFrame(user_record["history"]).set_index("Scenarios"))

        # TABLE B (Stations)
        st.markdown("---")
        st.subheader("Table B: Station-Level Flow Diagnostics")
        s_df = pd.DataFrame(user_record["stations"])
        metrics_b = ["Dice Range", "Tot Output", "Entropy Hi", "Interpretation"]
        rows_b = []
        for scen in s_df['Scenario'].unique():
            for metric in metrics_b:
                row = {"Scenario": scen, "Metric": metric}
                for station in s_df['Station'].unique():
                    val = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == station)][metric].values
                    row[station] = val[0] if len(val) > 0 else "N/A"
                rows_b.append(row)
        st.table(pd.DataFrame(rows_b).set_index(["Scenario", "Metric"]))

        # TABLE C (Buffers)
        st.markdown("---")
        st.subheader("Table C: Temporal WIP Averages (By Buffer)")
        b_df = pd.DataFrame(user_record["buffer_history"])
        rows_c = []
        for scen in b_df['Scenario'].unique():
            for label, mult in [("Day wise Avg WIP", 1), ("Week wise Avg WIP", 5), ("Month wise Avg WIP", 20)]:
                row = {"Scenario": scen, "Time Metric": label}
                for buffer in b_df['Buffer'].unique():
                    val = b_df[(b_df['Scenario'] == scen) & (b_df['Buffer'] == buffer)]['Daily Avg'].values
                    row[buffer] = round(val[0] * mult, 2) if len(val) > 0 else 0.00
                rows_c.append(row)
        st.table(pd.DataFrame(rows_c).set_index(["Scenario", "Time Metric"]))

# --- PAGE 3: METHODOLOGY ---

with tab3:
    st.title("📖 Simulation Methodology & Logic")
    st.markdown("""
    This page pulls back the curtain on the simulation engine. It explains how **dependency** and **fluctuation** (the core of the Dice Game/Theory of Constraints) are calculated.
    """)

    st.header("🔄 The Flow Logic (Station A ➔ Buffer ➔ Station B)")
    st.markdown("### System Architecture")
    st.markdown("The simulation follows a linear production chain where each station is linked by an inventory buffer:")
    st.success("🏭 **Station A** (Source) $\longrightarrow$ 📦 **Buffer AB** (WIP) $\longrightarrow$ ⚙️ **Station B** (Processor) $\longrightarrow$ 📦 **Buffer BC** (WIP) $\longrightarrow$ ⚙️ **Station C**...")

    st.info("""
    **The Student's Guide to Movement Logic:**
    The actual work done is the **minimum** of your ability (Dice) and your availability (Buffer).
    """)

    st.latex(r"\text{Movement}_{B} = \min(\text{Dice Roll}_{B}, \text{Buffer}_{A \to B})")

    st.markdown("---")

    st.header("📊 Table A: Summary History")
    col1, col2 = st.columns(2)
    with col1:

        st.write("### Throughput Rate ($TR$)")
        st.latex(r"TR = \frac{\sum_{day=1}^{n} \text{Daily FG}}{n}")

        st.write("### Average System Entropy ($\bar{H}$)")
        st.latex(r"\bar{H} = \frac{1}{M} \sum_{i=1}^{M} H_i")

    with col2:
        st.write("### Lead Time ($L$)")
        st.markdown("Calculated based on average daily WIP levels relative to output rate.")
        st.latex(r"L = \frac{(\sum \text{Daily Total WIP} / n)}{TR}")

        st.write("### Entropy Spread ($\sigma H$)")
        st.latex(r"\sigma H = \sqrt{\frac{\sum (H_i - \bar{H})^2}{M}}")

    st.markdown("---")

    st.header("🔬 Table B: Station-Level Flow Diagnostics")
    st.latex(r"H = -\sum P(x) \log_2 P(x)")

    st.markdown("""
    **How to read Table B:**
    * **Avg WIP:** High WIP indicates this station is a **Bottleneck**.
    * **Entropy ($H_i$):**
        * **Stable (< 2.4):** Predictable output.
        * **Variable (≥ 2.4):** High 'jitter' or chaos.
    """)








