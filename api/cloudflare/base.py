class CloudflareAPIResponse:
    @classmethod
    def from_dict(cls, result: dict):
        raise NotImplementedError

    def to_dict(self) -> dict:
        return vars(self)


class WorkerInfo(CloudflareAPIResponse):
    def __init__(self, duration, errors, requests, response_body_size, subrequests):
        """
        :param duration:
        :param errors: Number of error requests
        :param requests: Total requests today (Free plan allows up to 100,000/day, resets at 8 AM Beijing time)
        :param response_body_size: Used traffic
        :param subrequests: Number of subrequests
        """
        self.duration = duration
        self.errors = errors
        self.requests = requests
        self.response_body_size = response_body_size
        self.subrequests = subrequests

    @classmethod
    def from_dict(cls, result: dict):
        if data := result.get("data"):
            if not data["viewer"]["accounts"][0]["workersInvocationsAdaptive"]:
                return cls(
                    duration=0,
                    errors=0,
                    requests=0,
                    response_body_size=0,
                    subrequests=0,
                )
            sum = data["viewer"]["accounts"][0]["workersInvocationsAdaptive"][0]["sum"]
            return cls(
                duration=sum["requests"],
                errors=sum["errors"],
                requests=sum["requests"],
                response_body_size=sum["responseBodySize"],
                subrequests=sum["subrequests"],
            )
        else:
            raise ValueError("Invalid data")
