import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io
from supabase import create_client, Client

# --- Page Configuration ---
st.set_page_config(page_title="Dice Simulation Platform", layout="wide")

# --- Supabase Initialization ---
# Ensure these are added in Streamlit Cloud -> Settings -> Secrets
try:
    url: str = st.secrets["SUPABASE_URL"]
    key: str = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("Supabase credentials not found. Please add them to Streamlit Secrets.")
    st.stop()

if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None

# --- Authentication Gateway ---
def auth_gateway():
    st.title("🔐 Cloud-Synced Production Gateway")
    auth_mode = st.radio("Select Mode:", ["Login", "Signup"], horizontal=True)
    user_id = st.text_input("User ID")
    pwd = st.text_input("Password", type="password")

    if auth_mode == "Signup":
        if st.button("Create Account"):
            # Check if user exists
            existing = supabase.table("users").select("*").eq("username", user_id).execute()
            if not existing.data:
                supabase.table("users").insert({"username": user_id, "password": pwd}).execute()
                st.success("Account created! Please switch to Login.")
            else:
                st.error("User ID already taken.")

    elif auth_mode == "Login":
        if st.button("Sign In"):
            res = supabase.table("users").select("*").eq("username", user_id).execute()
            if res.data and res.data[0]['password'] == pwd:
                st.session_state.authenticated_user = user_id
                st.rerun()
            else:
                st.error("Invalid Username or Password.")

if st.session_state.authenticated_user is None:
    auth_gateway()
    st.stop()

current_user = st.session_state.authenticated_user

# --- Sidebar: Simulation Settings ---
st.sidebar.header(f"👤 User: {current_user}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.markdown("---")
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
tab1, tab2 = st.tabs(["🚀 Live Operations Console", "📊 Strategic Performance Analytics"])

with tab1:
    st.title("🚀 Live Operations Console")
    
    if st.sidebar.button("▶ Run & Save Simulation"):
        # 1. Simulation logic
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

            history.append({
                "Day": day, 
                "Daily_Total_WIP": sum(wip_buffers.values()), 
                "Day Wise Total FG": daily_fg_out
            })

        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative FG"] = results_df["Day Wise Total FG"].cumsum()
        sum_total_wip = int(results_df["Daily_Total_WIP"].sum())

        # Display Metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Finished Goods", int(total_fg))
        c2.metric("Throughput (T)", round(total_fg / num_days, 2))
        c3.metric("Total WIP (Sum)", sum_total_wip)

        st.line_chart(results_df[["Daily_Total_WIP", "Cumulative FG"]])

        # --- Cloud Save ---
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}={v}" for k, v in initial_wip.items()])
        dice_info = ", ".join([f"{m}:{dice_configs[m][0]}-{dice_configs[m][1]}" for m in members])
        scen_label = f"Scenario_{pd.Timestamp.now().strftime('%H:%M:%S')}"

        # 1. Save Global History
        supabase.table("history").insert({
            "username": current_user,
            "scenario_name": scen_label,
            "config_summary": f"Days={num_days} | {wip_summary} | {dice_info}",
            "total_fg": int(total_fg),
            "throughput": round(total_fg / num_days, 2),
            "total_wip": sum_total_wip
        }).execute()

        # 2. Save Station Diagnostics (Skipping Station A)
        for m in members:
            pair = next((k.replace("WIP_", "") for k in wip_keys if k.endswith(m)), m)
            if pair == "A": continue
            
            h_val = calculate_entropy(st_output[m])
            supabase.table("stations").insert({
                "username": current_user,
                "scenario": scen_label,
                "station": f"Station {pair}",
                "dice_range": f"{dice_configs[m][0]}-{dice_configs[m][1]}",
                "tot_output": sum(st_output[m]),
                "avg_wip": round(np.mean(st_wip_trend[pair]), 2) if pair in st_wip_trend else 0,
                "entropy_hi": round(h_val, 3)
            }).execute()
            
        st.success("Simulation complete and saved to cloud!")

with tab2:
    st.title("📊 Strategic Performance Analytics")
    # Fetch from Supabase
    hist_res = supabase.table("history").select("*").eq("username", current_user).execute()
    stat_res = supabase.table("stations").select("*").eq("username", current_user).execute()

    if hist_res.data:
        df_a = pd.DataFrame(hist_res.data).drop(columns=['id', 'username'])
        st.subheader("Table A: Global Summary History")
        st.table(df_a)

        if stat_res.data:
            df_s = pd.DataFrame(stat_res.data)
            st.subheader("Table B: Station-Level Flow Diagnostics (Buffers Only)")
            # Pivot logic for Table B (Similar to your previous layout)
            st.dataframe(df_s.drop(columns=['id', 'username']), use_container_width=True)
