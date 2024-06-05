import pandas as pd
import re

df = pd.read_csv('data/injuries_2021-2024.csv')

def extract_il_injury(note):
    match = re.search(r'placed on IL with (.+)', note)
    return match.group(1) if match else None

df['Injury'] = df['Notes'].apply(extract_il_injury)

def extract_any_injury(note):
    match = re.search(r'with surgery on (.+)', note)
    if match:
        return match.group(1), True
    match = re.search(r'with (.+)', note)
    if match:
        return match.group(1), False
    return None, None

df['Injury'], df['Surgery'] = zip(*df['Notes'].apply(extract_any_injury))
df.drop("Notes", axis=1, inplace=True)
df["Date"] = pd.to_datetime(df["Date"]).dt.date
df["Days_Missed"] = pd.NaT

relinquished = {}

for index, row in df.iterrows():
    if pd.notna(row["Relinquished"]) and not row["Surgery"]:
        relinquished[row['Relinquished']] = [row["Date"], row["Injury"]]
    elif pd.notna(row["Acquired"]) and row["Acquired"] in relinquished:
        row["Days_Missed"] = row["Date"] - relinquished[row['Acquired']][0]
        df.at[index, 'Days_Missed'] = row["Days_Missed"].days
        df.at[index,"Injury"] = relinquished[row['Acquired']][1]
        del relinquished[row['Acquired']]

print(df.head())
# new_df = df[pd.notna(df["Acquired"])][['Team', 'Acquired', 'Injury', 'Surgery', 'Days_Missed']].copy()
