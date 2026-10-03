class ConversationError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


class IntegrationUnavailable(ConversationError):
    def __init__(self):
        super().__init__(503, "Conversation integrations are not configured or are unavailable.")
