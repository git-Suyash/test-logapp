class LogProcessor:

    def process(self, event):

        print({
            "timestamp": str(event.timestamp),
            "log_level": event.log_level,
            "message": event.message
        })