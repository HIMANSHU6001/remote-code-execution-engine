from enum import StrEnum


class Language(StrEnum):
    PYTHON = "python"
    CPP = "cpp"
    JAVA = "java"
    NODEJS = "nodejs"


class SubmissionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


class Verdict(StrEnum):
    ACC = "ACC"  # Accepted
    WA = "WA"   # Wrong Answer
    TLE = "TLE"  # Time Limit Exceeded
    MLE = "MLE"  # Memory Limit Exceeded
    RE = "RE"   # Runtime Error
    CE = "CE"   # Compilation Error
    IE = "IE"   # Internal Error
