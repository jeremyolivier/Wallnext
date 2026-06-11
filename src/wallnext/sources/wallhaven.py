import random

from wallnext.wallhaven.wallhaven_requester import WallhavenRequester


class WallhavenSource:
    def __init__(self) -> None:
        self._requester = WallhavenRequester()

    def random_url(self) -> str:
        result = self._requester.toplist()
        return random.choice(result.data).path
