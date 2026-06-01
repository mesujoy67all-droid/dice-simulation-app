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

# --- SEED LOGIC ---
if 'sim_seed' not in st.session_state:
    st.session_state.sim_seed = None

keep_seed = st.sidebar.toggle("🔒 Keep the same seed (for replication)", value=False)

if not keep_seed:
    st.session_state.sim_seed = np.random.randint(0, 1000000)

st.sidebar.caption(f"Current Seed: {st.session_state.sim_seed}")
# ----------------------

# System Constraints (Fixed configurations)
num_days = st.sidebar.number_input("Days", min_value=1, value=1500, max_value=1500)
num_members = st.sidebar.number_input("Workstations", min_value=2, value=7, max_value=7)

members = [chr(64 + i) for i in range(1, num_members + 1)]
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]

# --- UPDATED CAPACITY MANAGEMENT WITH OVERRIDE LOGIC ---
st.sidebar.subheader("🎲 Capacity Generation Mode")
capacity_source = st.sidebar.radio(
    "Choose Capacity Source:",
    ["Pure Random (Dice)", "Upload CSV/Excel + Tweak Sliders"],
    help="Select whether to generate entirely fresh values or use an uploaded file while tweaking specific bottlenecks."
)

uploaded_df = None
dice_configs = {}

# Keep sliders active for BOTH options so you can tweak the bottleneck on top of your file!
st.sidebar.markdown("### 🎛️ Station Configuration Sliders")
for m in members:
    dice_configs[m] = st.sidebar.slider(f"Dice Range for {m}", 1, 20, (1, 6))

if capacity_source == "Upload CSV/Excel + Tweak Sliders":
    uploaded_file = st.sidebar.file_uploader("Upload Base Capacity File (CSV or XLSX)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                uploaded_df = pd.read_csv(uploaded_file)
            else:
                uploaded_df = pd.read_excel(uploaded_file)
            
            # Basic validation check
            missing_cols = [m for m in members if m not in uploaded_df.columns]
            if missing_cols:
                st.sidebar.error(f"Missing station columns in file: {missing_cols}")
                uploaded_df = None
            elif len(uploaded_df) < num_days:
                st.sidebar.warning(f"File has {len(uploaded_df)} rows. Setting simulation window to match file.")
                num_days = len(uploaded_df)
        except Exception as e:
            st.sidebar.error(f"Error loading file: {e}")
            
    # Allow user to check which stations should drop the uploaded data and use the slider values instead
    st.sidebar.markdown("### 🚨 Override Bottlenecks")
    override_stations = st.sidebar.multiselect(
        "Select Stations to OVERRIDE with Slider Ranges instead of File Data:",
        options=members,
        help="Check the stations where you want to ignore the file data and deploy your new dice configuration."
    )
else:
    override_stations = []

wip_keys_list = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]
initial_wip = {k: st.sidebar.number_input(k, min_value=0, value=4) for k in wip_keys}

# The "Run" button
if st.sidebar.button("▶ Run & Save Simulation"):
    if capacity_source == "Upload CSV/Excel + Tweak Sliders" and uploaded_df is None:
        st.sidebar.error("Please upload a valid capacity file before running.")
        st.session_state.trigger_sim = False
    else:
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
        np.random.seed(st.session_state.sim_seed)
        
        # 1. Hybrid Capacity Generation Engine
        dice_rolls = {}
        d_range_log = {}
        
        for m in members:
            # If pure random, or if this specific station is selected for a bottleneck breakthrough override
            if capacity_source == "Pure Random (Dice)" or m in override_stations:
                dice_rolls[m] = [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)]
                d_range_log[m] = f"{dice_configs[m][0]}-{dice_configs[m][1]} (Dice)"
            else:
                # Fallback to the uploaded file configuration data
                dice_rolls[m] = uploaded_df[m].head(num_days).tolist()
                d_range_log[m] = "Uploaded Data"

        df_dice = pd.DataFrame(dice_rolls)
        df_dice.index = range(1, num_days + 1)
        df_dice.index.name = "Day"

        # 2. Simulation Engine Flow Logic
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

        # --- DISPLAY RESULTS ---
        st.subheader("🎲 Table of Capacity Values")
        st.dataframe(df_dice, use_container_width=True)

        st.subheader("🪙 Day-wise Pennies Movement")
        df_pennies = pd.DataFrame(pennies_movement_data)
        df_pennies.index = range(1, num_days + 1)
        df_pennies.index.name = "Day"

        total_output_row = df_pennies.sum().to_frame().T
        total_output_row.index = ["THROUGHPUT"]
        
        entropy_vals = {m: round(calculate_entropy(pennies_movement_data[m]), 3) for m in members}
        entropy_row = pd.DataFrame([entropy_vals])
        entropy_row.index = ["ENTROPY (H)"]

        df_pennies_final = pd.concat([df_pennies, total_output_row, entropy_row])
        st.dataframe(df_pennies_final, use_container_width=True)

        st.subheader("📦 Work-In-Progress (WIP) History")
        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative Throughput"] = results_df["Day Wise Total FG"].cumsum()
        sum_total_wip = int(results_df["Daily_Total_WIP"].sum())
        st.dataframe(results_df, use_container_width=True)

        history_count = len(user_record["history"])
        display_title = "🏁 Base Run Results" if history_count == 0 else f"🏁 Scenario #{history_count} Results"
        scen_label = "Base-Run" if history_count == 0 else f"Scenario #{history_count}"
        
        st.subheader(display_title)
        final_wip_inventory = sum(wip_buffers.values())

        c1, c2, c3 = st.columns(3)
        c1.metric("Throughput", int(total_fg))
        c2.metric("Throughput Rate (TR)", round(total_fg / num_days, 2))
        c3.metric("Ending WIP Inventory", int(final_wip_inventory)) 

        st.subheader("📈 Performance Trends")
        st.line_chart(results_df[["Daily_Total_WIP", "Cumulative Throughput"]])

        # --- Logging Logic ---
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}={initial_wip[k]}" for k in wip_keys])
        if capacity_source == "Pure Random (Dice)":
            run_description = f"Days={num_days} | WIP: {wip_summary} | Pure Random Simulation"
        else:
            run_description = f"Days={num_days} | WIP: {wip_summary} | File + Overridden Stations: {override_stations}"

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
                "Scenario": scen_label, 
                "Station": station_label, 
                "Dice Range": d_range_log[m],
                "Throughput": tot_out,
                "Avg WIP": avg_wip_val,
                "Entropy Hi (Monthly Avg)": avg_h_monthly,
                "Entropy Spread σH (Monthly)": spread_h_monthly,
                "Interpretation": "Variable" if avg_h_monthly > 2.4 else "Stable"
            })

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
                        total_wip_accumulated = subset["Avg WIP"].values[0] * num_days
                        if period == "Day-wise Avg WIP": val = total_wip_accumulated / num_days
                        elif period == "Week-wise Avg WIP": val = total_wip_accumulated / (num_days / 5)
                        else: val = total_wip_accumulated / (num_days / 20)
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
        st.download_button(label="Download Full Analytics Excel", data=output.getvalue(), file_name=f"Full_Simulation_{current_user}.xlsx")
    else:
        st.info("No recorded history found for this User ID.")

# --- PAGE 3: METHODOLOGY ---
with tab3:
    st.title("📖 Simulation Methodology & Logic")
    st.markdown("This page pulls back the curtain on the simulation engine.")
    st.success("🏭 **Station A** $\longrightarrow$ 📦 **Buffer AB** $\longrightarrow$ ⚙️ **Station B**...")
    st.latex(r"\text{Movement}_{B} = \min(\text{Capacity}_{B}, \text{Buffer}_{A \to B})")
