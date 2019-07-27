import json

import requests
from requests.auth import HTTPBasicAuth


class PlanningCenterWrapper(object):
    def __init__(self, config):
        self.config = config
        self.URL_ENDPOINT = "https://api.planningcenteronline.com/services/v2/"

    def auth(self):
        key = self.config.get("PLANNING_CENTER_ID")
        secret = self.config.get("PLANNING_CENTER_SECRET")

        if not key or not secret:
            raise Exception("Could not find planning center credentials.")
        return HTTPBasicAuth(key, secret)

    def _make_request(self, url, params=None):
        return requests.get(
            self.URL_ENDPOINT + url, params=params, auth=self.auth()
        ).json()

    def get_songs(self, offset=0):
        params = {"per_page": 100, "offset": offset, "order": "-last_scheduled_at"}
        return self._make_request("songs", params)

    def get_service_songs(self, plan_id):
        service_type = "287665"
        url = "service_types/{service_type}/plans/{plan_id}/items".format(
            service_type=service_type, plan_id=str(plan_id)
        )
        data = self._make_request(url)
        songs = [
            item["attributes"]["title"]
            for item in data["data"]
            if item["attributes"]["item_type"] == "song"
        ]
        return songs

    def output_song_data(self):
        song_response = self.get_songs()
        song_data = song_response["data"]
        while song_response["meta"].get("next"):
            song_response = self.get_songs(
                offset=song_response["meta"]["next"]["offset"]
            )
            song_data.extend(song_response["data"])

        output_data = {"songs": []}
        for song in song_data:
            if song["attributes"]:
                output_data["songs"].append(
                    {
                        "title": song["attributes"]["title"],
                        "author": song["attributes"]["author"],
                    }
                )
        with open("songs.json", "w") as outfile:
            json.dump(output_data, outfile)
