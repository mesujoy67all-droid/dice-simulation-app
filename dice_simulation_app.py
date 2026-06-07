import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Enterprise Operations Flight Simulator", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- Custom Styling for Premium Simulation Feel ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #4a90e2;
        margin-bottom: 10px;
    }
    .status-stable { color: #2ecc71; font-weight: bold; }
    .status-variable { color: #e74c3c; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- User Database & Session State Simulation ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = {} 

if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None

if 'active_results' not in st.session_state:
    st.session_state.active_results = None

# --- Authentication Gateway ---
def auth_gateway():
    st.title("🔐 Enterprise Flight Simulator Gateway")
    auth_mode = st.radio("Select Portal Mode:", ["Login", "Signup"], horizontal=True)
    
    user_id = st.text_input("Corporate User ID")
    pwd = st.text_input("Security Passcode", type="password")
    
    if auth_mode == "Signup":
        st.info("Your User ID must be unique. Registrations create an isolated environment instance.")
        if st.button("Provision Instance"):
            if user_id in st.session_state.user_db:
                st.error(f"User ID '{user_id}' is already assigned.")
            elif user_id and pwd:
                st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": []}
                st.success("Environment provisioned! Switch to Login mode.")
            else:
                st.warning("All security fields are required.")
                
    elif auth_mode == "Login":
        if st.button("Initialize Simulator"):
            if user_id in st.session_state.user_db:
                if st.session_state.user_db[user_id]["password"] == pwd:
                    st.session_state.authenticated_user = user_id
                    st.session_state.active_results = None
                    st.rerun()
                else:
                    st.error("Invalid passcode credential.")
            else:
                st.error("User ID not registered.")

if st.session_state.authenticated_user is None:
    auth_gateway()
    st.stop()

# --- Access Current User Data Context ---
current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]

history_count = len(user_record["history"])
is_base_run = (history_count == 0)

# --- Interactive Control Room Sidebar ---
st.sidebar.title("🎛️ Flight Command Center")
st.sidebar.caption(f"Active Operator Profile: **{current_user}**")

# Interactive Multi-Step Accordion Tabs in Sidebar
with st.sidebar.expander("📍 Step 1: Operational Mode", expanded=True):
    capacity_mode = st.radio(
        "Capacity Dispatch Method:", 
        ["Stochastic Generation", "Load Baseline File (Excel/CSV)"]
    )

# Establish Structural System Variables
uploaded_df = None
num_days = 1500
num_members = 7
dice_configs = {}
choke_target_station = None
activate_choke_release = False

# Normalize standard workstation identifier tags strictly (A, B, C...)
members_list = [chr(64 + i) for i in range(1, 9)]

with st.sidebar.expander("⚙️ Step 2: Capacity Matrix Parameters", expanded=True):
    if capacity_mode == "Stochastic Generation":
        if 'sim_seed' not in st.session_state:
            st.session_state.sim_seed = None

        keep_seed = st.toggle("🔒 Freeze Seed Lock (Replication Mode)", value=False)
        if not keep_seed or st.session_state.sim_seed is None:
            st.session_state.sim_seed = np.random.randint(0, 1000000)

        st.caption(f"Active Realtime Seed: `{st.session_state.sim_seed}`")
        
        if not is_base_run:
            st.markdown("**⚡ Optimization Interventions**")
            activate_choke_release = st.checkbox("🔓 Release Bottleneck Node (Station A)", value=False)
            if activate_choke_release:
                choke_target_station = st.selectbox(
                    "Mirror Station A parameters to:", 
                    [m for m in members_list if m != 'A' and ord(m)-64 <= 7]
                )
                st.info(f"Station A constraints dynamically synchronized with Node {choke_target_station}.")

        for m in members_list[:7]:
            if m == 'A' and activate_choke_release and choke_target_station:
                st.caption(f"Node {m} Range: *Dynamic Mirror Match*")
                continue
            dice_configs[m] = st.slider(f"Capacity Bounds Node {m}", 1, 20, (1, 6))

        num_days = st.number_input("Simulation Duration (Days)", min_value=1, value=1500, max_value=1500)
        num_members = 7

    else:
        uploaded_file = st.file_uploader("Upload Structural Run Matrix Data", type=["xlsx", "xls", "csv"])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'):
                    uploaded_df = pd.read_csv(uploaded_file, index_col=0)
                else:
                    uploaded_df = pd.read_excel(uploaded_file, index_col=0)
                
                uploaded_df = uploaded_df.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
                num_days = len(uploaded_df)
                num_members = len(uploaded_df.columns)
                st.success(f"Loaded Baseline: {num_days} Horizons, {num_members} Structural Nodes.")
            except Exception as e:
                st.error(f"Execution Error Parsing Record Matrix: {e}")
                
        if uploaded_df is not None:
            temp_members = [chr(64 + i) for i in range(1, num_members + 1)]
            if is_base_run:
                st.warning("🔒 Baseline Anchor Locked: Scaling modifiers suppressed.")
                for m in temp_members:
                    dice_configs[m] = (1, 6)
            else:
                st.markdown("**🚀 Live Intervention Scenario**")
                activate_choke_release = st.checkbox("🔓 Release Bottleneck Node (Station A)", value=False)
                if activate_choke_release:
                    choke_target_station = st.selectbox("Synchronize Node A parameters to:", [m for m in temp_members if m != 'A'])
                
                for m in temp_members:
                    if m == 'A' and activate_choke_release:
                        st.caption("Node A Bounds: *Mirrored from Source Column Target*")
                        continue
                    dice_configs[m] = st.slider(f"Bounds Shift Node {m}", 1, 20, (1, 6))

# Dynamic Generation of Evaluation Elements
members = [chr(64 + i) for i in range(1, num_members + 1)]
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]

with st.sidebar.expander("📦 Step 3: Material Buffer Levels", expanded=False):
    initial_wip = {k: st.number_input(f"Buffer Stage {k.replace('WIP_', '')}", min_value=0, value=4) for k in wip_keys}

# Simulation Controls Layout
st.sidebar.markdown("---")
run_sim_clicked = st.sidebar.button("▶ Execute Live Operational Iteration", type="primary", use_container_width=True)

with st.sidebar.expander("⚙️ System Reset Options"):
    clear_history_clicked = st.button("🗑️ Purge Historical Simulation Memory", use_container_width=True)
    logout_clicked = st.button("🚪 Terminate Flight Session", use_container_width=True)

if clear_history_clicked:
    user_record["history"] = []
    user_record["stations"] = []
    st.session_state.active_results = None
    st.rerun()

if logout_clicked:
    st.session_state.authenticated_user = None
    st.session_state.active_results = None
    st.rerun()

# --- Analytical Processing Core Functions ---
def calculate_entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# --- Simulator Compute Processing Engine ---
if run_sim_clicked:
    if "Load" in capacity_mode and uploaded_df is None:
        st.sidebar.error("Upload a baseline validation run data asset first.")
    else:
        if activate_choke_release and choke_target_station:
            dice_configs['A'] = dice_configs[choke_target_station]

        if capacity_mode == "Stochastic Generation":
            np.random.seed(st.session_state.sim_seed)
            dice_rolls = {}
            for m in members:
                if m == 'A' and activate_choke_release and choke_target_station:
                    continue
                dice_rolls[m] = [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)]
            
            if activate_choke_release and choke_target_station:
                dice_rolls['A'] = list(dice_rolls[choke_target_station])
                
            df_dice = pd.DataFrame(dice_rolls).reindex(columns=members)
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
                        continue
                    low, high = dice_configs[m]
                    if (low != 1) or (high != 6):
                        df_dice[m] = [np.random.randint(low, high + 1) for _ in range(num_days)]
                if activate_choke_release and choke_target_station:
                    df_dice['A'] = df_dice[choke_target_station].copy()
            df_dice = df_dice.reindex(columns=members)

        applied_configs_desc = [
            f"A(Mirrored:{choke_target_station})" if m == 'A' and activate_choke_release 
            else f"{m}({dice_configs[m][0]}-{dice_configs[m][1]})" for m in members
        ]
        dice_info = " | ".join(applied_configs_desc)

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

        df_pennies = pd.DataFrame(pennies_movement_data).reindex(columns=members)
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

        scen_label = "Base-Run" if is_base_run else f"Scenario #{history_count}"
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}={initial_wip[k]}" for k in wip_keys])
        run_description = f"Days={num_days} | WIP: {wip_summary} | Configs: {dice_info}"

        avg_throughput_rate = total_fg / num_days
        avg_total_wip_per_day = sum_total_wip / num_days
        calculated_lead_time = round(avg_total_wip_per_day / avg_throughput_rate, 2) if avg_throughput_rate > 0 else 0

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
            station_label = f"{m}"
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

        st.session_state.active_results = {
            "scen_label": scen_label, "df_dice": df_dice, "df_pennies_final": df_pennies_final,
            "results_df": results_df, "total_fg": total_fg, "num_days": num_days,
            "final_wip_inventory": final_wip_inventory, "lead_time": calculated_lead_time,
            "throughput_rate": avg_throughput_rate
        }
        st.rerun()

# --- Primary Display Tabs ---
tab1, tab2, tab3 = st.tabs(["🚀 Simulator Dashboard", "📊 Flow Diagnostics & Analytics", "📖 Operations Playbook"])

with tab1:
    st.title("🛡️ Flight Deck Live Stream")
    
    if st.session_state.active_results is not None:
        res = st.session_state.active_results
        
        # Micro What-If Notification Modal UI element
        st.markdown(f"### Current Run Segment Profile: `{res['scen_label']}`")
        
        # Top Dashboard Telemetry Cards
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"<div class='metric-card'><h4>Net Throughput</h4><h2>{int(res['total_fg'])} units</h2></div>", unsafe_allow_html=True)
        with m2:
            st.markdown(f"<div class='metric-card'><h4>Velocity (TR)</h4><h2>{round(res['throughput_rate'], 2)} /day</h2></div>", unsafe_allow_html=True)
        with m3:
            st.markdown(f"<div class='metric-card'><h4>Cycle Lead Time</h4><h2>{res['lead_time']} days</h2></div>", unsafe_allow_html=True)
        with m4:
            st.markdown(f"<div class='metric-card'><h4>Ending System WIP</h4><h2>{int(res['final_wip_inventory'])} units</h2></div>", unsafe_allow_html=True)
            
        # Live Performance Analysis Callouts
        if not is_base_run and len(user_record["history"]) > 1:
            base_perf = user_record["history"][0]["Throughput"]
            diff = int(res["total_fg"]) - base_perf
            pct = round((diff / base_perf) * 100, 1)
            if diff > 0:
                st.success(f"📈 **Strategic Impact Assessment:** Current iteration output expanded by **+{pct}%** compared to the initial system validation run.")
            else:
                st.warning(f"📉 **Strategic Impact Assessment:** Strategic change caused variance contraction or loss. Throughput changed by **{pct}%** against baseline parameters.")

        st.markdown("---")
        # Visual Node Network Data Block Layout
        st.subheader("📊 Operational Telemetry Tracking Arrays")
        
        exp_dice = st.expander("🎲 Capacity Dispatch Matrix Table (Allocated Daily Node Potential)", expanded=False)
        with exp_dice:
            st.dataframe(res["df_dice"], use_container_width=True)

        exp_pennies = st.expander("🪙 Daily Effective Unit Displacement Data Array", expanded=True)
        with exp_pennies:
            st.dataframe(res["df_pennies_final"], use_container_width=True)

        exp_wip = st.expander("📦 Stage Buffer Inventory History (Daily WIP Balance Traces)", expanded=False)
        with exp_wip:
            st.dataframe(res["results_df"], use_container_width=True)
    else:
        st.info("💡 Flight simulator payload idle. Configure settings in Command Center and launch the run sequence.")

with tab2:
    st.title("📈 Post-Flight Analytics Ledger")
    if user_record["history"]:
        df_table_a = pd.DataFrame(user_record["history"]).set_index("Scenarios")
        s_df = pd.DataFrame(user_record["stations"])

        st.subheader("Table A: Execution Summary Ledger")
        st.table(df_table_a)
        
        st.markdown("---")
        st.subheader("Table B: Node-Level Process Architecture Analysis")
        
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
        st.subheader("Table C: Multi-Scale Stage Inventory Variance")
        all_recorded_stations = s_df['Station'].unique()
        recorded_letters = sorted([s for s in all_recorded_stations])
        buffer_labels = [f"{recorded_letters[i]}{recorded_letters[i+1]}" for i in range(len(recorded_letters) - 1)]

        rows_c = []
        for scen in s_df['Scenario'].unique():
            for period in ["Day-wise Avg WIP", "Week-wise Avg WIP", "Month-wise Avg WIP"]:
                row_data = {"Scenario": scen, "Time Scale Metric": period}
                for b_label in buffer_labels:
                    target_station = f"{b_label[1]}" 
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == target_station)]
                    if not subset.empty:
                        val = subset["Avg WIP"].values[0]
                        row_data[b_label] = round(val, 2)
                    else:
                        row_data[b_label] = 0.0
                rows_c.append(row_data)

        if rows_c:
            df_table_c = pd.DataFrame(rows_c).set_index(["Scenario", "Time Scale Metric"])
            st.table(df_table_c)
            
        st.markdown("---")
        st.subheader("📥 Export Intelligence Briefing")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_table_a.to_excel(writer, sheet_name='Summary History')
            df_table_b.reset_index().to_excel(writer, sheet_name='Node Diagnostics', index=False)
            df_table_c.reset_index().to_excel(writer, sheet_name='Temporal WIP Analysis', index=False)
        excel_data = output.getvalue()
        st.download_button(
            label="Download Complete Simulation Dossier (Excel)", 
            data=excel_data, 
            file_name=f"Operations_Report_{current_user}.xlsx",
            type="secondary"
        )
    else:
        st.info("No execution runs recorded under this session profile yet.")

with tab3:
    st.title("📖 Strategic System Playbook")
    st.markdown("""
    This section decodes the underlying mechanics of your simulation matrix, focusing on how downstream dependency propagation interacts with stochastic capacity fluctuations.
    """)

    st.header("🔄 Value Stream Structural Formula")
    st.success("🏭 Node A (Infeed) $\longrightarrow$ 📦 Buffer AB $\longrightarrow$ ⚙️ Node B (Internal Node) $\longrightarrow$ 📦 Buffer BC $\longrightarrow$ ⚙️ Node C...")

    st.warning("""
    💡 **Core Operational Guardrail:** A station's daily movement cannot exceed its capacity (Dice Roll) or outpace available inventory upstream (Buffer Balance).
    """)

    st.latex(r"\text{Movement}_{i} = \min(\text{Stochastic Capacity}_{i}, \text{Upstream Buffer}_{i-1 \to i})")

    st.markdown("---")
    st.header("🔬 Informational Chaos Metric (Shannon System Entropy)")
    st.latex(r"H = -\sum_{x} P(x) \log_2 P(x)")
    st.markdown("""
    * **Stable Flow Zone ($H_i < 2.4$):** Balanced capacity allocation with highly repeatable performance metrics.
    * **Turbulent Friction Zone ($H_i \ge 2.4$):** High performance deviation or starvation patterns, indicating systemic imbalance or bottlenecking.
    """)
