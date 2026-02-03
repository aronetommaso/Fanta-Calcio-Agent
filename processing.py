import json
import os
from fpdf import FPDF

# --- CONFIGURATION ---
INPUT_FILE = "probabili_formazioni.json"
OUTPUT_FILE = "dataset_rag.pdf"

def get_player_names(team_data):
    """
    Extracts the names of starting players based on the specific JSON structure provided.
    Path: team -> playerList -> startingLineup (List)
    """
    starters = []
    
    try:
        # Access the playerList object directly
        player_list_obj = team_data.get('playerList', {})
        
        # Access the startingLineup list directly
        starting_lineup = player_list_obj.get('startingLineup', [])
        
        # Loop through the list of players
        for player in starting_lineup:
            # Combine name and surname
            name = player.get('name', '')
            surname = player.get('surname', '')
            full_name = f"{name} {surname}".strip()
            
            role = player.get('role', 'Unknown')
            
            # Format: Name Surname (Role)
            if full_name:
                starters.append(f"{full_name} ({role})")
                
    except Exception as e:
        print(f"Error extracting players: {e}")
        
    return starters

def format_match_text(match):
    """
    Formats a single match object into a descriptive text block optimized for RAG.
    """
    # Extract basic match info
    # Note: The JSON uses 'home' and 'away', not 'homeTeam'/'awayTeam'
    home_team = match.get('home', {}).get('name', 'Home Team')
    away_team = match.get('away', {}).get('name', 'Away Team')
    date = match.get('date', 'Date not available')
    
    # Extract lineups using the new logic
    home_starters = get_player_names(match.get('home', {}))
    away_starters = get_player_names(match.get('away', {}))
    
    # Handle cases where lineups might be empty (to avoid empty strings)
    home_lineup_str = ', '.join(home_starters) if home_starters else "Data not available"
    away_lineup_str = ', '.join(away_starters) if away_starters else "Data not available"

    # Create the semantic text block
    text_block = (
        f"MATCH: {home_team} vs {away_team}\n"
        f"DATE: {date}\n"
        f"STARTING LINEUP {home_team.upper()}: {home_lineup_str}.\n"
        f"STARTING LINEUP {away_team.upper()}: {away_lineup_str}.\n"
        f"NOTES: Predicted Serie A lineup for the match between {home_team} and {away_team}."
    )
    
    return text_block

def transform_json_to_docs():
    """
    Main function: loads the JSON file, processes each match, and writes
    the output to a text file ready for embedding.
    """
    if not os.path.exists(INPUT_FILE):
        print(f"Error: The file {INPUT_FILE} does not exist.")
        return

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # The matches are inside 'matchList'
        matches = data.get('matchList', [])
        documents = []

        print(f"Processing {len(matches)} matches...")

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        for match in matches:
            doc_text = format_match_text(match)
            # Encode to latin-1 to handle accents with standard fonts
            safe_text = doc_text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, safe_text)
            pdf.ln(5)
            pdf.cell(0, 10, "---", ln=True)
            pdf.ln(5)
            documents.append(doc_text)

        pdf.output(OUTPUT_FILE)

        print(f"Done! Data saved to '{OUTPUT_FILE}'.")
        print("-" * 30)
        print("PREVIEW OF THE FIRST GENERATED DOCUMENT:")
        print("-" * 30)
        if documents:
            print(documents[0])
            
    except json.JSONDecodeError:
        print("Error: The JSON file is corrupted or incomplete. Please run the scraper again.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    transform_json_to_docs()