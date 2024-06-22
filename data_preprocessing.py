import pandas as pd
import re
from season_dates import season_dates
import datetime

df = pd.read_csv('data/injuries_2021-2024.csv')

#Type of injury listed in notes. Preprocessing of the Notes column required to extract the type of injury
def preprocess_notes(note):
    note = re.sub(r'recovering from', 'with', note)
    return note

df['Notes'] = df['Notes'].apply(preprocess_notes)

#Function to extract the type of injury from Notes text
def extract_il_injury(note):
    match = re.search(r'placed on IL with (.+)', note)
    return match.group(1) if match else None

df['Injury'] = df['Notes'].apply(extract_il_injury)

def extract_any_injury(note):
    match = re.search(r'with surgery (?:on|to repair) (.+?)\s*(?:\(out for (?:the )?season\))?$', note)
    if match:
        return match.group(1), True
    match = re.search(r'with (.+?)\s*(?:\(out for (?:the )?season\))?$', note)
    if match:
        return match.group(1), False
    return None, None

#Check if player is out for the season due to the injury. Usually listed in '()' in the Notes text
def is_out_for_season(note):
    return bool(re.search(r'\(out for season\)$', note))

df['Injury'], df['Surgery'] = zip(*df['Notes'].apply(extract_any_injury))

#Listing all the different types on injuries into different buckets
def standardize_injury(injury):
    if pd.isna(injury):
        return None
    match = re.search(r'(.+) to (?:repair\s+)?(.+)', injury)
    if match:
        body_part, specific_injury = match.group(1), match.group(2)
        return f"{specific_injury} in {body_part}"
    return injury

df['Injury'] = df['Injury'].apply(standardize_injury)

def handle_surgery_in_injury(injury):
    if pd.isna(injury):
        return injury, False
    
    match = re.search(r'(.+?)\s*\(surgery\)$', injury)
    if match:
        return match.group(1), True
    
    return injury, False

# Apply the function to each injury
df['Injury'], df['temp_surgery'] = zip(*df['Injury'].apply(handle_surgery_in_injury))

# Update Surgery column
df.loc[df['Surgery'].isna(), 'Surgery'] = df['temp_surgery']
df.loc[~df['Surgery'].isna(), 'Surgery'] |= df['temp_surgery']

# Drop the temporary column
df.drop("temp_surgery", axis=1, inplace=True)

df['Out_For_Season'] = df['Notes'].apply(is_out_for_season)

df.drop("Notes", axis=1, inplace=True)
df["Date"] = pd.to_datetime(df["Date"]).dt.date
df["Days_Missed"] = pd.Series(dtype=pd.Int64Dtype())

relinquished = {}

for index, row in df.iterrows():
    if pd.notna(row["Relinquished"]) and not row["Surgery"]:
        relinquished[row['Relinquished']] = [row["Date"], row["Injury"]]
    elif pd.notna(row["Acquired"]) and row["Acquired"] in relinquished:
        row["Days_Missed"] = row["Date"] - relinquished[row['Acquired']][0]
        df.at[index, 'Days_Missed'] = row["Days_Missed"].days
        df.at[index,"Injury"] = relinquished[row['Acquired']][1]
        del relinquished[row['Acquired']]

new_df = df[pd.notna(df["Acquired"])][['Date', 'Team', 'Acquired', 'Injury', 'Surgery', 'Days_Missed']].copy()

# print(df.head())
new_df = new_df.rename(columns={'Acquired': 'Player_name'})
# print(len(new_df['Injury'].unique()))
# print(new_df.shape)
new_df['Injury'] = new_df['Injury'].fillna('Injury not known')
# print(new_df.head(50))

ofs_df = df[df["Out_For_Season"]==True].copy()


def parse_date(date_str):
    month, day = map(int, date_str.split('/'))
    return month, day

end_month, end_day = parse_date(season_dates['end_date'])

def calculate_days_missed(date):
    if not isinstance(date, datetime.date):
        date = pd.to_datetime(date).date()
    
    current_year_end = datetime.date(date.year, end_month, end_day)
    next_year_end = datetime.date(date.year + 1, end_month, end_day)
    
    if date > current_year_end:
        end_date = next_year_end
    else:
        end_date = current_year_end
    
    return (end_date - date).days

ofs_df['Days_Missed'] = ofs_df['Date'].apply(calculate_days_missed)
ofs_df.drop(['Acquired', 'Out_For_Season'], axis = 1, inplace = True)
ofs_df = ofs_df.rename(columns={'Relinquished': 'Player_name'})

combined_df = pd.concat([new_df, ofs_df], ignore_index=True)
combined_df = combined_df.sort_values('Date', ascending=True)
# print(ofs_df.head())
# print(new_df.head())
combined_df = combined_df.dropna(subset=['Days_Missed'])
# print(combined_df.head(20))
# print(combined_df.shape)
