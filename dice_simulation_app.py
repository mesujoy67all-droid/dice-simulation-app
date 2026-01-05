import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# -----------------------------------
# Page Configuration
# -----------------------------------
st.set_page_config(page_title="Dice Simulation Platform", layout="wide")

# Initialize session state for tracking scenarios across the session
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'scenario_history' not in st.session_state:
    st.session_state.scenario_history = []

# 1. Login Screen
if not st.session_state.user_name:
    st.title("🔐 Access Production Simulation")
    name_input = st.text_input("Enter your name to start recording the session:")
    if st.button("Start Session"):
        if name_input:
            st.session_state.user_name = name_input
            st.rerun()
        else:
            st.warning("Please enter a name.")
    st.stop()

# -----------------------------------
# Main App UI
# -----------------------------------
st.title("🎲 Dice-Based Production Simulation Platform")
st.markdown(f"**Current Operator:** {st.session_state.user_name} | **Session Recording Active**")

# Sidebar Settings
st.sidebar.header("Simulation Settings")
num_members = st.sidebar.number_input("Number of Workstations", min_value=2, value=7, step=1)
num_days = st.sidebar.number_input("Number of Days", min_value=1, value=20, step=1)

members = [chr(65 + i) for i in range(num_members)]

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

# Helper: Entropy Function
def entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# -----------------------------------
# Run Simulation
# -----------------------------------
if st.sidebar.button("▶ Run Simulation & Record Scenario"):
    # Generate Dice Capacity
    dice_data = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
    df_dice = pd.DataFrame(dice_data)
    df_dice.index += 1

    # Simulation Logic
    wip_buffers = initial_wip.copy()
    history = []
    total_finished_goods = 0
    station_output = defaultdict(list)
    station_wip_history = defaultdict(list)

    for day in df_dice.index:
        day_rolls = df_dice.loc[day]
        daily_fg = 0

        for i, m in enumerate(members):
            roll = day_rolls[m]
            if i == 0:
                nxt = f"WIP_{members[i]}{members[i+1]}"
                wip_buffers[nxt] += roll
                station_output[m].append(roll)
            elif i == len(members) - 1:
                prv = f"WIP_{members[i-1]}{members[i]}"
                move = min(roll, wip_buffers[prv])
                wip_buffers[prv] -= move
                daily_fg = move
                total_finished_goods += move
                station_output[m].append(move)
            else:
                prv = f"WIP_{members[i-1]}{members[i]}"
                nxt = f"WIP_{members[i]}{members[i+1]}"
                move = min(roll, wip_buffers[prv])
                wip_buffers[prv] -= move
                wip_buffers[nxt] += move
                station_output[m].append(move)

        for key, val in wip_buffers.items():
            receiving_station = key.split("_")[1][1]
            station_wip_history[receiving_station].append(val)

        rec = {"Day": day, **wip_buffers.copy(), "Daily_Total_WIP": sum(wip_buffers.values()), "Daily_FG": daily_fg}
        history.append(rec)

    results_df = pd.DataFrame(history).set_index("Day")
    
    # CALCULATE GLOBAL METRICS
    t_put = total_finished_goods / num_days
    avg_wip_total = results_df["Daily_Total_WIP"].mean()
    
    # Calculate Station Entropies for Table A
    station_entropies = [entropy(station_output[m]) for m in members]
    avg_h = np.mean(station_entropies)
    sigma_h = np.std(station_entropies)

    # SAVE SCENARIO TO HISTORY (As requested in image_498107.png)
    scenario_label = f"Scenario #{len(st.session_state.scenario_history) + 1}"
    
    # Formatting setting summary
    wip_val = sum(initial_wip.values())
    ranges = f"Range {dice_configs[members[0]][0]}-{dice_configs[members[0]][1]}"
    
    scenario_data = {
        "Scenarios": scenario_label,
        "Initial WIP & Config": f"WIP={wip_val}, {ranges}, Stations={num_members}",
        "Mean Throughput (T)": round(t_put, 3),
        "Total WIP (W)": round(avg_wip_total, 2),
        "Lead Time (L = W / T)": round(avg_wip_total / t_put, 3) if t_put > 0 else 0,
        "Avg Entropy Ḣ": round(avg_h, 3),
        "Entropy Spread σH": round(sigma_h, 3)
    }
    st.session_state.scenario_history.append(scenario_data)

    # Show results of current run
    st.subheader(f"🚀 Active Run: {scenario_label}")
    st.dataframe(results_df, use_container_width=True)

# -----------------------------------
# TABLE A: GLOBAL SYSTEM DIAGNOSTICS (Scenario Comparison)
# -----------------------------------
if st.session_state.scenario_history:
    st.markdown("---")
    st.subheader("📊 Table A: Global System Diagnostics (Scenario Comparison)")
    st.markdown("Every time you change settings and click 'Run', a new row is added below.")
    
    history_df = pd.DataFrame(st.session_state.scenario_history)
    st.table(history_df)

    # Excel Download Logic
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        history_df.to_excel(writer, sheet_name='Summary_Table', index=False)
    
    st.download_button(
        label="📥 Download All Scenarios as Excel",
        data=output.getvalue(),
        file_name=f"dice_sim_summary_{st.session_state.user_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if st.button("Reset Session / Clear History"):
    st.session_state.scenario_history = []
    st.rerun()
