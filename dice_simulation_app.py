import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Strategic Operations Simulation Platform", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- Custom Premium Styling ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetricContainer"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    div.stButton > button:first-child {
        border-radius: 6px;
    }
    .auth-container {
        background-color: #ffffff;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border: 1px solid #eaeaea;
    }
    </style>
""", unsafe_allowed_html=True)

# --- User Database Simulation ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = {} 

if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None

# --- PERSISTENCE STORAGE INITIALIZATION ---
if 'active_results' not in st.session_state:
    st.session_state.active_results = None

# --- Authentication Gateway ---
def auth_gateway():
    # Centered layout structure for a premium portal look
    _, col_center, _ = st.columns([1, 1.5, 1])
    
    with col_center:
        st.markdown("<div class='auth-container'>", unsafe_allowed_html=True)
        st.markdown("<h2 style='text-align: center; color: #1E3A8A; margin-bottom: 5px;'>🏛️ Executive Learning Portal</h2>", unsafe_allowed_html=True)
        st.markdown("<p style='text-align: center; color: #6B7280; font-size: 14px;'>Operations & Supply Chain Simulation Engine</p>", unsafe_allowed_html=True)
        st.markdown("<hr style='margin-top: 10px; margin-bottom: 20px;'>", unsafe_allowed_html=True)
        
        auth_mode = st.radio("Access Method:", ["Sign In to Session", "Register New Account"], horizontal=True, label_visibility="collapsed")
        st.markdown("<br>", unsafe_allowed_html=True)
        
        user_id = st.text_input("User ID / Unique Username", placeholder="e.g., exec_analyst")
        pwd = st.text_input("Password", type="password", placeholder="••••••••")
        
        st.markdown("<br>", unsafe_allowed_html=True)
        
        if auth_mode == "Register New Account":
            st.caption("ℹ️ *Your User ID must be unique. This credential manages your trial scenarios.*")
            if st.button("Establish Account", use_container_width=True, type="secondary"):
                if user_id in st.session_state.user_db:
                    st.error(f"User ID '{user_id}' is already taken.")
                elif user_id and pwd:
                    st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": []}
                    st.success("Account provisions established! Please switch to Sign In mode.")
                else:
                    st.warning("All input fields must be populated.")
                    
        elif auth_mode == "Sign In to Session":
            if st.button("Initialize Platform Access", use_container_width=True, type="primary"):
                if user_id in st.session_state.user_db:
                    if st.session_state.user_db[user_id]["password"] == pwd:
                        st.session_state.authenticated_user = user_id
                        st.session_state.active_results = None
                        st.rerun()
                    else:
                        st.error("Authentication failed. Check password credentials.")
                else:
                    st.error("User ID record not discovered.")
        
        st.markdown("</div>", unsafe_allowed_html=True)

if st.session_state.authenticated_user is None:
    auth_gateway()
    st.stop()

# --- Access Current User's Data ---
current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]

# Determine history count to check current state
history_count = len(user_record["history"])
is_base_run = (history_count == 0)

# --- Sidebar: User Controls & Settings ---
st.sidebar.markdown(f"### 👤 Participant ID: **{current_user}**")

# SECTION 1: CAPACITY INPUT CONFIGURATION
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Capacity Configuration")
capacity_mode = st.sidebar.radio("Choose Capacity Input Mode:", ["Random Generation", "Import Data File (Excel/CSV)"])

# Initialize dynamic operational variables
uploaded_df = None
num_days = 1500
num_members = 7
dice_configs = {}
choke_target_station = None
activate_choke_release = False

if capacity_mode == "Random Generation":
    if 'sim_seed' not in st.session_state:
        st.session_state.sim_seed = None

    keep_seed = st.sidebar.toggle("🔒 Keep the same seed (for replication)", value=False)

    if not keep_seed:
        st.session_state.sim_seed = np.random.randint(0, 1000000)

    st.sidebar.caption(f"Current Seed: {st.session_state.sim_seed}")
    
    members_list = [chr(64 + i) for i in range(1, 9)] 
    
    # "Release the Choke" Configuration for Scenario Runs
    if not is_base_run:
        st.sidebar.subheader("🚨 Control Room")
        activate_choke_release = st.sidebar.checkbox("🔓 Activate 'Release the Choke' for Station A", value=False)
        if activate_choke_release:
            choke_target_station = st.sidebar.selectbox("Match Station A's production to:", [m for m in members_list if m != 'A' and ord(m)-64 <= 7])
            st.sidebar.info(f"Station A will dynamically mirror Station {choke_target_station}'s constraints.")

    for m in members_list[:7]: # Default to 7 workstations
        if m == 'A' and activate_choke_release and choke_target_station:
            st.sidebar.caption("Station A Range: *Mirrored from Target*")
            continue
        dice_configs[m] = st.sidebar.slider(f"Dice Range for {m}", 1, 20, (1, 6))

    num_days = st.sidebar.number_input("Days", min_value=1, value=1500, max_value=1500)
    num_members = st.sidebar.number_input("Workstations", min_value=2, value=7, max_value=7)

else:
    uploaded_file = st.sidebar.file_uploader("Upload your 'Table of Dice Rolls' file", type=["xlsx", "xls", "csv"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                uploaded_df = pd.read_csv(uploaded_file, index_col=0)
            else:
                uploaded_df = pd.read_excel(uploaded_file, index_col=0)
            
            uploaded_df = uploaded_df.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
            num_days = len(uploaded_df)
            num_members = len(uploaded_df.columns)
            st.sidebar.success(f"📂 Loaded Baseline: {num_days} Days, {num_members} Stations.")
        except Exception as e:
            st.sidebar.error(f"Error parsing file: {e}. Ensure day counts are structural records.")
            
    if uploaded_df is not None:
        temp_members = [chr(64 + i) for i in range(1, num_members + 1)]
        
        if is_base_run:
            st.sidebar.warning("🔒 Base Run Active: Custom dice modifiers are locked.")
            for m in temp_members:
                dice_configs[m] = (1, 6)
        else:
            st.sidebar.markdown("---")
            st.sidebar.header("🚀 Scenario Improvements")
            st.sidebar.info(f"Modifying Scenario #{history_count}. Set custom parameters below:")
            
            activate_choke_release = st.sidebar.checkbox("🔓 Activate 'Release the Choke' for Station A", value=False)
            if activate_choke_release:
                choke_target_station = st.sidebar.selectbox("Match Station A's capacity to:", [m for m in temp_members if m != 'A'])
            
            for m in temp_members:
                if m == 'A' and activate_choke_release:
                    st.sidebar.caption("Station A Range: *Mirrored from Target File Column*")
                    continue
                dice_configs[m] = st.sidebar.slider(f"Range {m}", 1, 20, (1, 6))

# Generate target structures dynamically
members = [chr(64 + i) for i in range(1, num_members + 1)]
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]

# SECTION 2: WIP INITIALIZATION
st.sidebar.markdown("---")
st.sidebar.header("📦 WIP Initialization")
initial_wip = {k: st.sidebar.number_input(k, min_value=0, value=4) for k in wip_keys}

# SECTION 3: SIMULATION EXECUTION (MAIN BUTTON PLACE)
st.sidebar.markdown("---")
st.sidebar.header("🚀 Action Console")
run_sim_clicked = st.sidebar.button("▶ Run & Save Simulation", use_container_width=True, type="primary")

# SECTION 4: DATA MAINTENANCE
st.sidebar.markdown("---")
st.sidebar.header("🧹 Data Maintenance")
clear_history_clicked = st.sidebar.button("🗑️ Clear Whole History", use_container_width=True)

# SECTION 5: ACCOUNT PORTAL
st.sidebar.markdown("---")
st.sidebar.header("🚪 Session Management")
logout_clicked = st.sidebar.button("🚪 Logout & Exit", use_container_width=True)


# --- Handle Clear and Logout Button Operations ---
if clear_history_clicked:
    user_record["history"] = []
    user_record["stations"] = []
    st.session_state.active_results = None
    st.rerun()

if logout_clicked:
    st.session_state.authenticated_user = None
    st.session_state.active_results = None
    st.rerun()


# --- Utility Functions ---
def calculate_entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))


# --- Simulation Processing Engine ---
if run_sim_clicked:
    if "Import" in capacity_mode and uploaded_df is None:
        st.sidebar.error("Please upload a valid Excel or CSV file first!")
    else:
        # Sync configurations if Choke release is chosen
        if activate_choke_release and choke_target_station:
            dice_configs['A'] = dice_configs[choke_target_station]

        # 1. Capacity Generation/Loading
        if capacity_mode == "Random Generation":
            np.random.seed(st.session_state.sim_seed)
            dice_rolls = {}
            
            # Populate ranges for all stations first
            for m in members:
                if m == 'A' and activate_choke_release and choke_target_station:
                    continue # Will copy after loop
                dice_rolls[m] = [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)]
            
            # Apply dynamic Choke Release mirroring if active
            if activate_choke_release and choke_target_station:
                dice_rolls['A'] = list(dice_rolls[choke_target_station])
                
            df_dice = pd.DataFrame(dice_rolls)
            
            # CRITICAL FIX: Force alignment back to standard structural ordering
            df_dice = df_dice.reindex(columns=members)
            
            df_dice.index = range(1, num_days + 1)
            df_dice.index.name = "Day"
        else:
            df_dice = uploaded_df.copy()
            df_dice.columns = members
            df_dice.index.name = "Day"
            
            if not is_base_run and dice_configs:
                np.random.seed(42) 
                for m in members:
                    if m == 'A' and activate_choke_release:
                        continue # Mirror file column values instead
                    low, high = dice_configs[m]
                    if (low != 1) or (high != 6):
                        df_dice[m] = [np.random.randint(low, high + 1) for _ in range(num_days)]
                
                if activate_choke_release and choke_target_station:
                    df_dice['A'] = df_dice[choke_target_station].copy()
                    
            # Enforce structural column tracking layout
            df_dice = df_dice.reindex(columns=members)

        # --- PROCESS LOGGING CONTEXTS (Implicit Daily Run) ---
        applied_configs_desc = []
        for m in members:
            if m == 'A' and activate_choke_release:
                applied_configs_desc.append(f"A(Choke-Released to {choke_target_station})")
            else:
                applied_configs_desc.append(f"{m}(Range:{dice_configs[m][0]}-{dice_configs[m][1]})")

        dice_info = " | ".join(applied_configs_desc)

        # 2. Simulation Operations Logic
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

        # Process Extra Performance Tables Matrix Data
        df_pennies = pd.DataFrame(pennies_movement_data)
        
        # Keep Station alignment chronological across output views
        df_pennies = df_pennies.reindex(columns=members)
        
        df_pennies.index = range(1, num_days + 1)
        df_pennies.index.name = "Day"
        total_output_row = df_pennies.sum().to_frame().T
        total_output_row.index = ["THROUGHPUT"]
        entropy_vals = {m: round(calculate_entropy(pennies_movement_data[m]), 3) for m in members}
        entropy_row = pd.DataFrame([entropy_vals])
        entropy_row.index = ["ENTROPY (H)"]
        df_pennies_final = pd.concat([df_pennies, total_output_row, entropy_row])

        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative Throughput"] = results_df["Day Wise Total FG"].cumsum()
        sum_total_wip = int(results_df["Daily_Total_WIP"].sum())
        final_wip_inventory = sum(wip_buffers.values())

        # Determine structural logging contexts
        scen_label = "Base-Run" if is_base_run else f"Scenario #{history_count}"
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}= {initial_wip[k]}" for k in wip_keys])
        run_description = f"Days={num_days} | Mode={capacity_mode} | WIP: {wip_summary} | Configs: {dice_info}"

        avg_throughput_rate = total_fg / num_days
        avg_total_wip_per_day = sum_total_wip / num_days
        calculated_lead_time = round(avg_total_wip_per_day / avg_throughput_rate, 2) if avg_throughput_rate > 0 else 0

        # Append to historical datastores
        user_record["history"].append({
            "Scenarios": scen_label,
            "Days, Initial WIP & Dice Range": run_description,
            "Throughput": int(total_fg), 
            "Throughput Rate (TR)": round(avg_throughput_rate, 2),
            "Avg WIP (W_avg)": round(avg_total_wip_per_day, 2),
            "WIP at the End of the Simulation": int(final_wip_inventory),
            "Lead Time (L = Avg WIP / TR)": calculated_lead_time,
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(st_output[m]) for m in members]), 2),
            "Entropy Spread σH": round(np.std([calculate_entropy(st_output[m]) for m in members]), 2)
        })

        days_per_month = 20
        num_months = int(np.ceil(num_days / days_per_month))
        for m in members:
            station_label = f"Station {m}"
            low, high = dice_configs.get(m, (1, 6))
            d_range = f"{low}-{high}"
            if m == 'A' and activate_choke_release:
                d_range = f"Choked ({choke_target_station})"
                
            tot_out = sum(st_output[m])
            avg_wip_val = 0.0
            if m != 'A':
                try:
                    target_key = next(k.replace("WIP_", "") for k in wip_keys if k.endswith(m))
                    avg_wip_val = round(np.mean(st_wip_trend[target_key]), 2)
                except StopIteration:
                    avg_wip_val = 0.0

            monthly_entropies = []
            for i in range(num_months):
                start = i * days_per_month
                end = min((i + 1) * days_per_month, num_days)
                month_data = st_output[m][start:end]
                if len(month_data) > 0:
                    monthly_entropies.append(calculate_entropy(month_data))
            avg_h_monthly = round(np.mean(monthly_entropies), 3) if monthly_entropies else 0.0
            spread_h_monthly = round(np.std(monthly_entropies), 3) if monthly_entropies else 0.0

            user_record["stations"].append({
                "Scenario": scen_label, "Station": station_label, "Dice Range": d_range,
                "Throughput": tot_out, "Avg WIP": avg_wip_val, "Entropy Hi (Monthly Avg)": avg_h_monthly,
                "Entropy Spread σH (Monthly)": spread_h_monthly, "Interpretation": "Variable" if avg_h_monthly > 2.4 else "Stable"
            })

        # Save all UI layouts to memory
        st.session_state.active_results = {
            "scen_label": scen_label,
            "df_dice": df_dice,
            "df_pennies_final": df_pennies_final,
            "results_df": results_df,
            "total_fg": total_fg,
            "num_days": num_days,
            "final_wip_inventory": final_wip_inventory
        }
        st.rerun()

# --- Application Tabs ---
tab1, tab2, tab3 = st.tabs(["🚀 Live Operations Console", "📊 Strategic Performance Analytics", "📖 Methodology"])

with tab1:
    st.title("🚀 Live Operations Console")
    
    if st.session_state.active_results is not None:
        res = st.session_state.active_results

        # Top Executive Key Indicators Bar
        st.subheader(f"🏁 {res['scen_label']} Production Dashboard")
        c1, c2, c3 = st.columns(3)
        c1.metric("Throughput (Units Produced)", int(res["total_fg"])) 
        c2.metric("Throughput Rate (TR / Day)", round(res["total_fg"] / res["num_days"], 2))
        c3.metric("Ending WIP Inventory Status", int(res["final_wip_inventory"])) 
        
        st.markdown("<br>", unsafe_allowed_html=True)

        st.subheader("🎲 Table of Dice Rolls (Capacity Applied)")
        st.dataframe(res["df_dice"], use_container_width=True, height=250)

        st.subheader("🪙 Day-wise Pennies Movement")
        st.dataframe(res["df_pennies_final"], use_container_width=True, height=250)

        st.subheader("📦 Work-In-Progress (WIP) History")
        st.dataframe(res["results_df"], use_container_width=True, height=250)
    else:
        st.info("💡 Configuration Pending: Adjust sidebar parameters and execute 'Run & Save Simulation' to load dashboard telemetry displays.")

with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_record["history"]:
        df_table_a = pd.DataFrame(user_record["history"]).set_index("Scenarios")
        s_df = pd.DataFrame(user_record["stations"])

        st.subheader("Table A: Summary History")
        st.table(df_table_a)
        
        st.markdown("---")
        st.subheader("Table B: Station-Level Flow Diagnostics")
        
        metrics_to_show = ["Dice Range", "Throughput", "Avg WIP", "Entropy Hi (Monthly Avg)", "Entropy Spread σH (Monthly)", "Interpretation"]
        rows_b = []
        for scen in s_df['Scenario'].unique():
            for i, metric in enumerate(metrics_to_show):
                row_data = {"Scenario": scen if i == 0 else "", "Metric": metric}
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    row_data[s_label] = subset[metric].values[0] if not subset.empty and metric in subset.columns else "N/A"
                rows_b.append(row_data)
        
        if rows_b:
            df_table_b = pd.DataFrame(rows_b).set_index(["Scenario", "Metric"])
            st.table(df_table_b)
            
        st.markdown("---")
        st.subheader("Table C: Temporal WIP Averages (By Buffer)")
        all_recorded_stations = s_df['Station'].unique()
        recorded_letters = sorted([s.split(" ")[1] for s in all_recorded_stations])
        buffer_labels = [f"{recorded_letters[i]}{recorded_letters[i+1]}" for i in range(len(recorded_letters) - 1)]

        rows_c = []
        for scen in s_df['Scenario'].unique():
            for period in ["Day-wise Avg WIP", "Week-wise Avg WIP", "Month-wise Avg WIP"]:
                row_data = {"Scenario": scen, "Time Metric": period}
                for b_label in buffer_labels:
                    target_station = f"Station {b_label[1]}" 
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == target_station)]
                    if not subset.empty:
                        val = subset["Avg WIP"].values[0]
                        row_data[b_label] = round(val, 2)
                    else:
                        row_data[b_label] = 0.0
                rows_c.append(row_data)

        if rows_c:
            df_table_c = pd.DataFrame(rows_c).set_index(["Scenario", "Time Metric"])
            st.table(df_table_c)
            
        st.markdown("---")
        st.subheader("📥 Export Analytics")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_table_a.to_excel(writer, sheet_name='Summary History')
            df_table_b.reset_index().to_excel(writer, sheet_name='Station Diagnostics', index=False)
            df_table_c.reset_index().to_excel(writer, sheet_name='Temporal WIP', index=False)
        excel_data = output.getvalue()
        st.download_button(label="Download Full Analytics Excel", data=excel_data, file_name=f"Full_Simulation_{current_user}.xlsx", type="secondary")
    else:
        st.info("No recorded history found for this User ID.")

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
        st.latex(r"TR = \frac{\sum_{day=1}^{n} \text{Daily Throughput}}{n}")

        st.write("### Average System Entropy ($\bar{H}$)")
        st.latex(r"\bar{H} = \frac{1}{M} \sum_{i=1}^{M} H_i")

    with col2:
        st.write("### Lead Time ($L$)")
        st.markdown("Calculated based on average daily WIP levels relative to throughput rate.")
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
