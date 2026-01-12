import pandas as pd
import numpy as np

# 1. Custom Setup via User Input
print("--- Setup Station Dice Ranges ---")
members = ['A', 'B', 'C', 'D', 'E']
dice_ranges = {}

for m in members:
    low = int(input(f"Enter MIN dice value for Station {m}: "))
    high = int(input(f"Enter MAX dice value for Station {m}: "))
    dice_ranges[m] = (low, high)

print("\n--- Setup Initial WIP (Day 1) ---")
initial_wip = {
    "AB": int(input("Initial WIP between A and B: ")),
    "BC": int(input("Initial WIP between B and C: ")),
    "CD": int(input("Initial WIP between C and D: ")),
    "DE": int(input("Initial WIP between D and E: "))
}

# 2. Generate Dice Rolls based on custom ranges
days = 20
dice_data = {m: [np.random.randint(dice_ranges[m][0], dice_ranges[m][1] + 1) for _ in range(days)] for m in members}
df_dice = pd.DataFrame(dice_data)
df_dice.index += 1
df_dice.index.name = "Day"

print("\n--- Generated Dice Rolls ---")
print(df_dice)

# 3. Simulation Logic
wip = initial_wip.copy()
history = []
total_finished_goods = 0

for day in df_dice.index:
    rolls = df_dice.loc[day]
    
    # Station A: Takes from RM and adds to WIP_AB
    # (A is unique because it pulls from infinite Raw Material)
    move_A = rolls['A']
    wip["AB"] += move_A
    
    # Station B: Moves from AB to BC
    move_B = min(rolls['B'], wip["AB"])
    wip["AB"] -= move_B
    wip["BC"] += move_B
    
    # Station C: Moves from BC to CD
    move_C = min(rolls['C'], wip["BC"])
    wip["BC"] -= move_C
    wip["CD"] += move_C
    
    # Station D: Moves from CD to DE
    move_D = min(rolls['D'], wip["CD"])
    wip["CD"] -= move_D
    wip["DE"] += move_D
    
    # Station E: Moves from DE to Finished Goods
    move_E = min(rolls['E'], wip["DE"])
    wip["DE"] -= move_E
    
    daily_fg = move_E
    total_finished_goods += daily_fg
    daily_total_wip = sum(wip.values())
    
    history.append({
        "Day": day,
        "WIP_AB": wip["AB"],
        "WIP_BC": wip["BC"],
        "WIP_CD": wip["CD"],
        "WIP_DE": wip["DE"],
        "Daily_Total_WIP": daily_total_wip,
        "Daily_FG": daily_fg
    })

# 4. Results
results_df = pd.DataFrame(history).set_index("Day")
print("\n--- Simulation Results ---")
print(results_df)
print(f"\nTOTAL FINISHED GOODS: {total_finished_goods}")
