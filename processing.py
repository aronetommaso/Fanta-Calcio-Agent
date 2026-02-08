import json
import os
from fpdf import FPDF

# --- CONFIGURATION ---
INPUT_FILE = "combined_lineups.json"  # Ensure this matches the output of the previous script
OUTPUT_FILE = "dataset_rag.pdf"

def get_sky_players(team_data):
    """
    Extracts players from the Sky Sport data structure.
    Path: team -> playerList -> startingLineup (list of dicts)
    """
    if not team_data:
        return "Data not available"

    starters = []
    try:
        # Sky puts the lineup inside playerList.startingLineup
        player_list_obj = team_data.get('playerList', {})
        starting_lineup = player_list_obj.get('startingLineup', [])
        
        for player in starting_lineup:
            # Extract player info
            name = player.get('name', '')
            surname = player.get('surname', '')
            role = player.get('role', 'N/A')
            full_name = f"{name} {surname}".strip()
            
            if full_name:
                starters.append(f"{full_name} ({role})")
                
    except Exception as e:
        return f"Error extracting Sky players: {e}"

    return ", ".join(starters) if starters else "No players found"

def get_sky_unavailables(team_data):
    """
    Extracts unavailable/injured players from Sky Sport data.
    """
    if not team_data:
        return ""
    
    try:
        player_list_obj = team_data.get('playerList', {})
        unavailables_list = player_list_obj.get('unavailables', [])
        
        unavailable_names = []
        for item in unavailables_list:
            fullname = item.get('fullname', '').strip()
            if fullname:
                unavailable_names.append(fullname)
        
        if unavailable_names:
            return ", ".join(unavailable_names)
    except:
        pass
    
    return ""

def get_sky_substitutes(team_data):
    """
    Extracts substitute players from Sky Sport data.
    """
    if not team_data:
        return ""
    
    try:
        player_list_obj = team_data.get('playerList', {})
        substitutes_list = player_list_obj.get('substitutes', [])
        
        sub_names = []
        for item in substitutes_list:
            fullname = item.get('fullname', '').strip()
            if fullname:
                sub_names.append(fullname)
        
        if sub_names:
            return ", ".join(sub_names)
    except:
        pass
    
    return ""

def format_match_text(match_entry):
    """
    Formats a single match entry (containing both Sky and Fanta data) 
    into a structured text block optimized for RAG.
    """
    match_name = match_entry.get('match_name', 'Unknown Match')
    
    # --- 1. Process Sky Data ---
    sky_data = match_entry.get('source_sky', {})
    if sky_data:
        # CORRECT: use 'home' and 'away' instead of 'homeTeam' and 'awayTeam'
        sky_home = sky_data.get('home', {})
        sky_away = sky_data.get('away', {})
        
        sky_home_name = sky_home.get('name', 'Home')
        sky_away_name = sky_away.get('name', 'Away')
        sky_home_formation = sky_home.get('formation', 'N/A')
        sky_away_formation = sky_away.get('formation', 'N/A')
        
        sky_home_lineup = get_sky_players(sky_home)
        sky_away_lineup = get_sky_players(sky_away)
        
        # Additional info
        sky_home_unavailables = get_sky_unavailables(sky_home)
        sky_away_unavailables = get_sky_unavailables(sky_away)
        sky_home_subs = get_sky_substitutes(sky_home)
        sky_away_subs = get_sky_substitutes(sky_away)
        
        sky_block = (
            f"SOURCE 1: SKY SPORT\n"
            f"   HOME TEAM: {sky_home_name} (Formation: {sky_home_formation})\n"
            f"   - Starting XI: {sky_home_lineup}\n"
        )
        if sky_home_unavailables:
            sky_block += f"   - Unavailable: {sky_home_unavailables}\n"
        if sky_home_subs:
            sky_block += f"   - Substitutes: {sky_home_subs}\n"
            
        sky_block += (
            f"\n   AWAY TEAM: {sky_away_name} (Formation: {sky_away_formation})\n"
            f"   - Starting XI: {sky_away_lineup}\n"
        )
        if sky_away_unavailables:
            sky_block += f"   - Unavailable: {sky_away_unavailables}\n"
        if sky_away_subs:
            sky_block += f"   - Substitutes: {sky_away_subs}\n"
    else:
        sky_block = "SOURCE 1: SKY SPORT\n   - Data not available."

    # --- 2. Process Fantacalcio Data ---
    fanta_data = match_entry.get('source_fantacalcio')
    if fanta_data:
        # Fanta data structure based on the previous script
        fanta_home_team = fanta_data.get('home_team', 'Home')
        fanta_away_team = fanta_data.get('away_team', 'Away')
        lineups = fanta_data.get('lineups', {})
        
        # Home
        home_mod = lineups.get('home', {}).get('module', 'N/A')
        home_players = lineups.get('home', {}).get('starters', [])
        home_players_str = ", ".join(home_players) if home_players else "No players found"
        
        # Away
        away_mod = lineups.get('away', {}).get('module', 'N/A')
        away_players = lineups.get('away', {}).get('starters', [])
        away_players_str = ", ".join(away_players) if away_players else "No players found"
        
        fanta_block = (
            f"\nSOURCE 2: FANTACALCIO.IT\n"
            f"   HOME TEAM: {fanta_home_team} (Module: {home_mod})\n"
            f"   - Starting XI: {home_players_str}\n"
            f"\n   AWAY TEAM: {fanta_away_team} (Module: {away_mod})\n"
            f"   - Starting XI: {away_players_str}"
        )
    else:
        fanta_block = "\nSOURCE 2: FANTACALCIO.IT\n   - Data not matched or not available."

    # --- 3. Combine into a single semantic block ---
    text_block = (
        f"\n{'='*60}\n"
        f"MATCH: {match_name}\n"
        f"{'='*60}\n"
        f"{sky_block}\n"
        f"{fanta_block}\n"
        f"{'-'*60}\n"
    )
    
    return text_block

def transform_json_to_pdf():
    """
    Main function: loads the combined JSON, processes matches, 
    and generates a PDF.
    """
    if not os.path.exists(INPUT_FILE):
        print(f"Error: The file {INPUT_FILE} does not exist. Run the scraper first.")
        return

    try:
        print(f"Reading {INPUT_FILE}...")
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # The new JSON root is a list, not a dict with 'matchList'
        matches = data if isinstance(data, list) else []
        
        if not matches:
            print("Warning: No matches found in the JSON file.")
            return

        print(f"Processing {len(matches)} matches...")

        # Initialize PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=9)
        
        # Add title
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Serie A - Probabili Formazioni", ln=True, align='C')
        pdf.ln(5)
        pdf.set_font("Arial", size=9)

        for idx, match in enumerate(matches, 1):
            # Generate the text block
            doc_text = format_match_text(match)
            
            # Sanitize text for FPDF (Standard FPDF doesn't support UTF-8 directly)
            # We encode to latin-1 and replace unknown chars (like emojis or weird accents) with '?'
            safe_text = doc_text.encode('latin-1', 'replace').decode('latin-1')
            
            # Write to PDF
            pdf.multi_cell(0, 5, safe_text)
            pdf.ln(2) # Add a small gap between matches
            
            print(f"  [{idx}/{len(matches)}] Processed: {match.get('match_name', 'Unknown')}")

        # Save PDF
        pdf.output(OUTPUT_FILE)

        print(f"\n{'='*60}")
        print(f"SUCCESS! PDF saved to '{os.path.abspath(OUTPUT_FILE)}'")
        print(f"{'='*60}")
        
    except json.JSONDecodeError:
        print("Error: The JSON file is corrupted.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    transform_json_to_pdf()