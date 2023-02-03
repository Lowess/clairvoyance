class TestSnsNotifier:
    def test_sns(self, sns_notifier):
        sns_notifier.send("Subject", "Message")
