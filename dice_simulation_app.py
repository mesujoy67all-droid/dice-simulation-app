import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict

# --- Page Configuration ---
st.set_page_config(page_title="Dice Simulation Platform", layout="wide")

# --- Persistent Data Storage (Simulation of a Database) ---
# In a real app, this would be a database or a file. 
# Here we use st.session_state to track "Registered Users" for the current browser session.
if 'user_db' not in st.session_state:
    st.session_state.user_db = {}  # Format: {username: {"password": pwd, "history": [], "stations": []}}

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# --- Login Logic ---
def login_page():
    st.title("🔐 Production Simulation Login")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Login / Create Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Access Simulation"):
            if username and password:
                if username in st.session_state.user_db:
                    # Check Password
                    if st.session_state.user_db[username]["password"] == password:
                        st.session_state.current_user = username
                        st.success(f"Welcome back, {username}!")
                        st.rerun()
                    else:
                        st.error("Incorrect password.")
                else:
                    # Create New User
                    st.session_state.user_db[username] = {
                        "password": password,
                        "history": [],
                        "stations": []
                    }
                    st.session_state.current_user = username
                    st.success(f"Account created for {username}!")
                    st.rerun()
            else:
                st.warning("Please enter both username and password.")

if st.session_state.current_user is None:
    login_page()
    st.stop()

# --- Load User Data ---
user_data = st.session_state.user_db[st.session_state.current_user]

# --- Sidebar: Simulation Settings & User Control ---
st.sidebar.header(f"👤 User: {st.session_state.current_user}")

if st.sidebar.button("🚪 Logout"):
    st.session_state.current_user = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Control Panel")

# Reset specific to this user
if st.sidebar.button("🗑️ Start New Session (Clear History)"):
    user_data["history"] = []
    user_data["stations"] = []
    st.success("History cleared for this session.")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Simulation Settings")
num_members = st.sidebar.number_input("Number of Workstations", min_value=2, value=7, step=1)
num_days = st.sidebar.number_input("Number of Days", min_value=1, value=25, step=1)

members = [chr(64 + i) for i in range(1, num_members + 1)]

st.sidebar.subheader("Dice Range per Member")
dice_configs = {}
for m in members:
    low, high = st.sidebar.slider(f"Dice range for {m}", 1, 20, (1, 6))
    dice_configs[m] = (low, high)

st.sidebar.subheader("Initial WIP Buffers")
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]
initial_wip = {}
for key in wip_keys:
    initial_wip[key] = st.sidebar.number_input(f"{key}", min_value=0, value=4, step=1)

def calculate_entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# --- Navigation Tabs ---
tab1, tab2 = st.tabs(["🚀 Live Operations Console", "📊 Strategic Performance Analytics"])

with tab1:
    st.title("🚀 Live Operations Console")

    if st.sidebar.button("▶ Run Simulation & Record"):
        # 1. Capacity Generation
        dice_rolls = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
        df_dice = pd.DataFrame(dice_rolls)
        df_dice.index = range(1, num_days + 1)
        df_dice.index.name = "Day"

        # 2. Logic Execution
        wip_buffers = initial_wip.copy()
        history = []
        total_finished_goods = 0
        station_output_data = defaultdict(list)
        buffer_levels_over_time = defaultdict(list)

        for day in df_dice.index:
            day_rolls = df_dice.loc[day]
            daily_fg = 0
            for i, m in enumerate(members):
                roll = day_rolls[m]
                if i == 0:
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    wip_buffers[nxt] += roll
                    station_output_data[m].append(roll)
                elif i == len(members) - 1:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    daily_fg = move
                    total_finished_goods += move
                    station_output_data[m].append(move)
                else:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    wip_buffers[nxt] += move
                    station_output_data[m].append(move)

            for key, val in wip_buffers.items():
                pair = key.replace("WIP_", "")
                buffer_levels_over_time[pair].append(val)

            day_record = {"Day": day, **wip_buffers.copy(), "Daily_Total_WIP": sum(wip_buffers.values()), "Daily_FG": daily_fg}
            history.append(day_record)

        results_df = pd.DataFrame(history).set_index("Day")

        # --- Page 1 Display Order ---
        st.subheader("🎲 Table of Dice Rolls (Capacity)")
        st.dataframe(df_dice, use_container_width=True)

        st.subheader("📦 Work-In-Progress (WIP) History")
        st.dataframe(results_df.drop(columns=["Daily_FG"]), use_container_width=True)

        scen_count = len(user_data["history"]) + 1
        st.subheader(f"🏁 Current Results: Scenario #{scen_count}")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Finished Goods", int(total_finished_goods))
        m_col2.metric("Mean Throughput (T)", round(total_finished_goods / num_days, 2))
        m_col3.metric("Avg Total WIP (W)", round(results_df["Daily_Total_WIP"].mean(), 2))

        st.subheader("📈 Performance Trends")
        st.line_chart(results_df[["Daily_Total_WIP", "Daily_FG"]])

        # --- Logging for Page 2 ---
        scen_label = "Base-4" if not user_data["history"] else f"Scenario #{len(user_data['history'])}"
        wip_val = list(initial_wip.values())[0] if initial_wip else 0
        dice_str = ", ".join([f"{m}:{dice_configs[m][0]}-{dice_configs[m][1]}" for m in members])
        combined_config = f"WIP={wip_val} | {dice_str}"

        user_data["history"].append({
            "Scenarios": scen_label,
            "Initial WIP & Dice Range": combined_config,
            "Total Finished Goods": int(total_finished_goods),
            "Mean Throughput (T)": round(total_finished_goods / num_days, 2),
            "Total WIP (W)": round(results_df["Daily_Total_WIP"].mean(), 2),
            "Lead Time (L = W / T)": round(results_df["Daily_Total_WIP"].mean() / (total_finished_goods/num_days), 2) if total_finished_goods > 0 else 0,
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(station_output_data[m]) for m in members]), 3),
            "Entropy Spread σH": round(np.std([calculate_entropy(station_output_data[m]) for m in members]), 3)
        })

        for m in members:
            pair = next((k.replace("WIP_", "") for k in wip_keys if k.endswith(m)), m)
            avg_wip = np.mean(buffer_levels_over_time[pair]) if pair in buffer_levels_over_time else 0
            h_i = calculate_entropy(station_output_data[m])
            user_data["stations"].append({
                "Scenario": scen_label,
                "Station": f"Station {pair}",
                "Dice Range": f"{dice_configs[m][0]}-{dice_configs[m][1]}",
                "Tot Output": sum(station_output_data[m]),
                "Avg WIP": round(avg_wip, 2),
                "Entropy Hi": round(h_i, 3),
                "Interpretation": "High variability" if h_i > 2.4 else "Stable"
            })

with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_data["history"]:
        st.subheader("Table A: Global Summary")
        st.table(pd.DataFrame(user_data["history"]).set_index("Scenarios"))
        
        st.markdown("---")
        st.subheader("Table B: Station-Level Flow Diagnostics")
        
        s_df = pd.DataFrame(user_data["stations"])
        metrics = ["Dice Range", "Tot Output", "Avg WIP", "Entropy Hi", "Interpretation"]
        
        rows = []
        for scen in s_df['Scenario'].unique():
            for i, metric in enumerate(metrics):
                row_data = {"Scenario": scen if i == 0 else "", "Metric": metric}
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    row_data[s_label] = subset[metric].values[0] if not subset.empty else ""
                rows.append(row_data)
        
        st.table(pd.DataFrame(rows).set_index(["Scenario", "Metric"]))
    else:
        st.info("No data recorded yet. Please run a simulation in the 'Live Operations Console'.")
