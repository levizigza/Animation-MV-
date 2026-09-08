"""Sequence-aware analysis — identify issues, never auto-fix."""

from mvm.sequence_analysis.evaluator import (
    evaluate_sequence,
    evaluate_shot_in_sequence,
    evaluate_shot_window,
    load_shots_fixture,
    save_evaluation,
)
from mvm.schemas.sequence_eval import (
    CharacterStateSnapshot,
    SequenceEvaluation,
    SequenceIssue,
)

__all__ = [
    "CharacterStateSnapshot",
    "SequenceEvaluation",
    "SequenceIssue",
    "evaluate_sequence",
    "evaluate_shot_in_sequence",
    "evaluate_shot_window",
    "load_shots_fixture",
    "save_evaluation",
]
