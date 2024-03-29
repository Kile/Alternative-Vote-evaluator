# MIT License
#
# Copyright (c) 2024, Erik
# All rights reserved.

import pandas as pd
import requests
from io import StringIO
from typing import Dict, List
from numpy import nan
import logging

logging.basicConfig(filename='process.log', level=logging.INFO)

def get_data(url: str) -> pd.DataFrame:
    """Fetch data from a google spreadsheet"""
    # Get the id of the google spreadsheet
    id = url.split('/')[-2]

    # Get the data from the google spreadsheet
    response = requests.get(f"https://docs.google.com/spreadsheets/d/{id}/gviz/tq?tqx=out:csv")
    data = pd.read_csv(StringIO(response.content.decode('utf-8')))

    return data

def parse_sheet(df: pd.DataFrame) -> Dict[str, Dict[str, Dict[int, int]]]:
    """
    From the spreadsheet data, parse into dictionary in this format:
    {
        "<role>": {
            "<name>": {
                1: <score>,
                2: <score>,
                // ...
            },
            // ...
        }
    }
    """
    data = {}

    # Iterate over each column in the DataFrame
    for column in df.columns:
        if "[" not in column:
            continue

        role, field_number = column.split(' [')
        field_number = int(field_number[0])  # Extract the field number from column name
        
        # Initialize dictionaries if not present
        if role not in data:
            data[role] = {}

        # Iterate over each row in the column
        for index, value in df[column].items():
            if not pd.isna(value):  # Ignore NaN values
                name = value
                if name not in data[role]:
                    data[role][name] = {}

                # Check if previous fields are filled
                previous_fields = [f"{role} [{i}]" for i in range(1, field_number)]
                if all(df[field].iloc[index] not in (nan, '') for field in previous_fields):
                    if field_number not in data[role][name]:
                        data[role][name][field_number] = 1
                    else:
                        data[role][name][field_number] += 1

    return data

def log_parsed(parsed: Dict[str, Dict[str, Dict[int, int]]]) -> None:
    """
    Log the parsed data in a readable format to a file for later reference.
    
    """
    logging.info("Parsed data from spreadsheet:")
    for role, data in parsed.items():
        logging.info(f"Role: {role}")
        for name, fields in data.items():
            logging.info(f"\t{name}")
            for field, score in fields.items():
                logging.info(f"\t\t{field}: {score}")

def determine_winner(
        parsed: Dict[str, Dict[str, Dict[int, int]]], 
        excluded: Dict[str, str | List[str]] = {}
        ) -> Dict[str, str]:
    """
    Returns the winner of each role based on the parsed data. 
    Excludes the names for the role specified in the excluded dictionary.
    """
    logging.info("Determining winners:")
    winners = {}

    for role, data in parsed.items():
        # Check if there is only one non excluded candidate left
        match len(data) - len(excluded.get(role, [])):
            case 0: # This will happen if no one voted for RON
                winner = "RON"
                winners[role] = winner
                logging.info(f"Winner for {role} determined by default: {winner}")
                continue
            case 1: 
                winner = [name for name in data if name not in excluded.get(role, [])][0]
                winners[role] = winner
                logging.info(f"Winner for {role} determined by default: {winner}")
                continue

        # Loop over each voting rnd (eg 1-MAX key in data.values)
        for rnd in range(1, max(max(fields.keys(), default=0) for fields in data.values()) + 1):
            # Find the max value for that rnd and total votes
            max_score_name = None
            max_score = 0
            total_votes = 0
            for name, fields in data.items():
                if name in excluded.get(role, []) or name == excluded.get(role, None):
                    continue
                if rnd in fields:
                    total_votes += fields[rnd]
                    if fields[rnd] > max_score:
                        max_score = fields[rnd]
                        max_score_name = name
            # If max_score is bigger or equal to half of the total votes, declare a winner
            if max_score >= total_votes / 2:
                winners[role] = max_score_name
                logging.info(
                    f"Winner for {role} found in round {rnd}: {max_score_name} with {max_score} votes ({max_score/total_votes*100:.2f}%)"
                )
                break # Do not go to the next rnd if a winner is declared

        # If no winner is found, declare the one with the most votes
        if role not in winners:
            winner = max(data, key=lambda x: sum(data[x].values()))
            winners[role] = winner

    return winners

def find_winners(parsed: Dict[str, Dict[str, Dict[int, int]]]) -> Dict[str, str]:
    # Determine initial winners
    winners = determine_winner(parsed)

    # Check if any name won twice
    while (
            invalid := {
                name: role for role, name in winners.items() 
                if list(winners.values()).count(name) > 1 and 
                name.upper() != "RON" # RON can win multiple roles
            }
        ):
        logging.error("One or more names won more than once. Re-running counting with preferences.")
        # Open first_choices.txt, extract the first choices and add second one to excluded
        excluded: Dict[str, List[str]] = {}

        with open('first_choices.txt', 'r') as f:
            for line in f:
                name, first_choice = line.strip().split(':')
                # Exclude from role that is NOT first_choice
                # if name is in invalid
                for inavlid_name, role in invalid.items():
                    if role.lower() != first_choice.strip().lower() and inavlid_name.lower() == name.lower().strip():
                        if role not in excluded:
                            excluded[role] = [name.strip()]
                        else:
                            excluded[role].append(name.strip())
                        logging.info(f"Excluding {name} from {role} because {first_choice} is the first choice but {name} won both.")

        winners = determine_winner(parsed, excluded)

    return winners

def print_winners(winners: Dict[str, str]) -> None:
    """
    Print the winners in a readable format.
    """
    print("Winners:")
    for role, name in winners.items():
        print(f"{role}: {name}")
            
def main():
    # Error if there is no first_choices.txt
    try:
        with open('first_choices.txt', 'r') as f:
            pass
    except FileNotFoundError:
        logging.error("first_choices.txt not found. Please create the file and add the first choices.")
        print("first_choices.txt not found. Please create the file and add the first choices in the format:")
        print("name: role")
        print("name: role")
        print("...")
        return
    
    # Clear log file
    open('process.log', 'w').close()

    # Ask for link to a google spreadsheet
    url = input("Enter the link to the google spreadsheet: ")

    # Get the data from the google spreadsheet
    data = get_data(url)
    # Parse sheet
    parsed = parse_sheet(data)
    # Log parsed data
    log_parsed(parsed)
    # Find winners
    winners = find_winners(parsed)

    logging.info("Winners declared successfully.")
    logging.info("Total form responses: " + str(len(data)))
    print_winners(winners)

if __name__ == "__main__":
    main()