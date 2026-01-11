# --- Application Tabs ---
tab1, tab2, tab3 = st.tabs(["🚀 Live Operations Console", "📊 Strategic Performance Analytics", "📖 Methodology"])

with tab1:
    st.title("🚀 Live Operations Console")
    
    if st.session_state.trigger_sim:
        # 1. Capacity Generation
        dice_rolls = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
        df_dice = pd.DataFrame(dice_rolls)
        df_dice.index = range(1, num_days + 1)
        df_dice.index.name = "Day"

        # 2. Simulation Logic
        wip_buffers = {k: initial_wip[k] for k in wip_keys}
        history = []
        movement_history = [] # <--- NEW: To track penny transfers
        total_fg = 0
        st_output = defaultdict(list)
        st_wip_trend = defaultdict(list)

        for day in df_dice.index:
            day_rolls = df_dice.loc[day]
            daily_fg_out = 0
            daily_movements = {"Day": day} # <--- NEW: Row for the movements table
            
            for i, m in enumerate(members):
                roll = day_rolls[m]
                if i == 0:
                    # Station A: Moves whatever the dice says into the first buffer
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    wip_buffers[nxt] += roll
                    st_output[m].append(roll)
                    daily_movements[m] = roll # Movement for A is the roll
                elif i == len(members) - 1:
                    # Last Station: Moves from buffer to Finished Goods
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    daily_fg_out = move
                    total_fg += move
                    st_output[m].append(move)
                    daily_movements[m] = move # Movement for last station
                else:
                    # Middle Stations: Moves from prev buffer to next buffer
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    wip_buffers[nxt] += move
                    st_output[m].append(move)
                    daily_movements[m] = move # Movement for middle station

            movement_history.append(daily_movements)

            for k, v in wip_buffers.items():
                st_wip_trend[k.replace("WIP_", "")].append(v)

            history.append({
                "Day": day, 
                **wip_buffers.copy(), 
                "Daily_Total_WIP": sum(wip_buffers.values()), 
                "Day Wise Total FG": daily_fg_out
            })

        # Convert movement history to DataFrame
        df_movements = pd.DataFrame(movement_history).set_index("Day")
        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative FG"] = results_df["Day Wise Total FG"].cumsum()
        sum_total_wip = int(results_df["Daily_Total_WIP"].sum())

        # --- DISPLAY SECTION ---
        st.subheader("🎲 Table of Dice Rolls (Capacity)")
        st.dataframe(df_dice, use_container_width=True)

        # NEW TABLE ADDED HERE
        st.subheader("🪙 Table of Penny Movements (Actual Units Transferred)")
        st.info("This table shows how many units actually moved from each station. (Station A = Dice Roll | Others = min(Dice, Available WIP))")
        st.dataframe(df_movements, use_container_width=True)

        st.subheader("📦 Work-In-Progress (WIP) History")
        st.dataframe(results_df, use_container_width=True)
        
        # ... (rest of your existing metrics and logging logic)
