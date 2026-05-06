from enum import Enum


class Language(str, Enum):
    PYTHON = "python"
    CPP = "cpp"
    JAVA = "java"
    NODEJS = "nodejs"


class SupportedLanguage(str, Enum):
    PYTHON = "python"
    CPP = "cpp"
    JAVA = "java"
    NODEJS = "nodejs"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


class Verdict(str, Enum):
    ACC = "ACC"  # Accepted
    WA = "WA"  # Wrong Answer
    TLE = "TLE"  # Time Limit Exceeded
    MLE = "MLE"  # Memory Limit Exceeded
    RE = "RE"  # Runtime Error
    CE = "CE"  # Compilation Error
    IE = "IE"  # Internal Error


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
