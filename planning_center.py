import json

import requests
from requests.auth import HTTPBasicAuth


class PlanningCenterWrapper(object):
    def __init__(self, config):
        self.config = config
        self.URL_ENDPOINT = "https://api.planningcenteronline.com/services/v2/"
        self.SERVICE_TYPE = "287665"
        self.USER_ID = "3878409"

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

    def get_person_plans(self):
        person_plans = self._make_request("people/{user_id}/plan_people".format(user_id=self.USER_ID))
        plan_ids = [item['relationships']['plan']['data']['id'] for item in person_plans['data']]
        return plan_ids

    def get_plan(self, plan_id):
        url = "service_types/{service_type}/plans/{plan_id}".format(
            service_type=self.SERVICE_TYPE, plan_id=str(plan_id)
        )
        data = self._make_request(url)
        return data['data']

    def get_service_songs(self, plan_id):
        url = "service_types/{service_type}/plans/{plan_id}/items".format(
            service_type=self.SERVICE_TYPE, plan_id=str(plan_id)
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
