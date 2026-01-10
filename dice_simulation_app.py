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
                # RE-INITIALIZED: Ensuring all necessary keys exist
                st.session_state.user_db[user_id] = {
                    "password": pwd, 
                    "history": [], 
                    "stations": [], 
                    "raw_wip_data": []
                }
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

# Sidebar logic for resetting
st.sidebar.header(f"👤 Active: {current_user}")
if st.sidebar.button("🚪 Logout & Exit"):
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear Whole History"):
    user_record["history"] = []
    user_record["stations"] = []
    user_record["raw_wip_data"] = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Simulation Settings")
num_members = st.sidebar.number_input("Workstations", min_value=2, value=8)
num_days = st.sidebar.number_input("Days", min_value=1, value=100)

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

            for k, v in wip_buffers.items():
                st_wip_trend[k.replace("WIP_", "")].append(v)

            history.append({"Day": day, **wip_buffers.copy(), "Daily_Total_WIP": sum(wip_buffers.values()), "Day Wise Total FG": daily_fg_out})

        results_df = pd.DataFrame(history).set_index("Day")
        
        st.subheader("🎲 Table of Dice Rolls (Capacity)")
        st.dataframe(df_dice, use_container_width=True)

        scen_id = len(user_record["history"]) + 1
        st.subheader(f"🏁 Scenario #{scen_id} Results")
        c1, c2 = st.columns(2)
        c1.metric("Total Finished Goods", int(total_fg))
        c2.metric("Throughput Rate (TR)", round(total_fg / num_days, 2))
        # POINT 1: Total WIP (Sum) metric is removed from here.

        # Data Processing for Storage
        scen_label = f"Scenario #{scen_id}"
        avg_tr = total_fg / num_days
        avg_wip = results_df["Daily_Total_WIP"].mean()
        calc_lt = round(avg_wip / avg_tr, 2) if avg_tr > 0 else 0

        user_record["history"].append({
            "Scenarios": scen_label,
            "Days, Initial WIP & Dice Range": f"Days={num_days} | {dice_configs}",
            "Total Finished Goods": int(total_fg),
            "Throughput Rate (TR)": round(avg_tr, 2),
            "Lead Time (L)": calc_lt,
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(st_output[m]) for m in members]), 3)
        })

        for m in members:
            pair = next((k.replace("WIP_", "") for k in wip_keys if k.endswith(m)), m)
            if pair == "A": continue
            user_record["stations"].append({
                "Scenario": scen_label, "Station": f"Station {pair}", 
                "Tot Output": sum(st_output[m]), "Avg WIP": round(np.mean(st_wip_trend[pair]), 2),
                "Entropy Hi": round(calculate_entropy(st_output[m]), 3), "Interpretation": "Variable" if calculate_entropy(st_output[m]) > 2.4 else "Stable"
            })
            
        # POINT 3: Storing Raw Data for the new Table C
        raw_wip = results_df[[c for c in results_df.columns if len(c)==2 and c.isupper()]].copy()
        raw_wip["Scenario"] = scen_label
        user_record["raw_wip_data"].append(raw_wip.reset_index())
        st.success(f"Scenario {scen_id} saved!")

with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_record["history"]:
        # Table A
        st.subheader("Table A: Summary History")
        st.table(pd.DataFrame(user_record["history"]).set_index("Scenarios"))
        
        # Table B: Station Level
        st.markdown("---")
        st.subheader("Table B: Station-Level Flow Diagnostics")
        s_df = pd.DataFrame(user_record["stations"])
        # POINT 2: "Dice Range" removed from the metrics list
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

        # POINT 3: Table C - Multi-Period WIP Analysis
        st.markdown("---")
        st.subheader("Table C: Station-Wise WIP Aggregations")
        if user_record["raw_wip_data"]:
            combined_raw = pd.concat(user_record["raw_wip_data"])
            selected_scen = st.selectbox("Detailed WIP breakdown for:", combined_raw["Scenario"].unique())
            
            scen_data = combined_raw[combined_raw["Scenario"] == selected_scen].drop(columns="Scenario").set_index("Day")
            st_cols = scen_data.columns.tolist()

            c1, c2, c3 = st.tabs(["Daily WIP", "Weekly Avg (5 Days)", "Monthly Avg (20 Days)"])
            
            with c1:
                st.write("**Every Station Day-Wise WIP**")
                st.dataframe(scen_data, use_container_width=True)
            
            with c2:
                st.write("**Every Station Week-Wise Avg WIP**")
                df_reset = scen_data.reset_index()
                df_reset["Week"] = (df_reset["Day"] - 1) // 5 + 1
                st.dataframe(df_reset.groupby("Week")[st_cols].mean().round(2), use_container_width=True)
            
            with c3:
                st.write("**Every Station Month-Wise Avg WIP**")
                df_reset = scen_data.reset_index()
                df_reset["Month"] = (df_reset["Day"] - 1) // 20 + 1
                st.dataframe(df_reset.groupby("Month")[st_cols].mean().round(2), use_container_width=True)
    else:
        st.info("No recorded history found.")

with tab3:
    st.title("📖 Methodology")
    st.markdown("System architecture and movement logic overview.")
