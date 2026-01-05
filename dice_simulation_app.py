import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# -----------------------------------
# Page Configuration
# -----------------------------------
st.set_page_config(page_title="Dice Simulation Platform", layout="wide")

# Initialize Session States
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'scenario_history' not in st.session_state:
    st.session_state.scenario_history = []

# 1. Login Screen
if not st.session_state.user_name:
    st.title("🔐 Access Production Simulation")
    name_input = st.text_input("Enter your name to start recording:")
    if st.button("Start Session"):
        if name_input:
            st.session_state.user_name = name_input
            st.rerun()
    st.stop()

# -----------------------------------
# Sidebar: Settings (Always Visible)
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
    initial_wip[key] = st.sidebar.number_input(f"{key}", min_value=0, value=4, step=1)

# Helper: Entropy Function
def entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# -----------------------------------
# Navigation Tabs
# -----------------------------------
tab1, tab2 = st.tabs(["🚀 Active Simulation", "📊 Global System Diagnostics"])

with tab1:
    st.title("🎲 Active Simulation")
    st.markdown(f"**Operator:** {st.session_state.user_name}")

    if st.sidebar.button("▶ Run Simulation & Record"):
        # Generate Dice Capacity
        dice_data = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
        df_dice = pd.DataFrame(dice_data)
        df_dice.index += 1

        # Logic & Recording
        wip_buffers = initial_wip.copy()
        history = []
        total_finished_goods = 0
        station_output = defaultdict(list)
        station_wip_history = defaultdict(list)

        for day in df_dice.index:
            day_rolls = df_dice.loc[day]
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

            rec = {"Day": day, **wip_buffers.copy(), "Daily_Total_WIP": sum(wip_buffers.values())}
            history.append(rec)

        results_df = pd.DataFrame(history).set_index("Day")
        
        # Calculate Metrics for History
        t_put = total_finished_goods / num_days
        avg_wip = results_df["Daily_Total_WIP"].mean()
        station_entropies = [entropy(station_output[m]) for m in members]
        h_bar = np.mean(station_entropies)
        sigma_h = np.std(station_entropies)

        # Build Scenario Label
        scen_count = len(st.session_state.scenario_history)
        scen_label = "Base-4" if scen_count == 0 else f"Scenario #{scen_count}"
        
        wip_val = list(initial_wip.values())[0] if initial_wip else 0
        dice_sum = f"Range {dice_configs['A'][0]}-{dice_configs['A'][1]}"
        
        # Save to session state
        st.session_state.scenario_history.append({
            "Scenarios": scen_label,
            "Initial WIP": f"WIP={wip_val}, {dice_sum}",
            "Mean Throughput (T)": round(t_put, 2),
            "Total WIP (W)": round(avg_wip, 2),
            "Lead Time (L = W / T)": round(avg_wip/t_put, 2) if t_put > 0 else 0,
            "Avg Entropy Ḣ": round(h_bar, 3),
            "Entropy Spread σH": round(sigma_h, 3)
        })

        st.subheader("🎲 Daily Dice Rolls")
        st.dataframe(df_dice, use_container_width=True)
        st.subheader("📊 Simulation Logs")
        st.dataframe(results_df, use_container_width=True)
        st.success(f"Scenario Recorded as {scen_label} in Tab 2!")

with tab2:
    st.subheader("📊 Table A: Global System Diagnostics")
    if st.session_state.scenario_history:
        history_df = pd.DataFrame(st.session_state.scenario_history)
        
        # Display the formatted table
        st.table(history_df.set_index("Scenarios"))

        # Download Button
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            history_df.to_excel(writer, sheet_name='Diagnostics', index=False)
        
        st.download_button(
            label="📥 Download Global Diagnostics",
            data=output.getvalue(),
            file_name=f"global_diagnostics_{st.session_state.user_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No scenarios recorded yet. Go to 'Active Simulation' and click Run.")

if st.button("Reset All Data"):
    st.session_state.scenario_history = []
    st.rerun()
