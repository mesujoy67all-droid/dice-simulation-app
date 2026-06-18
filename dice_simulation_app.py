import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Operations & Flow Dynamics Simulation Platform", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS Styling ---
st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; }
    div[data-testid="stMetricLabel"] { font-size: 0.95rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    </style>
""", unsafe_allow_html=True)

# --- Session Initialization ---
if 'user_db' not in st.session_state: st.session_state.user_db = {} 
if 'authenticated_user' not in st.session_state: st.session_state.authenticated_user = None
if 'active_results' not in st.session_state: st.session_state.active_results = None

# --- Authentication Gateway ---
def auth_gateway():
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏫 Institutional Executive Simulation Portal</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        auth_mode = st.radio("Select Session Objective:", ["Sign In to Account", "Register New Profile"], horizontal=True)
        user_id = st.text_input("👤 Operator ID")
        pwd = st.text_input("🔑 Security Password", type="password")
        
        if auth_mode == "Register New Profile":
            if st.button("Configure New Account"):
                if user_id in st.session_state.user_db: st.error("ID exists.")
                elif user_id and pwd:
                    st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": []}
                    st.success("Profile created. Switch to Sign In.")
        else:
            if st.button("Initialize Executive Session"):
                if user_id in st.session_state.user_db and st.session_state.user_db[user_id]["password"] == pwd:
                    st.session_state.authenticated_user = user_id
                    st.rerun()
                else: st.error("Authentication Failed.")
    st.stop()

if st.session_state.authenticated_user is None: auth_gateway()

current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]
is_base_run = len(user_record["history"]) == 0

# --- Sidebar: User Controls ---
st.sidebar.markdown(f"**👤 ACTIVE SESSION: {current_user.upper()}**")
capacity_mode = st.sidebar.radio("Choose Capacity Input Mode:", ["Random Generation", "Import Data File"])

# Dynamic Member Setup
num_days = 1500
dice_configs = {}
activate_choke_release = False
choke_target_station = None

if capacity_mode == "Random Generation":
    num_members = st.sidebar.number_input("Active Processing Stations", min_value=2, value=7, max_value=9)
    members = [chr(64 + i) for i in range(1, num_members + 1)]
    
    if not is_base_run:
        activate_choke_release = st.sidebar.checkbox("🔓 Relieve Bottleneck ('Release Choke' on A)")
        if activate_choke_release:
            choke_target_station = st.sidebar.selectbox("Align Station A to:", [m for m in members if m != 'A'])

    for m in members:
        if m == 'A' and activate_choke_release: continue
        dice_configs[m] = st.sidebar.slider(f"Dice Range for {m}", 1, 20, (1, 6))
else:
    uploaded_file = st.sidebar.file_uploader("Upload Data Source", type=["csv", "xlsx"])
    members = []
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        members = list(df.columns)
        num_members = len(members)

wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]
initial_wip = {k: st.sidebar.number_input(f"Initial Buffer {k.replace('WIP_', '')}", min_value=0, value=4) for k in wip_keys}

if st.sidebar.button("▶ Compile & Execute Trial"):
    # Logic implementation for 9 stations
    # 1. Generate/Load Data
    dice_rolls = {m: np.random.randint(dice_configs[m][0], dice_configs[m][1]+1, num_days) for m in members if m != 'A'}
    if activate_choke_release:
        dice_rolls['A'] = dice_rolls[choke_target_station]
    else:
        dice_rolls['A'] = np.random.randint(dice_configs['A'][0], dice_configs['A'][1]+1, num_days)
    
    df_dice = pd.DataFrame(dice_rolls).reindex(columns=members)
    
    # 2. Simulation Loop
    wip_buffers = {k: initial_wip[k] for k in wip_keys}
    history, st_output, total_fg = [], defaultdict(list), 0
    
    for day in range(num_days):
        day_rolls = df_dice.iloc[day]
        current_wip = wip_buffers.copy()
        for i, m in enumerate(members):
            roll = day_rolls[m]
            if i == 0: 
                wip_buffers[wip_keys[0]] += roll
                st_output[m].append(roll)
            elif i == len(members) - 1:
                move = min(roll, wip_buffers[wip_keys[-1]])
                wip_buffers[wip_keys[-1]] -= move
                total_fg += move
                st_output[m].append(move)
            else:
                move = min(roll, wip_buffers[wip_keys[i-1]])
                wip_buffers[wip_keys[i-1]] -= move
                wip_buffers[wip_keys[i]] += move
                st_output[m].append(move)
        history.append({"Day": day+1, **wip_buffers.copy(), "FG": total_fg})

    st.session_state.active_results = {"df_dice": df_dice, "total_fg": total_fg}
    st.rerun()

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
        st.dataframe(res["df_dice"], use_container_width=True)

        st.subheader("🪙 Day-wise Pennies Movement")
        st.dataframe(res["df_pennies_final"], use_container_width=True)

        st.subheader("📦 Work-In-Progress (WIP) History")
        st.dataframe(res["results_df"], use_container_width=True)
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
