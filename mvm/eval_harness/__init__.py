"""Craft evaluation harness — three scenes, auto signals + human form, no single score."""

from mvm.eval_harness.auto import evaluate_scene_automatic
from mvm.eval_harness.scenes import HARNESS_SCENES, get_scene, list_scenes
from mvm.eval_harness.workflow import (
    blank_human_form,
    load_session,
    list_sessions,
    run_all_scenes_auto,
    save_human_form,
    seed_harness_scenes,
    start_eval_session,
    submit_human_form,
)
from mvm.schemas.eval_harness import (
    ALL_EVAL_DIMENSIONS,
    AUTO_EVAL_DIMENSIONS,
    EvalDimension,
    EvalSession,
    HumanReviewForm,
    SceneKind,
)

__all__ = [
    "ALL_EVAL_DIMENSIONS",
    "AUTO_EVAL_DIMENSIONS",
    "EvalDimension",
    "EvalSession",
    "HARNESS_SCENES",
    "HumanReviewForm",
    "SceneKind",
    "blank_human_form",
    "evaluate_scene_automatic",
    "get_scene",
    "list_scenes",
    "list_sessions",
    "load_session",
    "run_all_scenes_auto",
    "save_human_form",
    "seed_harness_scenes",
    "start_eval_session",
    "submit_human_form",
]
