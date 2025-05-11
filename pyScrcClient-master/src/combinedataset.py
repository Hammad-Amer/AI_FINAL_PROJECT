import pandas as pd

expected_columns = [
    'time', 'speedX', 'speedY', 'speedZ', 'rpm', 'gear', 'steer', 'accel', 'brake',
    'trackPos', 'angle', 'distFromStart', 'trackDist', 'focusLeft', 'focusCenter', 'focusRight',
    'fuel', 'damage', 'racePos', 'wheelSpinFL', 'wheelSpinFR', 'wheelSpinRL', 'wheelSpinRR'
] + [f'track{i}' for i in range(19)] + [f'opponent{i+1}_dist' for i in range(5)]

# Input CSVs
csv_files = [
    'newtrainingdata/corolla-oval1.csv',
    'newtrainingdata/corolla-oval2.csv',
    'newtrainingdata/corolla-road1.csv',
    'newtrainingdata/corolla-road2.csv',
    'newtrainingdata/corolla-road3.csv',
    'newtrainingdata/corolla-road4.csv',
    'newtrainingdata/corolla-road5.csv',
    'newtrainingdata/corolla-road6.csv',
    'newtrainingdata/Dirt_corolla.csv',
    'newtrainingdata/Dirt_lancer.csv',
    'newtrainingdata/Dirt_p406.csv',
    'newtrainingdata/mitsubishi-road1.csv',
    'newtrainingdata/mitsubishi-road2.csv',
    'newtrainingdata/mitsubishi-road3.csv',
    'newtrainingdata/mitsubishi-road4.csv',
    'newtrainingdata/mitsubishi-road5.csv',
    'newtrainingdata/mitsubishi-road6.csv',
    'newtrainingdata/Oval_lancer.csv',
    'newtrainingdata/Oval_p406.csv',
    'newtrainingdata/p406-road1.csv',
    'newtrainingdata/p406-road2.csv',
    'newtrainingdata/p406-road3.csv',
    'newtrainingdata/p406-road4.csv',
    'newtrainingdata/p406-road5.csv',
    'newtrainingdata/p406-road6.csv'
]

dfs = []


df0 = pd.read_csv(csv_files[0])
df0 = df0[df0.columns.intersection(expected_columns)]  
dfs.append(df0)

for file in csv_files[1:]:
    df = pd.read_csv(file, skiprows=1, header=None) 
    df.columns = expected_columns[:len(df.columns)]  
    df = df[df.columns.intersection(expected_columns)]
    dfs.append(df)

combined_df = pd.concat(dfs, ignore_index=True)

combined_df = combined_df[expected_columns]

combined_df = combined_df.apply(pd.to_numeric, errors='coerce')
combined_df = combined_df.dropna()

combined_df.to_csv("combined_data.csv", index=False)
print("✅ Cleaned combined CSV saved as combined_data.csv")
