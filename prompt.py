#!/usr/bin/env python3

from __future__ import annotations
from yandex_cloud_ml_sdk import YCloudML

base_message = None
ML_API_KEY = None
FOLDER_ID = None
SDK = None

#
#
# Get tokens and secrets from env and preload prompt
def preload_contants():
    global ML_API_KEY, FOLDER_ID, SDK, base_message
    ML_API_KEY = os.environ.get('ML_API_KEY') or "a_very_secret_key"
    FOLDER_ID = os.environ.get('FOLDER_ID') or "a_very_secret_key"
    sdk = YCloudML(
        folder_id=FOLDER_ID,
        auth=ML_API_KEY,
    )
    with open("base_prompt.md") as f:
        base_message = [{"role":"system", "text":f.read()}]


def get_result(user_message):
    global base_message
    current_message = base_message + [{"role":"user", "text":user_message}]
    result = (
        sdk.models.completions("yandexgpt").configure(temperature=0.5).run(current_message)
    )

    for alternative in result:
        print(alternative)



if __name__ == "__main__":
    get_result()
