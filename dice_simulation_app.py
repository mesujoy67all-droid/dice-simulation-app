import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# -----------------------------------
# Page Configuration
# -----------------------------------
st.set_page_config(page_title="Dice Simulation Platform", layout="wide")

# -----------------------------------
# User "Login" / Session Record Simulation
# -----------------------------------
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

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
# Main App Headers
# -----------------------------------
st.title("🎲 Dice-Based Production Simulation Platform")
st.markdown(f"**Current Operator:** {st.session_state.user_name} | **Status:** Recording Enabled")
st.markdown("---")

# -----------------------------------
# Sidebar: Settings
# -----------------------------------
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
    # Allows any value from 0 up, defaults to 4
    initial_wip[key] = st.sidebar.number_input(f"{key}", min_value=0, value=4, step=1)

# -----------------------------------
# Helper: Entropy Function
# -----------------------------------
def entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# -----------------------------------
# Run Simulation
# -----------------------------------
if st.sidebar.button("▶ Run Simulation & Record"):
    # 1. Generate Dice Capacity
    dice_data = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
    df_dice = pd.DataFrame(dice_data)
    df_dice.index += 1

    st.subheader("🎲 Daily Capacity (Dice Rolls)")
    st.dataframe(df_dice, use_container_width=True)

    # 2. Logic & Recording
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
    
    # 3. Tables and Visuals
    st.subheader("📊 Full Simulation Log")
    st.dataframe(results_df, use_container_width=True)

    # Table B: Diagnostics (AB, BC, CD format)
    table_b_rows = []
    for key in wip_keys:
        pair = key.split("_")[1] # e.g., "AB"
        recv = pair[1] # "B"
        outputs, wips = station_output[recv], station_wip_history[recv]
        avg_w = np.mean(wips) if wips else 0
        h_i = entropy(outputs)
        
        interp = "High variability" if h_i > 2 else "Bottleneck" if avg_w > 8 else "Stable"
        table_b_rows.append({
            "Station Pair": pair, 
            "Total Output": sum(outputs), 
            "Avg WIP": round(avg_w, 2), 
            "Entropy Hᵢ": round(h_i, 3), 
            "Interpretation": interp
        })

    st.subheader("📊 Table B: Station-Level Flow Diagnostics")
    st.dataframe(pd.DataFrame(table_b_rows), use_container_width=True)

    # Download Button for Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        results_df.to_excel(writer, sheet_name='Simulation_History')
        pd.DataFrame(table_b_rows).to_excel(writer, sheet_name='Diagnostics')
    
    st.download_button(
        label="📥 Download Simulation Results (.xlsx)",
        data=output.getvalue(),
        file_name=f"simulation_{st.session_state.user_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if st.button("Log Out / Clear Session"):
        st.session_state.user_name = ""
        st.rerun()
