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

# --- Sidebar: User Controls & Settings ---
st.sidebar.header(f"👤 Active: {current_user}")
st.sidebar.header("Simulation Settings")

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
        
        # --- NEW: Dictionary to store the specific Pennies Movement ---
        pennies_movement_data = defaultdict(list)

        for day in df_dice.index:
            day_rolls = df_dice.loc[day]
            daily_fg_out = 0
            
            for i, m in enumerate(members):
                roll = day_rolls[m]
                
                if i == 0:
                    # Station A logic: Move always equals Dice Roll
                    move_a = roll
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    wip_buffers[nxt] += move_a
                    st_output[m].append(move_a)
                    pennies_movement_data[m].append(move_a)
                elif i == len(members) - 1:
                    # Last Station logic
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    move_last = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move_last
                    daily_fg_out = move_last
                    total_fg += move_last
                    st_output[m].append(move_last)
                    pennies_movement_data[m].append(move_last)
                else:
                    # Middle Station logic
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
        
        # 1. Dice Rolls (Original)
        st.subheader("🎲 Table of Dice Rolls (Capacity)")
        st.dataframe(df_dice, use_container_width=True)

        # 2. Pennies Movement (NEW TABLE)
        st.subheader("🪙 Day-wise Pennies Movement")
        df_pennies = pd.DataFrame(pennies_movement_data)
        df_pennies.index = range(1, num_days + 1)
        df_pennies.index.name = "Day"
        st.dataframe(df_pennies, use_container_width=True)

        # 3. WIP History
        st.subheader("📦 Work-In-Progress (WIP) History")
        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative FG"] = results_df["Day Wise Total FG"].cumsum()
        sum_total_wip = int(results_df["Daily_Total_WIP"].sum())
        st.dataframe(results_df, use_container_width=True)

        # Metrics and Logging (Simplified for clarity)
        st.markdown("---")
        c1, c2 = st.columns(2)
        c1.metric("Total Finished Goods", int(total_fg))
        c2.metric("Throughput Rate", round(total_fg / num_days, 2))
        
        # --- Save to history (unchanged from original logic) ---
        scen_label = "Base-Run" if not user_record["history"] else f"Scenario #{len(user_record['history'])}"
        user_record["history"].append({
            "Scenarios": scen_label,
            "Total Finished Goods": int(total_fg),
            "Throughput Rate (TR)": round(total_fg / num_days, 2),
            "Total WIP (W)": sum_total_wip,
            "Lead Time (L = Avg WIP / TR)": round((sum_total_wip/num_days)/(total_fg/num_days), 2) if total_fg > 0 else 0,
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(st_output[m]) for m in members]), 3),
            "Entropy Spread σH": round(np.std([calculate_entropy(st_output[m]) for m in members]), 3)
        })

        for m in members:
            pair = next((k.replace("WIP_", "") for k in wip_keys if k.endswith(m)), m)
            if pair == "A": continue
            h_val = calculate_entropy(st_output[m])
            user_record["stations"].append({
                "Scenario": scen_label, "Station": f"Station {pair}", "Dice Range": f"{dice_configs[m][0]}-{dice_configs[m][1]}",
                "Tot Output": sum(st_output[m]), "Avg WIP": round(np.mean(st_wip_trend[pair]), 2) if pair in st_wip_trend else 0,
                "Entropy Hi": round(h_val, 3), "Interpretation": "Variable" if h_val > 2.4 else "Stable"
            })

with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_record["history"]:
        st.table(pd.DataFrame(user_record["history"]).set_index("Scenarios"))
    else:
        st.info("No recorded history found.")

with tab3:
    st.title("📖 Methodology")
    st.markdown("Explanation of the linear flow logic and the minimum function used for WIP movement.")
