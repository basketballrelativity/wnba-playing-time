"""
This script processes play-by-play and box score
data to infer which players are on the court
at all times
"""

import pandas as pd


def play_clock_to_seconds(play_clock: str, period: int) -> int:
    """
    Convert play clock time from "MM:SS" format to total seconds.

    Args:
        play_clock (str): Time in "MM:SS" format.
        period (int): Current period of the game.
    
    Returns:
        int: Total seconds.
    """

    # Split time string
    pc_split = play_clock.split(":")

    # Convert to seconds
    minutes = int(pc_split[0])
    seconds = float(pc_split[1])

    # Account for the quarter to get total game time remaining
    if period <= 4:
        period_time = 10 * (4 - period) * 60
        max_period_time = 10 * (5 - period) * 60
    else:
        period_time = 0
        max_period_time = 5 * 60

    return period_time + (minutes * 60 + seconds), max_period_time


def process_pbp_data(pbp_df: pd.DataFrame, home_roster: pd.DataFrame, visitor_roster: pd.DataFrame, home_id: int, visitor_id: int) -> pd.DataFrame:
    """
    Process play-by-play data to infer player court
    presence using substitution logic.

    Args:
        pbp_df (pd.DataFrame): Play-by-play data.
        home_roster (pd.DataFrame): Home team roster.
        visitor_roster (pd.DataFrame): Visitor team roster.
        home_id (int): Home team ID.
        visitor_id (int): Visitor team ID.
    
    Returns:
        pd.DataFrame: Updated play-by-play data with
        inferred player court presence.
    """
    # Initialize objects
    home_on_court = []
    visitor_on_court = []
    period = 1

    # Initialize game time remaining
    pbp_df["game_time_remaining"] = [play_clock_to_seconds(x, y)[0] for x, y in zip(pbp_df["pctimestring"], pbp_df["period"])]
    pbp_df = pbp_df.sort_values(by=["game_time_remaining", "period", "eventnum"], ascending=[False, True, True]).reset_index(drop=True)

    # Initialize playing time bank
    time_on_court = {}
    for player_id in home_roster + visitor_roster:
        time_on_court[player_id] = {"playing_time": 0, "time_in": None, "time_in_list": [], "time_out_list": [], "period_list": []}

    for index, row in pbp_df.iterrows():
        # For substitutions, update on-court players
        game_time_remaining, max_period_time = play_clock_to_seconds(row["pctimestring"], row["period"])
        if row["eventmsgtype"] == 8:
            if row["player1_team_id"] == home_id:
                if row["player1_id"] in home_on_court:
                    home_on_court.remove(row["player1_id"])
                if row["player2_id"] not in home_on_court:
                    home_on_court.append(row["player2_id"])
                print(f"Subbing home: {row['player2_id']} in for {row['player1_id']}")
            else:
                if row["player1_id"] in visitor_on_court:
                    visitor_on_court.remove(row["player1_id"])
                if row["player2_id"] not in visitor_on_court:
                    visitor_on_court.append(row["player2_id"])
                print(f"Subbing visitor: {row['player2_id']} in for {row['player1_id']}")

            # Update playing time bank for player 1
            if pd.isnull(time_on_court[row["player1_id"]]["time_in"]):
                time_on_court[row["player1_id"]]["playing_time"] += (max_period_time - game_time_remaining)
                time_on_court[row["player1_id"]]["time_in_list"].append(max_period_time)
            else:
                time_on_court[row["player1_id"]]["playing_time"] += (time_on_court[row["player1_id"]]["time_in"] - game_time_remaining)
            
            time_on_court[row["player1_id"]]["time_in"] = None
            time_on_court[row["player1_id"]]["time_out_list"].append(game_time_remaining)
            time_on_court[row["player1_id"]]["period_list"].append(period)

            # Update playing time bank for player 2
            time_on_court[row["player2_id"]]["time_in"] = game_time_remaining
            time_on_court[row["player2_id"]]["time_in_list"].append(game_time_remaining)
        elif row["eventmsgtype"] == 13:
            # End of period - update playing time for all on-court players
            for player_id in home_on_court + visitor_on_court:
                time_on_court[player_id]["playing_time"] += (time_on_court[player_id]["time_in"] - game_time_remaining)
                time_on_court[player_id]["time_in"] = None
                time_on_court[player_id]["time_out_list"].append(game_time_remaining)
                time_on_court[player_id]["period_list"].append(period)

            period += 1
            home_on_court = []
            visitor_on_court = []
        elif row["eventmsgtype"] <= 5:
            for player_id in [row["player1_id"], row["player2_id"], row["player3_id"]]:
                if pd.isnull(player_id):
                    continue
                if player_id in home_roster and player_id not in home_on_court:
                    home_on_court.append(player_id)
                    time_on_court[player_id]["time_in"] = max_period_time
                    time_on_court[player_id]["time_in_list"].append(max_period_time)
                elif player_id in visitor_roster and player_id not in visitor_on_court:
                    visitor_on_court.append(player_id)
                    time_on_court[player_id]["time_in"] = max_period_time
                    time_on_court[player_id]["time_in_list"].append(max_period_time)

    sub_df = pd.DataFrame()
    for player_id in time_on_court:
        if player_id in home_roster:
            team_id = home_id
        else:
            team_id = visitor_id
        temp_df = pd.DataFrame(
            {
                "player_id": [player_id] * len(time_on_court[player_id]["time_in_list"]),
                "team_id": [team_id] * len(time_on_court[player_id]["time_in_list"]),
                "time_in": time_on_court[player_id]["time_in_list"],
                "time_out": time_on_court[player_id]["time_out_list"],
            }
        )
        sub_df = pd.concat([sub_df, temp_df], ignore_index=True)

    return sub_df, pbp_df

def assign_players_on_court(sub_df: pd.DataFrame, pbp_df: pd.DataFrame, home_id: int, visitor_id: int) -> pd.DataFrame:
    """
    Assign players on the court for each play-by-play event.

    Args:
        sub_df (pd.DataFrame): DataFrame containing substitution events.
        pbp_df (pd.DataFrame): Play-by-play data.
        home_id (int): Home team ID.
        visitor_id (int): Visitor team ID.

    Returns:
        pd.DataFrame: Updated play-by-play data with players on the court.
    """

    player_df = pd.DataFrame()
    for index, row in pbp_df.iterrows():
        for team_id, label_id in zip([home_id, visitor_id], ["home", "visitor"]):
            team_sub_df = sub_df[sub_df["team_id"] == team_id]

            if row["eventmsgtype"] == 13:
                on_court_players = team_sub_df[
                    team_sub_df["time_out"] == row["game_time_remaining"]
                ]["player_id"].tolist()
            elif row["eventmsgtype"] == 8:
                on_court_players = team_sub_df[
                    (team_sub_df["time_in"] >= row["game_time_remaining"]) & (team_sub_df["time_out"] < row["game_time_remaining"])
                ]["player_id"].tolist()
            else:
                on_court_players = team_sub_df[
                    (team_sub_df["time_in"] >= row["game_time_remaining"]) & (team_sub_df["time_out"] <= row["game_time_remaining"])
                ]["player_id"]
                if len(on_court_players) > 5:
                    on_court_players = team_sub_df[
                        (team_sub_df["time_in"] > row["game_time_remaining"]) & (team_sub_df["time_out"] <= row["game_time_remaining"])
                    ]["player_id"].tolist()
                else:
                    on_court_players = on_court_players.tolist()
            
            assert len(on_court_players) == 5, f"More than 5 players on court for team {team_id} at event {index}"
            temp_df = pd.DataFrame(
                {
                    "game_id": [row["game_id"]],
                    "eventnum": [row["eventnum"]],
                    f"{label_id}_player_1": [on_court_players[0]],
                    f"{label_id}_player_2": [on_court_players[1]],
                    f"{label_id}_player_3": [on_court_players[2]],
                    f"{label_id}_player_4": [on_court_players[3]],
                    f"{label_id}_player_5": [on_court_players[4]]
                }
            )
            if label_id == "home":
                row_df = temp_df
            else:
                row_df = row_df.merge(temp_df, on=["game_id", "eventnum"])

        player_df = pd.concat([player_df, row_df], ignore_index=True)

    return player_df