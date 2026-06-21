import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Dice Simulation Platform", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS Styling for Premium Institutional Theme ---
st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; }
    div[data-testid="stMetricLabel"] { font-size: 0.95rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem; font-weight: 600; padding: 10px 20px; }
    .auth-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }

    /* --- Larger fonts for st.table (Table A / B / C in Strategic Performance Analytics) --- */
    div[data-testid="stTable"] table { font-size: 1.15rem; }
    div[data-testid="stTable"] th { font-size: 1.15rem; font-weight: 700; }
    div[data-testid="stTable"] td { font-size: 1.15rem; }

    /* --- Scale ONLY the interactive st.dataframe grids (Dice Rolls / Pennies Movement / WIP History) ---
         st.dataframe renders its grid on an HTML canvas, so plain font-size CSS has no effect on it.
         zoom scales the whole rendered widget (including the canvas) as a unit, without touching
         the sidebar, buttons, or any other part of the app. Adjust 1.3 to taste (e.g. 1.5 for bigger). */
    div[data-testid="stDataFrame"] { zoom: 1.3; }

    </style>
""", unsafe_allow_html=True)

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
    st.markdown("<div style='text-align: center; padding: 1.5rem 0;'><h1 style='color: #1E3A8A; margin-bottom: 0.5rem;'>🏫 Institutional Executive Simulation Portal</h1><p style='color: #64748B; font-size:1.1rem;'>Strategic Operations & Assembly Flow Dynamics Engine</p></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; margin-bottom: 1.5rem; color: #334155;'>🔐 Secure Access Terminal</h3>", unsafe_allow_html=True)
        
        auth_mode = st.radio("Select Session Objective:", ["Sign In to Account", "Register New Profile"], horizontal=True, label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        
        user_id = st.text_input("👤 Operator ID / Username", placeholder="Enter unique ID...")
        pwd = st.text_input("🔑 Security Password", type="password", placeholder="Enter password...")
        
        st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
        
        if auth_mode == "Register New Profile":
            st.caption("ℹ️ *Operator IDs are persistent. Please ensure your username is uniquely identifiable.*")
            if st.button("Configure New Account", use_container_width=True, type="secondary"):
                if user_id in st.session_state.user_db:
                    st.error(f"❌ Execution Fault: User ID '{user_id}' is already registered in the database.")
                elif user_id and pwd:
                    st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": []}
                    st.success("✅ Profile successfully committed! Please toggle back to 'Sign In' mode to clear the gate.")
                else:
                    st.warning("⚠️ Access Rejected: Credentials cannot contain empty fields.")
                    
        elif auth_mode == "Sign In to Account":
            if st.button("Initialize Executive Session", use_container_width=True, type="primary"):
                if user_id in st.session_state.user_db:
                    if st.session_state.user_db[user_id]["password"] == pwd:
                        st.session_state.authenticated_user = user_id
                        st.session_state.active_results = None
                        st.rerun()
                    else:
                        st.error("❌ Authentication Failed: Cryptographic mismatch for security password.")
                else:
                    st.error("❌ Security Exception: Specified Operator ID was not found.")
        st.markdown('</div>', unsafe_allow_html=True)

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
st.sidebar.markdown(f"<div style='background-color:#1E3A8A; padding:10px; border-radius:6px; color:white; text-align:center; font-weight:bold;'>👤 ACTIVE SESSION: {current_user.upper()}</div>", unsafe_allow_html=True)

# SECTION 1: CAPACITY INPUT CONFIGURATION
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Capacity Input Mode")
capacity_mode = st.sidebar.radio("Choose Capacity Input Mode:", ["Random Generation", "Import Data File (Excel/CSV)"])

# Initialize dynamic operational variables
uploaded_df = None
num_days = 1500
num_members = st.session_state.get("num_members", 7)
dice_configs = {}
choke_target_station = None
activate_choke_release = False

if capacity_mode == "Random Generation":
    if 'sim_seed' not in st.session_state:
        st.session_state.sim_seed = None

    keep_seed = st.sidebar.toggle("🔒 Lock Environmental Seed", value=False)

    if not keep_seed:
        st.session_state.sim_seed = np.random.randint(0, 1000000)

    st.sidebar.caption(f"Active Deterministic Seed: `{st.session_state.sim_seed}`")
    
    members_list = [chr(64 + i) for i in range(1, 10)]
    
    # "Release the Choke" Configuration for Scenario Runs
    if not is_base_run:
        st.sidebar.subheader("🚨 Intervention Control Room")
        activate_choke_release = st.sidebar.checkbox("🔓 Relieve Bottleneck ('Release Choke' on A)", value=False)
    if activate_choke_release:
            choke_target_station = st.sidebar.selectbox("Align Station A production capacity to:", [m for m in members_list if m != 'A' and ord(m)-64 <= 9])
            st.sidebar.info(f"Station A will dynamically mirror Station {choke_target_station}'s constraints.")

    if 'num_members' not in st.session_state:
        st.session_state.num_members = 7

    for m in members_list[:st.session_state.num_members]:
        if m == 'A' and activate_choke_release and choke_target_station:
            st.sidebar.caption("Station A Range: *Mirrored from Target*")
            continue
        dice_configs[m] = st.sidebar.slider(f"Dice Range for Workstation {m}", 1, 20, (1, 6))

    num_days = st.sidebar.number_input("Simulation Duration (Days)", min_value=1, value=1500, max_value=3000)
    num_members = st.sidebar.number_input("Active Processing Stations", min_value=2, value=7, max_value=9, key="num_members")


else:
    uploaded_file = st.sidebar.file_uploader("Upload operational 'Table of Dice Rolls' data source", type=["xlsx", "xls", "csv"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                uploaded_df = pd.read_csv(uploaded_file, index_col=0)
            else:
                uploaded_df = pd.read_excel(uploaded_file, index_col=0)
            
            uploaded_df = uploaded_df.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
            num_days = len(uploaded_df)
            num_members = len(uploaded_df.columns)
            st.sidebar.success(f"📂 Verification Success: {num_days} Days, {num_members} Stations Loaded.")
        except Exception as e:
            st.sidebar.error(f"Error parsing file: {e}. Ensure day counts are structural records.")
            
    if uploaded_df is not None:
        temp_members = [chr(64 + i) for i in range(1, num_members + 1)]
        
        if is_base_run:
            st.sidebar.warning("🔒 Baseline Protection Active: Scenario parameters are locked.")
            for m in temp_members:
                dice_configs[m] = (1, 6)
        else:
            st.sidebar.markdown("---")
            st.sidebar.header("🚀 Scenario Interventions")
            st.sidebar.info(f"Configuring Interactive Scenario Expansion #{history_count}. Adjust parameters below:")
            
            activate_choke_release = st.sidebar.checkbox("🔓 Relieve Bottleneck ('Release Choke' on A)", value=False)
            if activate_choke_release:
                choke_target_station = st.sidebar.selectbox("Align Station A production capacity to:", [m for m in temp_members if m != 'A'])
            
            for m in temp_members:
                if m == 'A' and activate_choke_release:
                    st.sidebar.caption("Station A Range: *Mirrored from Target File Column*")
                    continue
                dice_configs[m] = st.sidebar.slider(f"Operational Range {m}", 1, 20, (1, 6))

# Generate target structures dynamically
members = [chr(64 + i) for i in range(1, num_members + 1)]
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]

# SECTION 2: WIP INITIALIZATION
st.sidebar.markdown("---")
st.sidebar.header("📦 Line-Stock WIP Initialization")
initial_wip = {k: st.sidebar.number_input(f"Initial Buffer {k.replace('WIP_', '')}", min_value=0, value=4) for k in wip_keys}

# SECTION 3: SIMULATION EXECUTION (MAIN BUTTON PLACE)
st.sidebar.markdown("---")
st.sidebar.header("🚀 Execution Terminal")
run_sim_clicked = st.sidebar.button("▶ Compile & Execute Trial", use_container_width=True, type="primary")

# SECTION 4: DATA MAINTENANCE
st.sidebar.markdown("---")
st.sidebar.header("🧹 Workspace Maintenance")
clear_history_clicked = st.sidebar.button("🗑️ Purge Historical Logs", use_container_width=True)

# SECTION 5: ACCOUNT PORTAL
st.sidebar.markdown("---")
st.sidebar.header("🚪 Session Management")
logout_clicked = st.sidebar.button("🚪 Terminate Session & Exit", use_container_width=True)


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
        st.sidebar.error("Execution Fault: Please upload an analytical capacity CSV/Excel matrix first!")
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
            station_label = m  # MANDATED: Simplified identifier format
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
    st.markdown("<h2 style='color:#1E3A8A; margin-top:10px;'>🚀 Operational Execution Cockpit</h2>", unsafe_allow_html=True)
    st.write("Monitor plant line behaviors, active structural parameters, and real-time station outputs below.")
    
    if st.session_state.active_results is not None:
        res = st.session_state.active_results

        # Metric Presentation Section
        st.markdown(f"### 🏁 Executive Target Summary ({res['scen_label']})")
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(label="Total Throughput Yield", value=f"{int(res['total_fg'])} units", delta=None)
        with m_col2:
            st.metric(label="System Throughput Rate (TR)", value=f"{round(res['total_fg'] / res['num_days'], 2)} units/day", delta=None)
        with m_col3:
            st.metric(label="Terminating WIP Stockpile", value=f"{int(res['final_wip_inventory'])} units", delta=None)
        
        st.markdown("<hr>", unsafe_allow_html=True)

        st.subheader("🎲 Table of Dice Rolls (Capacity Applied)")
        dice_col_config = {col: st.column_config.Column(width="small") for col in res["df_dice"].columns}
        st.dataframe(res["df_dice"], use_container_width=True, column_config=dice_col_config)

        st.subheader("🪙 Day-wise Pennies Movement")
        pennies_col_config = {col: st.column_config.Column(width="small") for col in res["df_pennies_final"].columns}
        st.dataframe(res["df_pennies_final"], use_container_width=True, column_config=pennies_col_config)

        st.subheader("📦 Work-In-Progress (WIP) History")
        wip_col_config = {col: st.column_config.Column(width="small") for col in res["results_df"].columns}
        st.dataframe(res["results_df"], use_container_width=True, column_config=wip_col_config)
    else:
        st.markdown("""
            <div style="background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 1.5rem; border-radius: 4px; margin-top: 2rem;">
                <h4 style="color: #1E40AF; margin-top:0;">💡 Terminal Ready for Simulation Run</h4>
                <p style="color: #1E3A8A; margin-bottom:0;">Configure initial parameters, distribution capacity limits, and buffer sizing targets inside the executive sidebar panel. Click <strong>Run & Save Simulation</strong> to plot current platform analytical data streams.</p>
            </div>
        """, unsafe_allow_html=True)

with tab2:
    st.markdown("<h2 style='color:#1E3A8A; margin-top:10px;'>📊 Strategic Performance Analytics</h2>", unsafe_allow_html=True)
    st.write("Compare cross-run scenarios, audit workflow variation variances, and map structural information.")
    
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
            # Table B renders clean simplified station identifiers dynamically as headers (A, B, C...)
            st.table(df_table_b)
            
        st.markdown("---")
        st.subheader("Table C: Temporal WIP Averages (By Buffer)")
        all_recorded_stations = s_df['Station'].unique()
        recorded_letters = sorted([s for s in all_recorded_stations])
        buffer_labels = [f"{recorded_letters[i]}{recorded_letters[i+1]}" for i in range(len(recorded_letters) - 1)]

        rows_c = []
        for scen in s_df['Scenario'].unique():
            for period in ["Day-wise Avg WIP", "Week-wise Avg WIP", "Month-wise Avg WIP"]:
                row_data = {"Scenario": scen, "Time Metric": period}
                for b_label in buffer_labels:
                    target_station = b_label[1] 
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
        st.download_button(label="Download Full Analytics Excel", data=excel_data, file_name=f"Full_Simulation_{current_user}.xlsx")
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
