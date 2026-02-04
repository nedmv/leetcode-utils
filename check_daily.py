#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# /// script
# dependencies = [
# "gql",
# "aiohttp",
# ]
# requires-python = ">=3.11"
# ///
#
# Checks whether a specified user has solved today's daily task.
# Run the script with `uv run check_daily.py <username>`.

import sys
from datetime import datetime, timezone
from enum import StrEnum

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport


class Difficulty(StrEnum):
    Easy = "Easy"
    Medium = "Medium"
    Hard = "Hard"


def query_graphql(username: str):
    LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
    SUBMISSION_LIMIT = 15
    transport = AIOHTTPTransport(url=LEETCODE_GRAPHQL_URL)
    client = Client(transport=transport)
    query = gql(
        """
        query recentAcSubmissions($username: String!, $limit:Int!) {
            recentAcSubmissionList(username: $username, limit: $limit) {
                titleSlug
                timestamp
            }
            activeDailyCodingChallengeQuestion {
                date
                question {
                    title
                    titleSlug
                    difficulty
                    acRate
                    topicTags {
                        name
                    }
                }
            }
        }
        """
    )
    query_params = {"username": username, "limit": SUBMISSION_LIMIT}
    return client.execute(query, variable_values=query_params)


def is_daily_question_for_today(data, today: datetime):
    question_date = datetime.fromisoformat(
        data["activeDailyCodingChallengeQuestion"]["date"]
    )
    return question_date.date() == today.date()


def is_daily_question_solved(data, today, title_slug):
    recently_solved = data["recentAcSubmissionList"]
    solved = False
    for submission in recently_solved:
        timestamp = int(submission["timestamp"])
        if datetime.fromtimestamp(timestamp, tz=timezone.utc).date() != today.date():
            break
        if submission["titleSlug"] != title_slug:
            continue
        solved = True

    # FIXME: if not solved, but last checked submission time is still today, request more data.
    return solved


def parse_daily_question(data):
    daily_question = data["activeDailyCodingChallengeQuestion"]["question"]
    title = daily_question["title"]
    title_slug = daily_question["titleSlug"]
    difficulty = Difficulty(daily_question["difficulty"])
    acRate = float(daily_question["acRate"])
    topics = [topic["name"] for topic in daily_question["topicTags"]]
    return title, title_slug, difficulty, acRate, topics


def main():
    username = sys.argv[1] if len(sys.argv) >= 2 else None
    if not username:
        sys.exit(f"Run the script with `uv run {sys.argv[0]} <username>`.")

    try:
        data = query_graphql(username)
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit("Failed to get data from Leetcode, please retry later.")

    today = datetime.now(tz=timezone.utc)
    if not is_daily_question_for_today(data, today):
        sys.exit("Got expired daily question, please retry later.")

    try:
        title, title_slug, difficulty, acRate, topics = parse_daily_question(data)
    except Exception as e:
        sys.exit(f"Failed to parse daily question: {e}")
    description = f'{difficulty} task "{title}" with acRate {acRate:.2f}%'

    if is_daily_question_solved(data, today, title_slug):
        print(f"{description} is solved!")
        print(f"Nice work, {username}!")
        sys.exit(0)

    print(f"{description} is not yet solved.")
    if difficulty == Difficulty.Easy or acRate > 60:
        print("Should be a piece of cake!")
    elif difficulty == Difficulty.Hard or acRate < 40:
        print(f"Brace yourself, {username}!")
    else:
        print("Time to think about it!")

    print()
    print(f"Link: https://leetcode.com/problems/{title_slug}")
    print(f"Topics: {', '.join(topics)}")
    sys.exit(1)


if __name__ == "__main__":
    main()
