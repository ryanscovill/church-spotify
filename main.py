import requests
import spotipy
from requests.auth import HTTPBasicAuth
import json
import os

from spotipy import util
from fuzzywuzzy import fuzz
from termcolor import colored

PLAYLIST_ID = "63ee8lZhphofTuxcLRqPYT"
USERNAME = "227mrq3dhtua255wff2tegtrq"
BATCH_ADD_SIZE = 5


def auth():
    key = os.getenv("PLANNING_CENTER_KEY")
    secret = os.getenv("PLANNING_CENTER_SECRET")
    if not key or not secret:
        raise Exception("Could not find planning center credentials.")
    return HTTPBasicAuth(key, secret)


def get_songs(offset=0):
    return requests.get(
        "https://api.planningcenteronline.com/services/v2/songs",
        params={"per_page": 100, "offset": offset, "order": "-last_scheduled_at"},
        auth=auth(),
    ).json()


def output_song_data():
    song_response = get_songs()
    song_data = song_response["data"]
    while song_response["meta"].get("next"):
        song_response = get_songs(offset=song_response["meta"]["next"]["offset"])
        song_data.extend(song_response["data"])

    output_data = {"songs": []}
    for song in song_data:
        if song["attributes"]:
            output_data["songs"].append(
                {"title": song["attributes"]["title"], "author": song["attributes"]["author"]}
            )
    with open("songs.json", "w") as outfile:
        json.dump(output_data, outfile)


def _possible_song(track):
    return not track["explicit"]


def _artist_list(artists_result):
    return " ".join(artist["name"] for artist in artists_result)


def _string_confidence(
    position, explicit, title_result, title_actual, artists_result, artist_actual
):
    title_result = title_result[:-7] if title_result.endswith(" - Live") else title_result
    matched_title = fuzz.ratio(title_result, title_actual)
    matched_author = fuzz.token_set_ratio(artists_result, artist_actual)
    explicit_score = 100 if explicit else 0
    return (matched_title * 0.8) + (matched_author * 0.2) - (position ** 1.7) - explicit_score


def _get_song_id(sp, title, author):
    song_full = title + " " + author
    tracks = sp.search(song_full)["tracks"]["items"]
    if not tracks:
        tracks = sp.search(title)["tracks"]["items"]
    possible_matches = [
        (
            track,
            _string_confidence(
                position,
                track["explicit"],
                track["name"],
                title,
                _artist_list(track["artists"]),
                author,
            ),
        )
        for position, track in enumerate(tracks)
    ]
    possible_matches.sort(key=lambda x: x[1], reverse=True)
    if possible_matches:
        track = possible_matches[0][0]
        song_id = track["uri"]
        output = "{: >5} {: >60} {: >60} {: >80} {: >80}".format(
            round(possible_matches[0][1], 1),
            track["name"],
            title,
            _artist_list(track["artists"]),
            author,
        )
        if possible_matches[0][1] > 80:
            print(colored(output, "green"))
        elif possible_matches[0][1] > 50:
            print(colored(output, "blue"))
        else:
            song_id = None
            print()
            print(colored(output, "red"))
            print()
    else:
        song_id = None
        print()
        print(colored("!!!!!! WARNING: Could not find {} !!!!!!!!".format(title), "red"))
        print()

    return song_id


def add_to_spotify_playlist():
    token = util.prompt_for_user_token(USERNAME, scope="playlist-modify-private")
    sp = spotipy.Spotify(auth=token)
    with open("songs.json", "r") as infile:
        song_data = json.load(infile)

    sp.user_playlist_replace_tracks(USERNAME, PLAYLIST_ID, [])
    song_ids = []
    failed_count = 0
    success_count = 0
    for song in song_data["songs"]:
        song_author = song["author"] if song["author"] else ""
        song_id = _get_song_id(sp, song["title"], song_author)
        if song_id and song_id not in song_ids:
            song_ids.append(song_id)
            success_count += 1
        if song_id is None:
            failed_count += 1

        if len(song_ids) == BATCH_ADD_SIZE:
            sp.user_playlist_add_tracks(USERNAME, PLAYLIST_ID, song_ids)
            song_ids = []
    if song_ids:
        sp.user_playlist_add_tracks(USERNAME, PLAYLIST_ID, song_ids)
    print('# of successful songs: {}'.format(success_count))
    print("# of failed songs: {}".format(failed_count))
    print('Success Rate: {}%'.format(round(success_count / (failed_count + success_count) * 100)))
    print("done")


if __name__ == "__main__":
    output_song_data()
    print("Saved song data to songs.json")
    add_to_spotify_playlist()
    print("Finished")
