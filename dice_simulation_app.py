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
                st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": [], "raw_data": []}
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

current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]

# --- Sidebar ---
st.sidebar.header(f"👤 Active: {current_user}")
if st.sidebar.button("🚪 Logout & Exit"):
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Data Management")
if st.sidebar.button("🗑️ Clear Whole History"):
    user_record["history"] = []
    user_record["stations"] = []
    user_record["raw_data"] = []
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

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["🚀 Live Operations Console", "📊 Strategic Performance Analytics", "📖 Methodology"])

with tab1:
    st.title("🚀 Live Operations Console")
    
    if st.sidebar.button("▶ Run & Save Simulation"):
        dice_rolls = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
        df_dice = pd.DataFrame(dice_rolls)
        df_dice.index = range(1, num_days + 1)

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

            day_snapshot = {"Day": day, **wip_buffers.copy()}
            history.append(day_snapshot)
            for k, v in wip_buffers.items():
                st_wip_trend[k.replace("WIP_", "")].append(v)

        results_df = pd.DataFrame(history).set_index("Day")
        scen_label = "Base-Run" if not user_record["history"] else f"Scenario #{len(user_record['history'])}"
        
        # Save Raw Data for Table C
        raw_entry = results_df.copy()
        raw_entry['Scenario'] = scen_label
        user_record["raw_data"].append(raw_entry)

        # Logging Summaries
        avg_tr = total_fg / num_days
        sum_total_wip = results_df.filter(like="WIP_").sum(axis=1).sum()
        avg_wip_val = sum_total_wip / num_days
        l_time = round(avg_wip_val / avg_tr, 2) if avg_tr > 0 else 0

        user_record["history"].append({
            "Scenarios": scen_label,
            "Days, Initial WIP & Dice Range": f"Days={num_days} | {dice_configs}",
            "Total Finished Goods": int(total_fg),
            "Throughput Rate (TR)": round(avg_tr, 2),
            "Total WIP (W)": int(sum_total_wip),
            "Lead Time (L = Avg WIP / TR)": l_time,
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(st_output[m]) for m in members]), 3),
            "Entropy Spread σH": round(np.std([calculate_entropy(st_output[m]) for m in members]), 3)
        })

        for m in members:
            pair = next((k.replace("WIP_", "") for k in wip_keys if k.endswith(m)), m)
            if pair == "A": continue
            user_record["stations"].append({
                "Scenario": scen_label, "Station": f"Station {pair}", 
                "Tot Output": sum(st_output[m]), "Avg WIP": round(np.mean(st_wip_trend[pair]), 2) if pair in st_wip_trend else 0,
                "Entropy Hi": round(calculate_entropy(st_output[m]), 3), "Interpretation": "Variable" if calculate_entropy(st_output[m]) > 2.4 else "Stable"
            })
        st.success(f"Simulation {scen_label} complete and saved!")

with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_record["history"]:
        # Table A
        st.subheader("Table A: Summary History")
        st.table(pd.DataFrame(user_record["history"]).set_index("Scenarios"))
        
        # Table B
        st.subheader("Table B: Station-Level Flow Diagnostics")
        s_df = pd.DataFrame(user_record["stations"])
        metrics = ["Tot Output", "Avg WIP", "Entropy Hi", "Interpretation"]
        rows = []
        for scen in s_df['Scenario'].unique():
            for i, metric in enumerate(metrics):
                row_data = {"Scenario": scen if i == 0 else "", "Metric": metric}
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    row_data[s_label] = subset[metric].values[0] if not subset.empty else ""
                rows.append(row_data)
        st.table(pd.DataFrame(rows).set_index(["Scenario", "Metric"]))

        # Table C: Station Wise, Day/Week/Month WIP
        st.markdown("---")
        st.subheader("Table C: Multi-Interval WIP Diagnostics")
        
        if user_record["raw_data"]:
            all_raw = pd.concat(user_record["raw_data"])
            selected_scen = st.selectbox("Select Scenario for Time-Series Analysis", all_raw['Scenario'].unique())
            df_scen = all_raw[all_raw['Scenario'] == selected_scen].drop(columns=['Scenario'])
            
            # Formatting Columns for Table C
            wip_cols = [c for c in df_scen.columns if "WIP_" in c]
            
            # 1. Day Wise (Last 10 days as sample)
            st.write("**Daily WIP Snapshot (Recent Days)**")
            st.dataframe(df_scen[wip_cols].tail(10))

            # Aggregations
            df_scen['Week'] = (df_scen.index - 1) // 5 + 1
            df_scen['Month'] = (df_scen.index - 1) // 20 + 1
            
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                st.write("**Weekly Average WIP (5-Day Cycles)**")
                st.dataframe(df_scen.groupby('Week')[wip_cols].mean().round(2))
            
            with col_w2:
                st.write("**Monthly Average WIP (20-Day Cycles)**")
                st.dataframe(df_scen.groupby('Month')[wip_cols].mean().round(2))

with tab3:
    st.title("📖 Methodology")
    st.markdown("""
    **Time Interval Logic:**
    * **1 Week:** 5 Production Days.
    * **1 Month:** 20 Production Days (4 Weeks).
    
    The WIP shown in Table C reflects the **Average Inventory** held within that period at each specific buffer.
    """)
