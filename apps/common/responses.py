class CustomResponse:
    def success(message, data=None, status_code=200):
        response = {
            "status": "success",
            "message": message,
            "data": data,
        }
        response.pop("data", None) if data is None else ...
        return response

    def error(message, err_code, data=None, status_code=400):
        response = {
            "status": "failure",
            "message": message,
            "code": err_code,
            "data": data,
        }
        response.pop("data", None) if data is None else ...
        return response
