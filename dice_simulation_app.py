import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------------
# Page Configuration
# -----------------------------------
st.set_page_config(
    page_title="Dice Simulation Platform",
    layout="wide"
)

st.title("🎲 Dice-Based Production Simulation Platform")
st.markdown(
    "This platform simulates capacity variability using dice rolls, "
    "WIP buffers, and finished goods output."
)

# -----------------------------------
# Sidebar: Simulation Settings
# -----------------------------------
st.sidebar.header("Simulation Settings")

num_members = st.sidebar.number_input(
    "Number of Members (Workstations)",
    min_value=2,
    value=3,
    step=1
)

num_days = st.sidebar.number_input(
    "Number of Days",
    min_value=1,
    max_value=100000,
    value=10,
    step=1
)

members = [chr(65 + i) for i in range(num_members)]

# -----------------------------------
# Sidebar: Dice Configuration
# -----------------------------------
st.sidebar.subheader("Dice Range per Member")

dice_configs = {}
for m in members:
    low, high = st.sidebar.slider(
        f"Dice range for {m}",
        min_value=1,
        max_value=20,
        value=(1, 6)
    )
    dice_configs[m] = (low, high)

# -----------------------------------
# Sidebar: Initial WIP Buffers
# -----------------------------------
st.sidebar.subheader("Initial WIP Buffers")

wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]
initial_wip = {}

for key in wip_keys:
    initial_wip[key] = st.sidebar.number_input(
        f"{key}",
        min_value=0,
        value=4,
        step=1
    )

# -----------------------------------
# Run Simulation
# -----------------------------------
if st.sidebar.button("▶ Run Simulation"):

    # Generate Dice Rolls
    dice_data = {
        m: [
            np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1)
            for _ in range(num_days)
        ]
        for m in members
    }

    df_dice = pd.DataFrame(dice_data)
    df_dice.index += 1
    df_dice.index.name = "Day"

    st.subheader("🎲 Dice Roll Table (Capacity)")
    st.dataframe(df_dice, use_container_width=True)

    # Simulation Logic
    wip_buffers = initial_wip.copy()
    history = []
    total_finished_goods = 0

    for day in df_dice.index:
        day_rolls = df_dice.loc[day]
        daily_fg = 0

        for i, m in enumerate(members):
            roll = day_rolls[m]

            if i == 0:
                next_wip = f"WIP_{members[i]}{members[i+1]}"
                wip_buffers[next_wip] += roll

            elif i == len(members) - 1:
                prev_wip = f"WIP_{members[i-1]}{members[i]}"
                move_amount = min(roll, wip_buffers[prev_wip])
                wip_buffers[prev_wip] -= move_amount
                daily_fg = move_amount
                total_finished_goods += move_amount

            else:
                prev_wip = f"WIP_{members[i-1]}{members[i]}"
                next_wip = f"WIP_{members[i]}{members[i+1]}"
                move_amount = min(roll, wip_buffers[prev_wip])
                wip_buffers[prev_wip] -= move_amount
                wip_buffers[next_wip] += move_amount

        daily_record = {"Day": day}
        daily_record.update(wip_buffers.copy())
        daily_record["Daily_Total_WIP"] = sum(wip_buffers.values())
        daily_record["Daily_FG"] = daily_fg
        history.append(daily_record)

    # Results
    results_df = pd.DataFrame(history).set_index("Day")

    st.subheader("📊 Simulation Results")
    st.dataframe(results_df, use_container_width=True)

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Finished Goods", total_finished_goods)
    col2.metric("Average Daily FG", round(results_df["Daily_FG"].mean(), 2))
    col3.metric("Average Total WIP", round(results_df["Daily_Total_WIP"].mean(), 2))

    # Charts
    st.subheader("📈 Performance Trends")
    st.line_chart(results_df[["Daily_Total_WIP", "Daily_FG"]])




