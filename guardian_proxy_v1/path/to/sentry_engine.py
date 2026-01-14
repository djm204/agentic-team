import re
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import PatternRecognizer

class SentryEngine:
    def __init__(self, recognizers=None):
        if recognizers is None:
            recognizers = []
            recognizers.append(self.build_sin_recognizer())
            recognizers.append(self.build_uci_recognizer())
        self.registry = RecognizerRegistry(recognizers=recognizers)
        self.engine = AnalyzerEngine(registry=self.registry)

    def build_sin_recognizer(self):
        return PatternRecognizer(name="CANADA_SIN", patterns=[r"\b\d{3}-\d{3}-\d{3}\b"])

    def build_uci_recognizer(self):
        return PatternRecognizer(name="CANADA_UCI", patterns=[r"\b\d{8,10}\b"])
        
    def sanitize(self, text):
        return self.engine.analyze(text=text, language='en')