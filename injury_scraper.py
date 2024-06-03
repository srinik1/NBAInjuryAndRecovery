import numpy as np
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup

def replace_all(text, dic):
    '''
    This function will replace characters in text given a dictionary of characters to search for and replace
    '''
    rc = re.compile('|'.join(map(re.escape, dic)))

    def translate(match):
        return dic[match.group(0)]
    return rc.sub(translate, text)

# Dictionary of characters to remove from text
char_replace = {' • ': ''}

# Get total number of pages
base_url = 'https://www.prosportstransactions.com/basketball/Search/SearchResults.php'
params = {
    'Player': '',
    'Team': '',
    'BeginDate': '2021-10-19',
    'EndDate': '2024-06-03',
    'ILChkBx': 'yes',
    'Submit': 'Search',
    'start': 0
}

response = requests.get(base_url, params=params)
html = response.content
soup = BeautifulSoup(html, 'lxml')

# Look for page numbers at the bottom
page_links = soup.find_all('a', href=True, text=re.compile(r'^\d+$'))
if page_links:
    total_pages = max([int(link.text) for link in page_links])
else:
    # Fallback: Keep incrementing until no more results
    total_pages = 1
    while True:
        params['start'] = total_pages * 25
        response = requests.get(base_url, params=params)
        soup = BeautifulSoup(response.content, 'lxml')
        table = soup.find('table', attrs={'class': 'datatable center'})
        if not table or not table.findAll('tr', attrs={'align': 'left'}):
            break
        total_pages += 1

print(f"Total number of pages: {total_pages}")

# Create list of records read from webscraper
list_of_rows = []

# Loop through webpage table, scrap data, and store lists
for i in range(0, total_pages * 25, 25):
    params['start'] = i
    response = requests.get(base_url, params=params)
    html = response.content

    soup = BeautifulSoup(html, 'lxml')
    table = soup.find('table', attrs={'class': 'datatable center'})

    for row in table.findAll('tr', attrs={'align': 'left'}):
        list_of_cells = []

        for cell in row.findAll('td'):
            text = replace_all(cell.text, char_replace)
            text = text.strip()
            list_of_cells.append(text)
        list_of_rows.append(list_of_cells)

# Store data in a dataframe for manipulation
injuries_df = pd.DataFrame(list_of_rows, columns=[
                        'Date', 'Team', 'Acquired', 'Relinquished', 'Notes'])

acq = injuries_df['Acquired']
rel = injuries_df['Relinquished']

# Remove instances where value is like "Name 1/ Name 2"
injuries_df['Acquired'] = np.where(
    acq.str.contains('/'), acq.str.split('/ ').str[1], acq)
injuries_df['Relinquished'] = np.where(
    rel.str.contains('/'), rel.str.split('/ ').str[1], rel)

# Remove instances where value is like "(some text)"
injuries_df['Acquired'] = injuries_df.Acquired.str.replace(
    r"[\(\[].*?[\)\]]", "")
injuries_df['Relinquished'] = injuries_df.Relinquished.str.replace(
    r"[\(\[].*?[\)\]]", "")

# Write contents to csv file
injuries_df.to_csv('data/injuries_2021-2024.csv', index=False)
