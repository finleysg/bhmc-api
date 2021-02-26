from rest_framework.exceptions import APIException


class SlotConflictError(APIException):

    def __init__(self):
        self.status_code = 409
        self.detail = "One or more of the slots you requested have already been reserved"


class PlayerConflictError(APIException):

    def __init__(self):
        self.status_code = 409
        self.detail = "The player selected has already signed up or is in the process of signing up"


class MissingSlotsError(APIException):

    def __init__(self):
        self.status_code = 400
        self.detail = "This registration requires that you include at least one slot to reserve"


class EventFullError(APIException):

    def __init__(self):
        self.status_code = 400
        self.detail = "The event field is full"


class EventRegistrationNotOpenError(APIException):

    def __init__(self):
        self.status_code = 400
        self.detail = "The event is not currently open for registration"


class RegistrationConfirmedError(APIException):

    def __init__(self):
        self.status_code = 400
        self.detail = "This registration has already been confirmed and paid"


class CourseRequiredError(APIException):

    def __init__(self):
        self.status_code = 400
        self.detail = "A course must be included when registering for this event"


class InvalidHoleError(APIException):

    def __init__(self):
        self.status_code = 400
        self.detail = "The hole id provided is not part of this event"


class StripeCardError(APIException):

    original_error = {}

    def __init__(self, err):
        self.detail = err.json_body["error"]["message"]
        self.code = err.json_body["error"]["code"]
        self.status_code = err.http_status
        self.original_error = err.json_body


class StripePaymentError(APIException):

    original_error = {}

    def __init__(self, err):
        self.status_code = err.http_status
        self.detail = str(err)
        self.original_error = err.json_body
