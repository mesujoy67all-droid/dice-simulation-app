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
                # Added 'raw_data' to store full daily results for Table C
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

# --- Access Current User's Data ---
current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]

# Ensure raw_data key exists for older accounts
if "raw_data" not in user_record:
    user_record["raw_data"] = []

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
    user_record["raw_data"] = []
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
        # 1. Capacity Generation
        dice_rolls = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
        df_dice = pd.DataFrame(dice_rolls)
        df_dice.index = range(1, num_days + 1)
        df_dice.index.name = "Day"

        # 2. Simulation Logic
        wip_buffers = initial_wip.copy()
        history = []
        st_output = defaultdict(list)
        st_wip_trend = defaultdict(list)
        total_fg = 0

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
        c1, c2 = st.columns(2)
        c1.metric("Total Finished Goods", int(total_fg))
        c2.metric("Throughput Rate (TR)", round(total_fg / num_days, 2))
        # Total WIP (Sum) Metric Removed as requested

        st.subheader("📈 Performance Trends")
        st.line_chart(results_df[["Daily_Total_WIP", "Cumulative FG"]])

        # --- Logging Logic ---
        scen_label = f"Scenario #{scen_id}"
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}={v}" for k, v in initial_wip.items()])
        dice_info = ", ".join([f"{m}:{dice_configs[m][0]}-{dice_configs[m][1]}" for m in members])
        
        avg_tr = total_fg / num_days
        avg_wip = sum_total_wip / num_days
        lt = round(avg_wip / avg_tr, 2) if avg_tr > 0 else 0

        user_record["history"].append({
            "Scenarios": scen_label,
            "Days, Initial WIP & Dice Range": f"Days={num_days} | {wip_summary} | {dice_info}",
            "Total Finished Goods": int(total_fg),
            "Throughput Rate (TR)": round(avg_tr, 2),
            "Total WIP (W)": sum_total_wip,
            "Lead Time (L)": lt,
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(st_output[m]) for m in members]), 3)
        })

        for m in members:
            pair = next((k.replace("WIP_", "") for k in wip_keys if k.endswith(m)), m)
            if pair == "A": continue
            h_val = calculate_entropy(st_output[m])
            user_record["stations"].append({
                "Scenario": scen_label, "Station": f"Station {pair}", 
                "Tot Output": sum(st_output[m]), "Avg WIP": round(np.mean(st_wip_trend[pair]), 2) if pair in st_wip_trend else 0,
                "Entropy Hi": round(h_val, 3), "Interpretation": "Variable" if h_val > 2.4 else "Stable"
            })
        
        # Save raw results for the new Table C analysis
        raw_results = results_df.copy()
        raw_results['Scenario'] = scen_label
        user_record["raw_data"].append(raw_results)

with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_record["history"]:
        # --- Table A: Summary ---
        st.subheader("Table A: Summary History")
        st.table(pd.DataFrame(user_record["history"]).set_index("Scenarios"))
        
        # --- Table B: Station Diagnostics ---
        st.markdown("---")
        st.subheader("Table B: Station-Level Flow Diagnostics (Buffers Only)")
        s_df = pd.DataFrame(user_record["stations"])
        # Removed "Dice Range" from the metrics list
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

        # --- Table C: Time-Phased WIP Analysis ---
        st.markdown("---")
        st.subheader("Table C: Multi-Temporal WIP Analysis (Station-Wise)")
        
        if user_record["raw_data"]:
            # Display based on the latest simulation run
            latest_data = user_record["raw_data"][-1]
            # Filter only the WIP buffer columns (e.g., AB, BC, etc.)
            wip_cols = [c for c in latest_data.columns if "WIP_" in c]
            clean_wip_cols = [c.replace("WIP_", "") for c in wip_cols]
            
            wip_df = latest_data[wip_cols].copy()
            wip_df.columns = clean_wip_cols

            # Time grouping logic
            wip_df['Week'] = (wip_df.index - 1) // 5 + 1
            wip_df['Month'] = (wip_df.index - 1) // 20 + 1

            c_type = st.selectbox("Select Temporal View:", ["Day-Wise (Raw)", "Week-Wise (Avg)", "Month-Wise (Avg)"])

            if c_type == "Day-Wise (Raw)":
                st.dataframe(wip_df[clean_wip_cols], use_container_width=True)
            elif c_type == "Week-Wise (Avg)":
                week_avg = wip_df.groupby('Week')[clean_wip_cols].mean().round(2)
                st.dataframe(week_avg, use_container_width=True)
            else:
                month_avg = wip_df.groupby('Month')[clean_wip_cols].mean().round(2)
                st.dataframe(month_avg, use_container_width=True)

        st.markdown("---")
        st.subheader("📥 Export Analytics")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pd.DataFrame(user_record["history"]).to_excel(writer, sheet_name='Summary')
            if user_record["raw_data"]:
                user_record["raw_data"][-1].to_excel(writer, sheet_name='Full_WIP_Log')
        
        st.download_button(label="Download Analytics as Excel", data=output.getvalue(), file_name=f"Simulation_{current_user}.xlsx")
    else:
        st.info("No recorded history found for this User ID.")

with tab3:
    st.title("📖 Simulation Methodology & Logic")
    st.markdown("""
    ### Time Phasing Logic
    * **Day-Wise:** Direct WIP counts at the end of each simulated day.
    * **Week-Wise (5 Days):** The arithmetic mean of WIP levels recorded over a 5-day production cycle.
    * **Month-Wise (20 Days):** The arithmetic mean of WIP levels recorded over a 20-day production cycle.
    """)
