import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Dice Simulation Platform", 
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS Styling for Modern Gamified Feel ---
st.markdown("""
<style>
    /* Main overall background adjustments */
    .stApp {
        background-color: #f8f9fa;
    }
    /* Metric Card Styling customization overrides */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #1E3A8A;
    }
    div[data-testid="stMetricLabel"] {
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #4B5563;
    }
    /* Tab Styling adjustments */
    .stTabs [data-baseweb="tab"] {
        font-size: 1.1rem;
        font-weight: 600;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        color: #1E3A8A !important;
        border-bottom-color: #1E3A8A !important;
    }
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
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🎲 Production Simulation Studio</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280;'>Learn Lean Manufacturing & Variability Dynamics through Gamified Factory Running.</p>", unsafe_allow_html=True)
    
    col_l, col_c, col_r = st.columns([1, 1.5, 1])
    with col_c:
        with st.container(border=True):
            auth_mode = st.radio("Select Access Mode:", ["Login", "Signup"], horizontal=True)
            
            user_id = st.text_input("User ID (Unique Username)")
            pwd = st.text_input("Password", type="password")
            
            if auth_mode == "Signup":
                st.caption("💡 Your User ID must be unique. You can only sign up once.")
                if st.button("🚀 Create Student Account", use_container_width=True):
                    if user_id in st.session_state.user_db:
                        st.error(f"User ID '{user_id}' is already taken.")
                    elif user_id and pwd:
                        st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": []}
                        st.success("Account created! Please switch to Login mode.")
                    else:
                        st.warning("Fields cannot be empty.")
                        
            elif auth_mode == "Login":
                if st.button("🔑 Sign In to Lab", use_container_width=True):
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

history_count = len(user_record["history"])
is_base_run = (history_count == 0)

# --- Sidebar Layout Configuration ---
st.sidebar.markdown(f"### ⚙️ Factory Controls\n**Active Engineer:** `{current_user}`")

st.sidebar.markdown("---")
st.sidebar.subheader("🔌 Mode Settings")
capacity_mode = st.sidebar.radio("Capacity Input Mode:", ["Random Generation", "Import Data File (Excel/CSV)"])

# Initialize dynamic operational variables
uploaded_df = None
num_days = 1500
num_members = 7
dice_configs = {}
station_frequencies = {} 

if capacity_mode == "Random Generation":
    if 'sim_seed' not in st.session_state:
        st.session_state.sim_seed = None

    keep_seed = st.sidebar.toggle("🔒 Freeze System Seed (Replication)", value=False)

    if not keep_seed:
        st.session_state.sim_seed = np.random.randint(0, 1000000)

    st.sidebar.caption(f"Active Seed Value: `{st.session_state.sim_seed}`")
    
    st.sidebar.markdown("### 🎲 Dice Capacity Allocations")
    members_list = [chr(64 + i) for i in range(1, 8)] # Dynamic Generation targeting 7 standard stations
    
    for m in members_list:
        with st.sidebar.expander(f"Station {m} Parameters", expanded=False):
            dice_configs[m] = st.slider(f"Dice Range:", 1, 20, (1, 6), key=f"range_{m}")
            if not is_base_run:
                station_frequencies[m] = st.selectbox(
                    f"Operational Interval:", 
                    list(range(1, 31)), 
                    index=0, 
                    format_func=lambda x: "Every Single Day" if x == 1 else f"Once every {x} Days",
                    key=f"freq_{m}"
                )
            else:
                station_frequencies[m] = 1 

    num_days = st.sidebar.number_input("Simulation Duration (Days)", min_value=1, value=1500, max_value=1500, disabled=True)
    num_members = 7

else:
    uploaded_file = st.sidebar.file_uploader("Upload 'Table of Dice Rolls' File", type=["xlsx", "xls", "csv"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                uploaded_df = pd.read_csv(uploaded_file, index_col=0)
            else:
                uploaded_df = pd.read_excel(uploaded_file, index_col=0)
            
            uploaded_df = uploaded_df.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
            num_days = len(uploaded_df)
            num_members = len(uploaded_df.columns)
            st.sidebar.success(f"📂 Structure Loaded! {num_days} Days, {num_members} Stations.")
        except Exception as e:
            st.sidebar.error(f"Error parsing file: {e}")
            
    if uploaded_df is not None:
        temp_members = [chr(64 + i) for i in range(1, num_members + 1)]
        
        if is_base_run:
            st.sidebar.warning("🔒 Base Run Active: System Modifiers Locked.")
            for m in temp_members:
                dice_configs[m] = (1, 6)
                station_frequencies[m] = 1
        else:
            st.sidebar.markdown("### 🚀 Dynamic Upgrades")
            for m in temp_members:
                with st.sidebar.expander(f"Station {m} Calibration", expanded=False):
                    dice_configs[m] = st.slider(f"Range Modifier:", 1, 20, (1, 6), key=f"up_range_{m}")
                    station_frequencies[m] = st.selectbox(
                        f"Frequency Matrix:", 
                        list(range(1, 31)), 
                        index=0, 
                        format_func=lambda x: "Daily Flow" if x == 1 else f"1 in {x} Days",
                        key=f"up_freq_{m}"
                    )

# Target structure parameters
members = [chr(64 + i) for i in range(1, num_members + 1)]
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Base Buffer Storage (WIP)")
initial_wip = {k: st.sidebar.number_input(f"Initial Buffer {k.replace('WIP_', '')}:", min_value=0, value=4) for k in wip_keys}

st.sidebar.markdown("---")
run_sim_clicked = st.sidebar.button("▶️ Execute & Save Run", type="primary", use_container_width=True)
clear_history_clicked = st.sidebar.button("🗑️ Reset All Scenarios", use_container_width=True)
logout_clicked = st.sidebar.button("🚪 Exit Simulation Lab", use_container_width=True)

if clear_history_clicked:
    user_record["history"] = []
    user_record["stations"] = []
    st.session_state.active_results = None
    st.rerun()

if logout_clicked:
    st.session_state.authenticated_user = None
    st.session_state.active_results = None
    st.rerun()

# --- Calculation Utilities ---
def calculate_entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# --- Processing Engine ---
if run_sim_clicked:
    if "Import" in capacity_mode and uploaded_df is None:
        st.sidebar.error("Please drop an Excel/CSV structure profile first!")
    else:
        if capacity_mode == "Random Generation":
            np.random.seed(st.session_state.sim_seed)
            dice_rolls = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
            df_dice = pd.DataFrame(dice_rolls)
            df_dice.index = range(1, num_days + 1)
            df_dice.index.name = "Day"
        else:
            df_dice = uploaded_df.copy()
            df_dice.columns = members
            df_dice.index.name = "Day"
            
            if not is_base_run and dice_configs:
                np.random.seed(42) 
                for m in members:
                    low, high = dice_configs[m]
                    if (low != 1) or (high != 6):
                        df_dice[m] = [np.random.randint(low, high + 1) for _ in range(num_days)]

        applied_configs_desc = []
        for m in members:
            freq = station_frequencies.get(m, 1)
            if freq > 1:
                for day in df_dice.index:
                    if (day - 1) % freq != 0:
                        df_dice.at[day, m] = 0
                applied_configs_desc.append(f"{m}({dice_configs[m][0]}-{dice_configs[m][1]}, 1/{freq}d)")
            else:
                applied_configs_desc.append(f"{m}({dice_configs[m][0]}-{dice_configs[m][1]}, Daily)")

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

        df_pennies = pd.DataFrame(pennies_movement_data)
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

        scen_label = "🔥 Base-Run" if is_base_run else f"⚡ Scenario #{history_count}"
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}={initial_wip[k]}" for k in wip_keys])
        run_description = f"Days={num_days} | Mode={capacity_mode} | WIP: {wip_summary} | Configs: {dice_info}"

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
            station_label = f"Station {m}"
            low, high = dice_configs.get(m, (1, 6))
            f_val = station_frequencies.get(m, 1)
            d_range = f"{low}-{high} (Freq: 1/{f_val}d)"
            
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
            "results_df": results_df, "total_fg": total_fg, "num_days": num_days, "final_wip_inventory": final_wip_inventory
        }
        st.rerun()

# --- Layout Management Tabs ---
tab1, tab2, tab3 = st.tabs(["🚀 Live Operations Console", "📊 Strategic Diagnostics", "📖 Concept & Logic Laboratory"])

with tab1:
    st.markdown("<h2 style='color: #1E3A8A;'>🏭 Live Operations & Flow Visualization</h2>", unsafe_allow_html=True)
    
    # Static visual layout of the production floor line
    with st.container(border=True):
        st.markdown("**Active Factory Floor Line Map:**")
        st.code("🏭 [Station A] ➔ 📦 Buffer AB ➔ [Station B] ➔ 📦 Buffer BC ➔ [Station C] ➔ 📦 Buffer CD ➔ [Station D]... ➔ 🏁 [Finished Goods]")
    
    if st.session_state.active_results is not None:
        res = st.session_state.active_results
        
        st.markdown(f"### Current Execution State: **{res['scen_label']}**")
        
        # High Vis Metric Tiles
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            with st.container(border=True):
                st.metric("Total System Throughput", f"{int(res['total_fg'])} units")
        with col_m2:
            with st.container(border=True):
                st.metric("Yield Throughput Rate (TR)", f"{round(res['total_fg'] / res['num_days'], 2)} u/day")
        with col_m3:
            with st.container(border=True):
                st.metric("Ending WIP Accumulation", f"{int(res['final_wip_inventory'])} units")
                
        # Interactive Performance Trend Lines
        st.markdown("### 📈 Industrial Flow Performance Analytics")
        st.line_chart(res["results_df"][["Daily_Total_WIP", "Cumulative Throughput"]], height=350)
        
        # Structured Accordion Layouts for deep diving data
        st.markdown("### 🔍 Granular Execution Logs")
        with st.expander("🎲 Capacity Generation Profile Data Matrix (Dice Outputs)", expanded=False):
            st.dataframe(res["df_dice"], use_container_width=True)
            
        with st.expander("🪙 Step-Wise Log Performance Matrix (Pennies Realized Movement)", expanded=False):
            st.dataframe(res["df_pennies_final"], use_container_width=True)
            
        with st.expander("📦 Queue Log (Buffer Inventory Histories)", expanded=False):
            st.dataframe(res["results_df"], use_container_width=True)
    else:
        st.info("💡 Adjust your factory configurations in the sidebar and click 'Execute & Save Run' to initialize the production studio.")

with tab2:
    st.markdown("<h2 style='color: #1E3A8A;'>📊 Cross-Scenario Strategic Performance Insights</h2>", unsafe_allow_html=True)
    
    if user_record["history"]:
        df_table_a = pd.DataFrame(user_record["history"]).set_index("Scenarios")
        s_df = pd.DataFrame(user_record["stations"])

        st.markdown("### 📋 Table A: High-Level Executive Summary")
        st.dataframe(df_table_a, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 🔬 Table B: Workstation Node Flow Diagnostics")
        
        metrics_to_show = ["Dice Range", "Throughput", "Avg WIP", "Entropy Hi (Monthly Avg)", "Entropy Spread σH (Monthly)", "Interpretation"]
        rows_b = []
        for scen in s_df['Scenario'].unique():
            for i, metric in enumerate(metrics_to_show):
                row_data = {"Scenario": scen if i == 0 else "", "Diagnostic Metric": metric}
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    row_data[s_label] = subset[metric].values[0] if not subset.empty and metric in subset.columns else "N/A"
                rows_b.append(row_data)
        
        if rows_b:
            df_table_b = pd.DataFrame(rows_b).set_index(["Scenario", "Diagnostic Metric"])
            st.dataframe(df_table_b, use_container_width=True)
            
        st.markdown("---")
        st.markdown("### ⏱️ Table C: Segmented Temporal Buffer Queue Averages")
        all_recorded_stations = s_df['Station'].unique()
        recorded_letters = sorted([s.split(" ")[1] for s in all_recorded_stations])
        buffer_labels = [f"Buffer {recorded_letters[i]}{recorded_letters[i+1]}" for i in range(len(recorded_letters) - 1)]

        rows_c = []
        for scen in s_df['Scenario'].unique():
            for period in ["Day-wise Avg WIP", "Week-wise Avg WIP", "Month-wise Avg WIP"]:
                row_data = {"Scenario": scen, "Evaluation Interval": period}
                for b_label in buffer_labels:
                    station_letter = b_label.split(" ")[1][1]
                    target_station = f"Station {station_letter}" 
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == target_station)]
                    if not subset.empty:
                        total_wip_accumulated = subset["Avg WIP"].values[0] * num_days
                        if period == "Day-wise Avg WIP": val = total_wip_accumulated / num_days
                        elif period == "Week-wise Avg WIP": val = total_wip_accumulated / (num_days / 5)
                        else: val = total_wip_accumulated / (num_days / 20)
                        row_data[b_label] = round(val, 2)
                    else:
                        row_data[b_label] = 0.0
                rows_c.append(row_data)

        if rows_c:
            df_table_c = pd.DataFrame(rows_c).set_index(["Scenario", "Evaluation Interval"])
            st.dataframe(df_table_c, use_container_width=True)
            
        st.markdown("---")
        st.markdown("### 📥 Export Laboratory Package Data")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_table_a.to_excel(writer, sheet_name='Summary History')
            df_table_b.reset_index().to_excel(writer, sheet_name='Station Diagnostics', index=False)
            df_table_c.reset_index().to_excel(writer, sheet_name='Temporal WIP', index=False)
        excel_data = output.getvalue()
        st.download_button(
            label="📥 Download Full Lab Results (.XLSX)", 
            data=excel_data, 
            file_name=f"Factory_Simulation_{current_user}.xlsx",
            type="secondary",
            use_container_width=True
        )
    else:
        st.info("No run logs found. Please run a simulation on the Operations Console first.")

with tab3:
    st.markdown("<h2 style='color: #1E3A8A;'>📖 Foundational Engineering Methodology</h2>", unsafe_allow_html=True)
    st.markdown("""
    This simulator models the classic **Theory of Constraints (TOC)** production engine game. It demonstrates how system variance and balanced dependencies create massive bottlenecks.
    """)
    
    with st.container(border=True):
        st.markdown("### ⚙️ The Mathematical Governing Flow Rule")
        st.markdown("Because a downline station is dependent on raw material provided by an upline partner station, real throughput is restricted by the absolute limit of available inventory:")
        st.latex(r"\text{Actual Realized Movement}_{i} = \min\left(\text{Dice Roll Capability}_{i},\, \text{Inventory Level In Buffer}_{i-1 \to i}\right)")
        st.info("💡 **Takeaway:** Even if you roll a 20, if your preceding buffer only holds 2 units, your station output is limited to 2!")

    col_l2, col_r2 = st.columns(2)
    with col_l2:
        with st.container(border=True):
            st.markdown("#### Throughput Rate ($TR$) Formula")
            st.latex(r"TR = \frac{\sum_{day=1}^{n} \text{Daily Finished Goods Out}}{n}")
            
            st.markdown("#### Shannon Node Entropy ($H$) Formula")
            st.latex(r"H = -\sum P(x) \log_2 P(x)")
    with col_r2:
        with st.container(border=True):
            st.markdown("#### Little's Law Operational Lead Time ($L$)")
            st.latex(r"L = \frac{\text{Average Accumulation Daily WIP}}{TR}")
            
            st.markdown("#### Entropy Spread System Metric ($\sigma H$)")
            st.latex(r"\sigma H = \sqrt{\frac{\sum (H_i - \bar{H})^2}{M}}")
