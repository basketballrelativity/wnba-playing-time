"""
This script leverages play-by-play and box score
data to infer which players are on the court
at all times
"""
from typing import List, Tuple

import pandas as pd

import data

def get_rosters(home_team_id: int, visitor_team_id: int, box_score_df: pd.DataFrame) -> Tuple[List[int], List[int]]:
    """
    Get the rosters for the home and visitor teams.

    Args:
        home_team_id (int): The ID of the home team.
        visitor_team_id (int): The ID of the visitor team.
        box_score_df (pd.DataFrame): DataFrame containing box score data.

    Returns:
        pd.DataFrame: DataFrame containing player IDs for both teams.
    """
    home_roster = box_score_df[box_score_df['team_id'] == home_team_id]
    visitor_roster = box_score_df[box_score_df['team_id'] == visitor_team_id]

    return list(home_roster['player_id']), list(visitor_roster['player_id'])


def main(game_id: int) -> pd.DataFrame:
    """
    Main function to process the game data and return the players on the court.
    
    Args:
        game_id (int): The ID of the game to process.
    
    Returns:
        pd.DataFrame: DataFrame containing players on the court at each timestamp.
    """

    # Ingest data
    pbp_df = data.ingest_pbp_data(game_id)
    box_score_df = data.ingest_box_score_data(game_id)
    game_df = data.ingest_game_data(game_id)

    # Get rosters
    home_roster, visitor_roster = get_rosters(
        game_df['home_team_id'].values[0],
        game_df['visitor_team_id'].values[0],
        box_score_df
    )

    return None


if __name__ == "__main__":
    main(None)