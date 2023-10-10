from ninja.responses import Response
from http import HTTPStatus

from apps.common.error import ErrorCode


class RequestError(Exception):
    default_detail = "An error occured"

    def __init__(
        self, err_code: str, err_msg: str, status_code: int = 400, data: dict = None
    ) -> None:
        self.status_code = HTTPStatus(status_code)
        self.err_code = err_code
        self.err_msg = err_msg
        self.data = data

        super().__init__()


def validation_errors(exc):
    # Get the original 'detail' list of errors
    details = exc.errors
    modified_details = {}
    for error in details:
        try:
            field_name = error["loc"][1]
        except:
            field_name = error["loc"][0]

        modified_details[f"{field_name}"] = error["msg"]

    return Response(
        {
            "status": "failure",
            "code": ErrorCode.INVALID_ENTRY,
            "message": "Invalid Entry",
            "data": modified_details,
        },
        status=422,
    )


def request_errors(exc):
    err_dict = {
        "status": "failure",
        "code": exc.err_code,
        "message": exc.err_msg,
    }
    if exc.data:
        err_dict["data"] = exc.data
    return Response(err_dict, status=exc.status_code)
