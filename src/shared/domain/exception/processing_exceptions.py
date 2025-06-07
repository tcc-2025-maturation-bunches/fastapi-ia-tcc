class ProcessingException(Exception):
    def __init__(self, error_code: str, error_message: str, stage: str, original_error: str):
        self.error_code = error_code
        self.error_message = error_message
        self.stage = stage
        self.original_error = original_error


class PartialProcessingError(ProcessingException):
    def __init__(self, detection_result, **kwargs):
        super().__init__(**kwargs)
        self.detection_result = detection_result
