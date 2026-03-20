"""Language-specific runner configuration.

LANGUAGE_CONFIG maps a language string to its:
- source_file : filename written into the sandbox directory
- compile_cmd : shell command run inside the compile container (None = interpreted)
- compile_artifact : expected output file produced by compiler (None = interpreted)
- run_cmd     : shell command run inside the execution container
"""
from __future__ import annotations

from dataclasses import dataclass

from shared.enums import Language


@dataclass(frozen=True)
class RunnerConfig:
    source_file: str
    run_cmd: str
    compile_cmd: str | None = None
    compile_artifact: str | None = None  # presence checked to detect CE


LANGUAGE_CONFIG: dict[str, RunnerConfig] = {
    Language.CPP: RunnerConfig(
        source_file="solution.cpp",
        compile_cmd="clang++ -O2 -o /sandbox/a.out /sandbox/solution.cpp",
        compile_artifact="a.out",
        run_cmd="/sandbox/a.out",
    ),
    Language.JAVA: RunnerConfig(
        source_file="Main.java",
        compile_cmd="javac -d /sandbox /sandbox/Main.java",
        compile_artifact="Main.class",
        run_cmd="java -cp /sandbox Main",
    ),
    Language.PYTHON: RunnerConfig(
        source_file="solution.py",
        run_cmd="python3 /sandbox/solution.py",
    ),
    Language.NODEJS: RunnerConfig(
        source_file="solution.js",
        run_cmd="node /sandbox/solution.js",
    ),
}
