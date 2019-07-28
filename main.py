import json
from itertools import takewhile

from fuzzywuzzy import fuzz, process
from termcolor import colored

from planning_center import PlanningCenterWrapper
from spotify import SpotifyWrapper

CBC_SUNDAY_WORSHIP_PLAYLIST = "spotify:playlist:7LdEl3ifE5NHa4tXm9Cn61"


class SpotifyPlanningCenter(object):
    def __init__(self):
        config = self.get_config()
        self.planning_center = PlanningCenterWrapper(config)
        self.spotify = SpotifyWrapper(config)

    @staticmethod
    def get_config():
        with open("config.json", "r") as cfg_file:
            cfg = json.load(cfg_file)
        return cfg

    def update_my_playlist(self):
        self.planning_center.output_song_data()
        print("Saved song data to songs.json")
        self.spotify.load_json_to_playlist(self.spotify.PLAYLIST_ID)

    def match_songs(self, service_songs, cbc_songs):
        def process_title(name):
            sep = "-"
            return name.split(sep, 1)[0]

        results = []
        cbc_song_lookup = {process_title(song[0]): song[1] for song in cbc_songs}

        for service_song in service_songs:
            song_matches = process.extract(
                service_song, cbc_song_lookup.keys(), scorer=fuzz.partial_ratio
            )
            matches = list(takewhile(lambda x: x[1] > 90, song_matches))
            if not matches:
                print(colored("Missing: {}".format(service_song), "red"))
            else:
                for match in matches:
                    print(colored("Added: {}".format(match[0]), "green"))
                    results.append(cbc_song_lookup[match[0]])

        return results

    def create_current_setlist(self, plan_id, title):
        playlist_id = util.spotify.create_playlist(title)
        service_songs = self.planning_center.get_service_songs(plan_id)
        cbc_songs = self.spotify.get_playlist_song_names(CBC_SUNDAY_WORSHIP_PLAYLIST)
        song_ids = self.match_songs(service_songs, cbc_songs)
        self.spotify.add_to_spotify_playlist(playlist_id, song_ids)


if __name__ == "__main__":
    util = SpotifyPlanningCenter()
    plan_ids = util.planning_center.get_person_plans()
    for plan_id in plan_ids[:2]:
        plan = util.planning_center.get_plan(plan_id)
        plan_date = plan['attributes']['dates']
        title_date = plan_date[:3] + " " + " ".join(plan_date.split(" ")[1:])
        playlist_title = "CBC " + title_date
        print("Creating Playlist for {} service...".format(playlist_title))
        util.create_current_setlist(plan['id'], playlist_title)
