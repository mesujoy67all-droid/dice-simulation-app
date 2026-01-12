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

        # 2. Pennies Movement (UPDATED WITH SUMMARY ROWS)
        st.subheader("🪙 Day-wise Pennies Movement")
        df_pennies = pd.DataFrame(pennies_movement_data)
        df_pennies.index = range(1, num_days + 1)
        df_pennies.index.name = "Day"

        # Calculate additional rows
        total_output_row = df_pennies.sum().to_frame().T
        total_output_row.index = ["TOTAL OUTPUT"]
        
        entropy_vals = {m: round(calculate_entropy(pennies_movement_data[m]), 3) for m in members}
        entropy_row = pd.DataFrame([entropy_vals])
        entropy_row.index = ["ENTROPY (H)"]

        # Concatenate summary rows to the main dataframe
        df_pennies_final = pd.concat([df_pennies, total_output_row, entropy_row])
        st.dataframe(df_pennies_final, use_container_width=True)

        # 3. WIP History
        st.subheader("📦 Work-In-Progress (WIP) History")
        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative FG"] = results_df["Day Wise Total FG"].cumsum()
        sum_total_wip = int(results_df["Daily_Total_WIP"].sum())
        st.dataframe(results_df, use_container_width=True)

        scen_id = len(user_record["history"]) + 1
        st.subheader(f"🏁 Scenario #{scen_id} Results")
        
        # Calculate the current final WIP for display
        final_wip_inventory = sum(wip_buffers.values())

        # Update the columns to show all three metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Finished Goods", int(total_fg))
        c2.metric("Throughput Rate (TR)", round(total_fg / num_days, 2))
        c3.metric("Ending WIP Inventory", int(final_wip_inventory)) # <--- Added this

        st.subheader("📈 Performance Trends")
        st.line_chart(results_df[["Daily_Total_WIP", "Cumulative FG"]])

        # --- Logging Logic ---
        scen_label = "Base-Run" if not user_record["history"] else f"Scenario #{len(user_record['history'])}"
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}={initial_wip[k]}" for k in wip_keys])
        dice_info = ", ".join([f"{m}:{dice_configs[m][0]}-{dice_configs[m][1]}" for m in members])
        run_description = f"Days={num_days} | WIP: {wip_summary} | Dice: {dice_info}"

        avg_throughput_rate = total_fg / num_days
        avg_total_wip_per_day = sum_total_wip / num_days
        calculated_lead_time = round(avg_total_wip_per_day / avg_throughput_rate, 2) if avg_throughput_rate > 0 else 0
        
        # Capture the final snapshot of inventory
        final_wip_inventory = sum(wip_buffers.values())

        user_record["history"].append({
            "Scenarios": scen_label,
            "Days, Initial WIP & Dice Range": run_description,
            "Total Finished Goods": int(total_fg),
            "Throughput Rate (TR)": round(avg_throughput_rate, 2),
            "Avg WIP (W_avg)": round(avg_total_wip_per_day, 2),
            "WIP at the End of the Simulation": int(final_wip_inventory), # <--- NEW COLUMN
            "Lead Time (L = Avg WIP / TR)": calculated_lead_time,
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(st_output[m]) for m in members]), 2),
            "Entropy Spread σH": round(np.std([calculate_entropy(st_output[m]) for m in members]), 2)
        })

        # --- Updated Logging Logic for Table B ---
        for m in members:
            # We determine the "Station Name" (e.g., Station A, Station B)
            station_label = f"Station {m}"
            
            # Calculate metrics for this specific member
            h_val = calculate_entropy(st_output[m])
            tot_out = sum(st_output[m])
            d_range = f"{dice_configs[m][0]}-{dice_configs[m][1]}"
            
            user_record["stations"].append({
                "Scenario": scen_label, 
                "Station": station_label, 
                "Dice Range": d_range,
                "Tot Output": tot_out, 
                "Entropy Hi": round(h_val, 3)
            })

with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_record["history"]:
        df_table_a = pd.DataFrame(user_record["history"]).set_index("Scenarios")
        s_df = pd.DataFrame(user_record["stations"])

        metrics = ["Tot Output", "Avg WIP", "Entropy Hi", "Interpretation"]
        rows_b = []
        for scen in s_df['Scenario'].unique():
            for i, metric in enumerate(metrics):
                row_data = {"Scenario": scen if i == 0 else "", "Metric": metric}
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    row_data[s_label] = subset[metric].values[0] if not subset.empty else ""
                rows_b.append(row_data)
        df_table_b = pd.DataFrame(rows_b).set_index(["Scenario", "Metric"])

        st.subheader("Table A: Summary History")
        st.table(df_table_a)
        
        st.markdown("---")
        st.subheader("Table B: Station-Level Flow Diagnostics")
        
        # 1. Define the specific metrics for the stations
        metrics_to_show = ["Dice Range", "Tot Output", "Entropy Hi"]
        
        rows_b = []
        # 2. Loop through each scenario and metric to build the pivot table
        for scen in s_df['Scenario'].unique():
            for i, metric in enumerate(metrics_to_show):
                # First row of a scenario shows the name; others are blank for a clean look
                row_data = {"Scenario": scen if i == 0 else "", "Metric": metric}
                
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    if not subset.empty:
                        row_data[s_label] = subset[metric].values[0]
                    else:
                        row_data[s_label] = "N/A"
                rows_b.append(row_data)
        
        # 3. Create the DataFrame and display it
        if rows_b:
            df_table_b = pd.DataFrame(rows_b).set_index(["Scenario", "Metric"])
            st.table(df_table_b)

        st.markdown("---")
        st.subheader("Table C: Temporal WIP Averages (Day/Week/Month)")

        rows_c = []
        for scen in s_df['Scenario'].unique():
            for period in ["Day-wise Avg WIP", "Week-wise Avg WIP", "Month-wise Avg WIP"]:
                row_data = {"Scenario": scen, "Time Metric": period}
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    if not subset.empty:
                        total_wip_accumulated = subset["Avg WIP"].values[0] * num_days
                        if period == "Day-wise Avg WIP":
                            val = total_wip_accumulated / num_days
                        elif period == "Week-wise Avg WIP":
                            val = total_wip_accumulated / (num_days / 5)
                        else: 
                            val = total_wip_accumulated / (num_days / 20)
                        row_data[s_label] = round(val, 2)
                    else:
                        row_data[s_label] = 0.0
                rows_c.append(row_data)
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
        st.latex(r"TR = \frac{\sum_{day=1}^{n} \text{Daily FG}}{n}")

        st.write("### Average System Entropy ($\bar{H}$)")
        st.latex(r"\bar{H} = \frac{1}{M} \sum_{i=1}^{M} H_i")

    with col2:
        st.write("### Lead Time ($L$)")
        st.markdown("Calculated based on average daily WIP levels relative to output rate.")
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




