import requests
import json
from bs4 import BeautifulSoup
import os

# --- CONFIGURATION ---
TARGET_URL = "https://sport.sky.it/calcio/serie-a/probabili-formazioni"
OUTPUT_FILE = "probabili_formazioni.json"

# Headers are required to mimic a real browser request and avoid being blocked (403 Forbidden)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
}

def fetch_and_save_lineups():
    print(f"Connecting to: {TARGET_URL}...")
    
    try:
        # 1. Request the webpage
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=10)
        response.raise_for_status() # Raise error for bad status codes (4xx, 5xx)
        
        # 2. Parse HTML content
        print("Parsing HTML content...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. Locate the specific tag containing the data model
        # Sky Sport stores the data in the 'model' attribute of this custom tag
        tag = soup.find('ld-football-scores-competition-predicted-lineups')
        
        if not tag or not tag.has_attr('model'):
            print("Error: Could not find the predicted lineups data container in the HTML.")
            return

        # 4. Extract and Parse the JSON string
        print("Extracting data model...")
        json_data_str = tag['model']
        data = json.loads(json_data_str)
        
        # 5. (Optional) Filter or Clean Data structure if needed
        # Currently, we save the full structure including match list, home/away teams, starters, etc.
        # The relevant path for starters is: match -> home/away -> playerList -> startingLineup
        
        # 6. Save to JSON file
        print(f"Saving data to {OUTPUT_FILE}...")
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("\n" + "="*50)
        print(f"SUCCESS! Data saved to '{os.path.abspath(OUTPUT_FILE)}'")
        print("="*50)
        
        # 7. Print a quick summary to console
        matches_count = len(data.get('matchList', []))
        print(f"Extracted {matches_count} matches.")

    except requests.exceptions.RequestException as e:
        print(f"Network Error: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON Error (failed to parse model attribute): {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    fetch_and_save_lineups()