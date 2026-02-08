import requests
import json
from bs4 import BeautifulSoup
import os

# --- CONFIGURATION ---
SKY_URL = "https://sport.sky.it/calcio/serie-a/probabili-formazioni"
FANTA_URL = "https://www.fantacalcio.it/probabili-formazioni-serie-a"
OUTPUT_FILE = "combined_lineups.json"

# Common headers to look like a real browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
}

def get_sky_data():
    """
    Fetches and parses the JSON model embedded in the Sky Sport HTML.
    """
    print(f"[Sky] Connecting to: {SKY_URL}...")
    try:
        response = requests.get(SKY_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Locate the specific tag containing the data model
        tag = soup.find('ld-football-scores-competition-predicted-lineups')
        
        if not tag or not tag.has_attr('model'):
            print("[Sky] Error: Could not find the predicted lineups data container.")
            return []

        # Extract and Parse the JSON string
        json_data_str = tag['model']
        data = json.loads(json_data_str)
        
        # Return the list of matches (usually under 'matchList')
        return data.get('matchList', [])

    except Exception as e:
        print(f"[Sky] Error: {e}")
        return []

def get_fantacalcio_data():
    """
    Scrapes Fantacalcio.it by parsing the HTML structure for matches, teams, and players.
    """
    print(f"[Fanta] Connecting to: {FANTA_URL}...")
    results = []
    
    try:
        response = requests.get(FANTA_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all match containers
        matches = soup.find_all("li", class_="match")
        
        for match in matches:
            match_info = {}
            
            # --- 1. Extract Team Names ---
            # Using meta tags inside the team labels as seen in the HTML snippet
            home_meta = match.select_one(".team-home .team-name meta[itemprop='name']")
            away_meta = match.select_one(".team-away .team-name meta[itemprop='name']")
            
            # Skip if names are not found (e.g. ad banners or empty blocks)
            if not home_meta or not away_meta:
                continue

            home_team = home_meta.get("content")
            away_team = away_meta.get("content")
            
            match_info["home_team"] = home_team
            match_info["away_team"] = away_team
            
            # --- 2. Extract Lineups (Pitch view) ---
            pitch = match.select_one(".pitch")
            match_info["lineups"] = {}

            if not pitch:
                continue

            if pitch:
                # Helper function to extract players from a specific side (home/away)
                def extract_team_details(side_class):
                    team_container = pitch.select_one(f".{side_class}")
                    if not team_container:
                        return {"module": "N/A", "starters": []}
                    
                    # Extract module (e.g., "3-5-2")
                    module = team_container.get("data-team-formation", "N/A")
                    
                    # Extract player names
                    player_nodes = team_container.select(".player .player-name span")
                    players = [p.get_text(strip=True) for p in player_nodes]
                    
                    return {"module": module, "starters": players}

                match_info["lineups"]["home"] = extract_team_details("team-home")
                match_info["lineups"]["away"] = extract_team_details("team-away")
            
            results.append(match_info)

        with open('output.json', 'w') as f:
            json.dump(results, f, indent=4)
            
        return results

    except Exception as e:
        print(f"[Fanta] Error: {e}")
        return []

def normalize_name(name):
    """
    Simple helper to normalize team names for comparison (lowercase, stripped).
    """
    if not name: return ""
    return name.lower().strip()

def integrate_and_save():
    # 1. Fetch data from both sources
    sky_matches = get_sky_data()
    fanta_matches = get_fantacalcio_data()
    
    combined_data = []

    print(f"\nMerging data... (Sky: {len(sky_matches)} matches, Fanta: {len(fanta_matches)} matches)")

    # 2. Iterate through Sky matches and try to find the corresponding Fantacalcio match
    # We use Sky as the "base" because its JSON structure is more detailed initially.
    for sky_match in sky_matches:
        
        # Get team names from Sky data (using correct field names: 'home' and 'away')
        sky_home_name = sky_match.get('home', {}).get('name', '')
        sky_away_name = sky_match.get('away', {}).get('name', '')
        
        sky_home = normalize_name(sky_home_name)
        sky_away = normalize_name(sky_away_name)
        
        # Create a combined object
        merged_match = {
            "match_name": f"{sky_home_name} - {sky_away_name}",
            "source_sky": sky_match,
            "source_fantacalcio": None # Default to None if not found
        }
        
        # Search for the matching game in Fantacalcio results
        for fanta_match in fanta_matches:
            fanta_home = normalize_name(fanta_match['home_team'])
            fanta_away = normalize_name(fanta_match['away_team'])
            
            # Check if team names match (using 'in' handles slight variations like "Verona" vs "Hellas Verona")
            # Match if both home teams match AND away teams match
            home_match = (sky_home in fanta_home) or (fanta_home in sky_home)
            away_match = (sky_away in fanta_away) or (fanta_away in sky_away)
            
            if home_match and away_match:
                merged_match["source_fantacalcio"] = fanta_match
                break
        
        combined_data.append(merged_match)

    # 3. Save to JSON
    print(f"Saving merged data to {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=4)
        
        print("\n" + "="*50)
        print(f"SUCCESS! Integrated data saved to '{os.path.abspath(OUTPUT_FILE)}'")
        print("="*50)
        
    except Exception as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    integrate_and_save()