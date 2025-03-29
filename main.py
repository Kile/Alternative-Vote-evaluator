"""
The MIT License (MIT)

Copyright (c) 2024-present Erik

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import pandas as pd
import requests
from io import StringIO
from typing import Dict, List
from numpy import nan
import logging
from copy import deepcopy

logging.basicConfig(filename="process.log", level=logging.INFO)


class Tie(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"TIE: {' and '.join(self)}"


def file_exists(file_path: str) -> bool:
    """
    Check if a file exists

    Parameters
    ----------
    file_path: :class:`str`
        The path to the file to be checked.

    Returns
    -------
    :class:`bool`
        True if the file exists, False otherwise.
    """
    try:
        with open(file_path, "r"):
            return True
    except FileNotFoundError:
        return False


def parse_file(file_path: str) -> Dict[str, str | int]:
    """
    Parse a file with the format:
    key: value
    key: value
    ...

    Parameters
    ----------
    file_path: :class:`str`
        The path to the file to be parsed.

    Returns
    -------
    :class:`Dict[str, str | int]`
        The parsed data from the file.
    """
    data = {}
    with open(file_path, "r") as f:
        for line in f:
            key, value = line.strip().split(":")
            data[key.strip()] = (
                int(value.strip()) if value.strip().isdigit() else value.strip()
            )
    return data


def get_data(url: str) -> pd.DataFrame:
    """
    Fetch data from a google spreadsheet

    Parameters
    ----------
    url: :class:`str`
        The url to the google spreadsheet.

    Returns
    -------
    :class:`pd.DataFrame`
        The data from the google spreadsheet.
    """
    # Get the id of the google spreadsheet
    id = url.split("/")[-2]

    # Get the data from the google spreadsheet
    response = requests.get(
        f"https://docs.google.com/spreadsheets/d/{id}/gviz/tq?tqx=out:csv"
    )
    data = pd.read_csv(StringIO(response.content.decode("utf-8")))

    return data


def parse_sheet(df: pd.DataFrame) -> Dict[str, Dict[str, Dict[int, List[int]]]]:
    """
    From the spreadsheet data, parse into dictionary in this format:
    {
        "<role>": {
            "<name>": {
                1: [<row_number>, <row_number>, ...],
                2: [<row_number>, <row_number>, ...]
                // ...
            },
            // ...
        }
    }

    Parameters
    ----------
    df: :class:`pd.DataFrame`
        The data from the google spreadsheet.

    Returns
    -------
    :class:`Dict[str, Dict[str, Dict[int, List[int]]]`
        The parsed data for the roles.
    """
    data: Dict[str, Dict[str, Dict[int, List[int]]]] = {}

    # Iterate over each column in the DataFrame
    for column in df.columns:
        if "[" not in column:
            continue

        role, field_number = column.split(" [")
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
                if all(
                    df[field].iloc[index] not in (nan, "") for field in previous_fields
                ):
                    if field_number not in data[role][name]:
                        data[role][name][field_number] = [index]
                    else:
                        data[role][name][field_number].append(index)

    return data


def log_parsed(parsed: Dict[str, Dict[str, Dict[int, List[int]]]]) -> None:
    """
    Log the parsed data in a readable format to a file for later reference.

    Parameters
    ----------
    parsed: :class:`Dict[str, Dict[str, Dict[int, List[int]]]`
        The parsed data for the roles.

    Returns
    -------
    None
    """
    logging.info("Parsed data from spreadsheet:")
    for role, data in parsed.items():
        logging.info(f"Role: {role}")
        for name, fields in data.items():
            logging.info(f"\t{name}")
            for field, score in fields.items():
                logging.info(f"\t\t{field}: ")
                logging.info(f"\t\t\ttotal: {len(score)}")
                logging.info(
                    "\t\t\t" + ", ".join(["Row " + str(i) + "'s choice" for i in score])
                )


def get_first_choice_helper(
    voter: int, round: int, votes: Dict[str, Dict[int, List[int]]], excluded: List[str]
) -> str | None:
    """
    Get the names that a person has previously voted for.

    Parameters
    ----------
    voter: :class:`int`
        The voter for which the first choices are to be determined.
    round: :class:`int`
        The round for which the first choices are to be determined.
    votes: :class:`Dict[str, Dict[int, List[int]]]`
        The parsed data for the role.
    excluded: :class:`List[str]`
        The names to be excluded from the first choice determination.
    """
    # Get the first choice for the voter
    non_excluded = {name: val for name, val in votes.items() if name not in excluded}

    # Get the first choice for the voter
    choices = []
    for r in range(1, round + 1):
        for name, fields in non_excluded.items():
            if r in fields and voter in fields[r]:
                choices.append((name, r))

    if len(choices) == 0:
        return None
    # Find the first choice for the voter (lowest round number)
    first_choice = min(choices, key=lambda x: x[1])[0]
    return first_choice


def winner_for_role(
    role: str,
    data: Dict[str, Dict[int, List[int]]],
    rows: int,
    excluded: Dict[str, List[str]] = {},
) -> str | Tie[str]:
    """
    Determine the winner for a role based on the parsed data.

    Parameters
    ----------
    role: :class:`str`
        The role for which the winner is to be determined.
    data: :class:`Dict[str, Dict[int, List[int]]]`
        The parsed data for the role.
    rows: :class:`int`
        The number of rows in the spreadsheet.
    excluded: :class:`Dict[str, List[str]]`
        The names to be excluded from the winner determination.

    Returns
    -------
    :class:`str`
        The winner for the role. Could be multiple winners if needed, or a tie.
    """
    # Check if there is only one non excluded candidate left
    match len(data) - len(excluded.get(role, [])):
        case 0:  # This will happen if no one voted for RON
            winner = "RON"
            logging.info(f"Winner for {role} determined by default: {winner}")
            return winner
        case 1:
            winner = [name for name in data if name not in excluded.get(role, [])][0]
            logging.info(f"Winner for {role} determined by default: {winner}")
            return winner

    # Loop over each voting rnd (eg 1-MAX key in data.values)
    for rnd in range(
        1, max(max(fields.keys(), default=0) for fields in data.values()) + 1
    ):
        # Get bonux votes for each person as a start for the round.
        total_votes = {}

        # Get total votes for each person
        for row in range(0, rows):
            # Get first choice for the row that is not excluded
            first_choice = get_first_choice_helper(
                row, rnd, data, excluded.get(role, [])
            )

            if first_choice is None:
                continue

            # Add the vote to the total votes
            if first_choice not in total_votes:
                total_votes[first_choice] = 1
            else:
                total_votes[first_choice] += 1

        # Get the person with the most votes
        person, score = max(total_votes.items(), key=lambda x: x[1])
        all_votes = sum(total_votes.values())
        threshold = all_votes / 2

        # Edge case, two people are left and have the same amount of votes
        if (
            len(
                two_winners := [
                    name for name in total_votes if total_votes[name] == threshold
                ]
            )
            > 1
        ):
            # Return both winners
            logging.info(f"TIE: Two winners found in round {rnd}: {two_winners}")
            return Tie(two_winners)

        logging.info(
            f"Round {rnd} for {role}: {person} with {score} votes ({score/all_votes*100:.2f}%)"
        )
        if score >= threshold:
            logging.info(
                f"Winner for {role} found in round {rnd}: {person} with {score} votes ({score/all_votes*100:.2f}%)"
            )
            return person

        # Eliminated least voted
        min_person, min_score = min(total_votes.items(), key=lambda x: x[1])
        logging.info(
            f"Eliminated {min_person} with {min_score} votes ({min_score/all_votes*100:.2f}%)"
        )
        excluded[role].append(min_person)


def determine_winner(
    parsed: Dict[str, Dict[str, Dict[int, List[int]]]],
    extra_roles: Dict[str, int],
    rows: int,
    excluded: Dict[str, str | List[str]] = {},
) -> Dict[str, str | List[str | Tie[str]] | Tie[str]]:
    """
    Returns the winner of each role based on the parsed data.
    Excludes the names for the role specified in the excluded dictionary.

    Parameters
    ----------
    parsed: :class:`Dict[str, Dict[str, Dict[int, List[int]]]`
        The parsed data for the roles.
    extra_roles: :class:`Dict[str, int]`
        The number of winners needed for each role.
    rows: :class:`int`
        The number of rows in the spreadsheet.
    excluded: :class:`Dict[str, str | List[str]]`
        The names to be excluded from the winner determination.

    Returns
    -------
    :class:`Dict[str, str | List[str | Tie[str]] | Tie[str]`
        The winners for each role.
    """
    logging.info("Determining winners:")
    winners = {}

    for role, data in parsed.items():
        # Open extra_roles.txt to find how many winners are needed
        if role in extra_roles:
            winners_needed = extra_roles[role]
        else:
            winners_needed = 1

        loop_winners = []
        for i in range(winners_needed):
            logging.info(f"Finding winner {i+1} for {role}")
            if role in excluded:
                excluded[role] = excluded[role] + loop_winners
            else:
                excluded[role] = deepcopy(
                    loop_winners
                )  # Shouldn't modify the original list
            winner = winner_for_role(role, data, rows, excluded)
            loop_winners.append(winner)

        winners[role] = loop_winners

    return winners


def wins_twice_helper(winners: Dict[str, str | List[str]]) -> Dict[str, List[str]]:
    """
    Helper function to determine if a name won more than once. Returns a dictionary in format:
    {
        "<name>": ["<role>", "<role>"], // Roles <name> won
        // ...
    }

    Parameters
    ----------
    winners: :class:`Dict[str, str | List[str]]`
        The winners for each role.

    Returns
    -------
    :class:`Dict[str, List[str]]`
        The names that won more than once.
    """
    # I apologize for the unreadable code
    all_winners = [item for sublist in winners.values() for item in sublist]

    return {
        name: [r for r, w in winners.items() if name in w]
        for _, names in winners.items()
        for name in names
        if all_winners.count(name) > 1 and name != "RON"
    }


def find_winners(
    parsed: Dict[str, Dict[str, Dict[int, List[int]]]],
    first_choices: Dict[str, str],
    extra_roles: Dict[str, int],
    rows: int,
) -> Dict[str, str | List[str]]:
    """
    Find the winners for each role based on the parsed data.

    Parameters
    ----------
    parsed: :class:`Dict[str, Dict[str, Dict[int, List[int]]]`
        The parsed data for the roles.
    first_choices: :class:`Dict[str, str]`
        The first choices for each role.
    extra_roles: :class:`Dict[str, int]`
        The number of winners needed for each role.
    rows: :class:`int`
        The number of rows in the spreadsheet.

    Returns
    -------
    :class:`Dict[str, str | List[str]`
        The winners for each role.
    """
    # Determine initial winners
    winners = determine_winner(parsed, extra_roles, rows)

    # Check if any name won twice
    while invalid := wins_twice_helper(winners):
        logging.error(
            f"Following winners have one more than one role: "
            + " | ".join(
                [(f"{name}: " + ", ".join(roles)) for name, roles in invalid.items()]
            )
        )
        # Open first_choices.txt, extract the first choices and add second one to excluded
        excluded: Dict[str, List[str]] = {}

        # Exclude from role that is NOT first_choice
        # if name is in invalid
        for name, roles in invalid.items():
            if name not in first_choices:
                logging.error(f"Role {name} not found in first_choices.txt.")
                raise ValueError(f"Role {name} not found in first_choices.txt.")

            first_choice = first_choices[name]
            for role in roles:
                if role == first_choice:  # Not exclude from first choice
                    continue
                # Exlude from other roles
                if role not in excluded:
                    excluded[role] = [name.strip()]
                else:
                    excluded[role].append(name.strip())
                logging.info(
                    f"Excluding {name} from {role} because {first_choice} is the first choice but {name} won both."
                )

        winners = determine_winner(parsed, extra_roles, rows, excluded)

    return winners


def print_winners(winners: Dict[str, str | List[str]]) -> None:
    """
    Print the winners in a readable format.

    Parameters
    ----------
    winners: :class:`Dict[str, str | List[str]]`
        The winners for each role.
    """
    print("Winners:")
    for role, name in winners.items():
        if isinstance(name, list):
            print(f"{role}:")
            if isinstance(name, Tie):  # Do not format Tie, print as __str__
                print(f"\t{name}")
            for n in name:
                print(f"\t{n}")
        else:
            print(f"{role}: {name}")


def main():
    # Error if there is no first_choices.txt
    if not file_exists("first_choices.txt"):
        logging.error(
            "first_choices.txt not found. Please create the file and add the first choices."
        )
        print(
            "first_choices.txt not found. Please create the file and add the first choices in the format:"
        )
        print("name: role")
        print("name: role")
        print("...")
        return

    # Clear log file
    open("process.log", "w").close()

    # Ask for link to a google spreadsheet
    url = input("Enter the link to the google spreadsheet: ")

    # Get the data from the google spreadsheet
    data = get_data(url)
    # Parse sheet
    parsed = parse_sheet(data)
    # Log parsed data
    log_parsed(parsed)
    # Find winners
    winners = find_winners(
        parsed,
        parse_file("first_choices.txt"),
        parse_file("extra_roles.txt") if file_exists("extra_roles.txt") else {},
        len(data),
    )

    logging.info("Winners declared successfully.")
    logging.info("Total form responses: " + str(len(data)))
    print_winners(winners)


if __name__ == "__main__":
    main()
