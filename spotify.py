import json

import spotipy
from fuzzywuzzy import fuzz
from spotipy import util
from termcolor import colored


class SpotifyWrapper(object):
    PLAYLIST_ID = "63ee8lZhphofTuxcLRqPYT"
    USERNAME = "227mrq3dhtua255wff2tegtrq"
    BATCH_ADD_SIZE = 5

    def __init__(self, config):
        self.config = config
        self.sp = self.get_api()

    def get_api(self):
        token = util.prompt_for_user_token(
            self.USERNAME,
            client_id=self.config.get("SPOTIPY_CLIENT_ID"),
            client_secret=self.config.get("SPOTIPY_CLIENT_SECRET"),
            scope="playlist-modify-private",
        )
        return spotipy.Spotify(auth=token)

    @staticmethod
    def _possible_song(track):
        return not track["explicit"]

    @staticmethod
    def _artist_list(artists_result):
        return " ".join(artist["name"] for artist in artists_result)

    @staticmethod
    def _string_confidence(
        position, explicit, title_result, title_actual, artists_result, artist_actual
    ):
        title_result = (
            title_result[:-7] if title_result.endswith(" - Live") else title_result
        )
        matched_title = fuzz.ratio(title_result, title_actual)
        matched_author = fuzz.token_set_ratio(artists_result, artist_actual)
        explicit_score = 100 if explicit else 0
        return (
            (matched_title * 0.8)
            + (matched_author * 0.2)
            - (position ** 1.7)
            - explicit_score
        )

    def get_playlist_songs(self, playlist_id):
        playlist = self.sp.user_playlist(self.USERNAME, playlist_id)
        return playlist

    def get_playlist_song_names(self, playlist_id):
        items = self.get_playlist_songs(playlist_id)["tracks"]["items"]
        return [(item["track"]["name"], item["track"]["id"]) for item in items]

    def _get_song_id(self, sp, title, author):
        song_full = title + " " + author
        tracks = sp.search(song_full)["tracks"]["items"]
        if not tracks:
            tracks = sp.search(title)["tracks"]["items"]
        possible_matches = [
            (
                track,
                self._string_confidence(
                    position,
                    track["explicit"],
                    track["name"],
                    title,
                    self._artist_list(track["artists"]),
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
                self._artist_list(track["artists"]),
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
            print(
                colored(
                    "!!!!!! WARNING: Could not find {} !!!!!!!!".format(title), "red"
                )
            )
            print()

        return song_id

    def load_json_to_playlist(self, playlist_id):
        with open("songs.json", "r") as infile:
            song_data = json.load(infile)

        song_ids = []
        failed_count = 0
        success_count = 0
        for song in song_data["songs"]:
            song_author = song["author"] if song["author"] else ""
            song_id = self._get_song_id(self.sp, song["title"], song_author)
            if song_id and song_id not in song_ids:
                song_ids.append(song_id)
                success_count += 1
            if song_id is None:
                failed_count += 1

        self.add_to_spotify_playlist(playlist_id, song_ids)

        print("# of successful songs: {}".format(success_count))
        print("# of failed songs: {}".format(failed_count))
        print(
            "Success Rate: {}%".format(
                round(success_count / (failed_count + success_count) * 100)
            )
        )
        print("done")

    def add_to_spotify_playlist(self, playlist_id, song_ids):
        self.sp.user_playlist_replace_tracks(self.USERNAME, playlist_id, [])
        if len(song_ids) == self.BATCH_ADD_SIZE:
            self.sp.user_playlist_add_tracks(self.USERNAME, playlist_id, song_ids)
            song_ids = []
        if song_ids:
            self.sp.user_playlist_add_tracks(self.USERNAME, playlist_id, song_ids)
