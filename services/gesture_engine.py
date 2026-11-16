import time
from enum import Enum

import numpy as np
from PySide6.QtCore import QObject, Signal

from core.hand_tracker import HandTracker
from services.neural_pose import NeuralPose


class GestureState(Enum):
    SLEEP = "SLEEP"
    ARMED = "ARMED"
    MOUSE = "MOUSE"


class GestureEngine(QObject):
    processed_frame = Signal(object, object, object)
    state_changed = Signal(str)
    gesture_detected = Signal(str, str, str)
    error_occurred = Signal(str)

    HAND_SIDES = ("LEFT", "RIGHT")
    MISSING_HAND_GRACE = 0.5
    POSE_CHANGE_THRESHOLD = 0.08
    STABLE_CHANGE_FRAMES = 2

    def __init__(self, hand_tracker=None, neural_pose=None):
        super().__init__()
        self.tracker = hand_tracker or HandTracker()
        self.neural_pose = neural_pose or NeuralPose()
        self.enabled = False
        self.state = GestureState.SLEEP
        self.hold_progress = 0.0
        self.mouse_exit_gestures = ()
        self._mouse_entry_pose = None
        self._mouse_entry_slot = None
        self._mouse_entry_signature = None
        self._mouse_wait_for_release = False
        self._slots = {}
        self._last_frame_time = 0.0

    def set_enabled(self, enabled):
        enabled = bool(enabled)
        if self.enabled == enabled:
            return
        self.enabled = enabled
        if not enabled:
            self.mouse_exit_gestures = ()
            self._mouse_entry_pose = None
            self._mouse_entry_slot = None
            self._mouse_entry_signature = None
            self._mouse_wait_for_release = False
        self._reset_slots()
        self._set_state(GestureState.ARMED if enabled else GestureState.SLEEP)

    def reload_model(self):
        self.neural_pose.reload_model()
        self._reset_slots()

    def set_mouse_mode(self, enabled, exit_gestures=(), entry_pose=None, entry_hand=None):
        if enabled:
            gestures = tuple(dict.fromkeys(exit_gestures))
            if not gestures and entry_pose:
                gestures = (entry_pose,)
            self.mouse_exit_gestures = gestures
            self._mouse_entry_pose = entry_pose
            self._mouse_entry_slot = (
                str(entry_hand).upper() if entry_hand is not None else None
            )
            self._mouse_entry_signature = None
            if self._mouse_entry_slot is None and entry_pose:
                self._mouse_entry_slot = next(
                    (
                        side
                        for side, state in self._slots.items()
                        if side in (*self.HAND_SIDES, "BOTH")
                        and state.get("pose") == entry_pose
                    ),
                    None,
                )
            if self._mouse_entry_slot in self._slots:
                entry_state = self._slots[self._mouse_entry_slot]
                if entry_state.get("pose") == entry_pose:
                    self._mouse_entry_signature = entry_state.get("signature")
            self._mouse_wait_for_release = bool(entry_pose)
            self._reset_slots()
            self._set_state(GestureState.MOUSE)
        else:
            self.mouse_exit_gestures = ()
            self._mouse_entry_pose = None
            self._mouse_entry_slot = None
            self._mouse_entry_signature = None
            self._mouse_wait_for_release = False
            self._reset_slots()
            self._set_state(GestureState.ARMED if self.enabled else GestureState.SLEEP)

    def process_frame(self, frame):
        now = time.monotonic()
        self._last_frame_time = now
        result = self.tracker.process(frame)
        hands = {
            hand.side.value.upper(): np.asarray(hand.points, dtype=np.float32)
            for hand in result.hands
        }
        tracked_hands = dict(hands)

        if self.state is GestureState.SLEEP or not hands:
            self._expire_missing_slots(set(hands), now)
            if self.state is GestureState.MOUSE and not hands:
                if self._mouse_wait_for_release:
                    self._reset_slots()
                self._mouse_wait_for_release = False
                self._mouse_entry_signature = None
            self.processed_frame.emit(frame, tracked_hands, {})
            return
        if not self.neural_pose.enabled or self.neural_pose.model is None:
            self._reset_slots()
            self.processed_frame.emit(frame, tracked_hands, {})
            return
        self._update_mouse_release_wait(hands)

        predictions = {}
        allowed = (
            frozenset(self.mouse_exit_gestures)
            if self.state is GestureState.MOUSE
            else None
        )
        requested_sides = set()
        for side in self.HAND_SIDES:
            if side not in hands:
                self._expire_slot(side, now)
                continue
            prediction, needs_classification = self._prepare_hand(
                side, hands[side]
            )
            if prediction is not None:
                predictions[side] = prediction
            if needs_classification:
                requested_sides.add(side)

        classify_both = False
        should_classify_both = (
            self.state is GestureState.ARMED
            or (
                self.state is GestureState.MOUSE
                and any(
                    self.neural_pose.get_gesture_config(pose).get("hand") == "BOTH"
                    for pose in self.mouse_exit_gestures
                )
            )
        )
        if should_classify_both and set(self.HAND_SIDES).issubset(hands):
            bilateral, classify_both = self._prepare_both(hands, now)
            if bilateral is not None:
                predictions["BOTH"] = bilateral
        else:
            self._expire_slot("BOTH", now)

        if requested_sides or classify_both:
            detected_events = []
            try:
                classified = self.neural_pose.predict(
                    hands,
                    allowed_gestures=allowed,
                    sides=requested_sides,
                    include_both=classify_both,
                )
            except (AttributeError, IndexError, TypeError, ValueError) as error:
                slots = set(requested_sides)
                if classify_both:
                    slots.add("BOTH")
                for slot in slots:
                    state = self._slots[slot]
                    state["negative_cached"] = True
                    self.neural_pose.reset(slot)
                self.error_occurred.emit(f"Помилка нейромережі: {error}")
                classified = {}
            for side, prediction in classified.items():
                state = self._slots[side]
                state.update(
                    pose=prediction[0],
                    confidence=prediction[1],
                    negative_cached=False,
                    candidate=None,
                    candidate_frames=0,
                )
                detected_events.append((prediction[0], side))
                predictions[side] = prediction
            for side in requested_sides:
                if (
                    side not in classified
                    and self.neural_pose.vote_window_full(side)
                ):
                    self._slots[side]["negative_cached"] = True
            if (
                classify_both
                and "BOTH" not in classified
                and self.neural_pose.vote_window_full("BOTH")
            ):
                self._slots["BOTH"]["negative_cached"] = True
            for pose, side in detected_events:
                if not self._is_waiting_entry_result(pose, side):
                    self.gesture_detected.emit("НЕЙРОМЕРЕЖА", pose, side)

        if "BOTH" in predictions:
            predictions.pop("LEFT", None)
            predictions.pop("RIGHT", None)

        if self.state is GestureState.MOUSE and self._mouse_wait_for_release:
            if self._mouse_entry_slot == "BOTH":
                signature = np.concatenate(
                    (
                        self._pose_signature(hands["LEFT"]),
                        self._pose_signature(hands["RIGHT"]),
                    )
                ) if set(self.HAND_SIDES).issubset(hands) else None
                if signature is not None and self._signature_distance(
                    signature, self._mouse_entry_signature
                ) > self.POSE_CHANGE_THRESHOLD:
                    self._mouse_wait_for_release = False
                    self._mouse_entry_signature = None
                    predictions.clear()
                else:
                    predictions.pop("BOTH", None)
            else:
                self._wait_for_single_hand_release(hands, predictions)

        self.processed_frame.emit(frame, tracked_hands, predictions)

    def _wait_for_single_hand_release(self, hands, predictions):
        for side, points in hands.items():
            signature = self._pose_signature(points)
            is_entry_hand = self._mouse_entry_slot in (None, side)
            if (
                is_entry_hand
                and self._mouse_entry_signature is not None
                and self._signature_distance(
                    signature, self._mouse_entry_signature
                )
                <= self.POSE_CHANGE_THRESHOLD
            ):
                predictions.pop(side, None)
            elif is_entry_hand:
                self._mouse_wait_for_release = False
                self._mouse_entry_signature = None
                predictions.clear()
                break

    def _update_mouse_release_wait(self, hands):
        if self.state is not GestureState.MOUSE or not self._mouse_wait_for_release:
            return
        signature = None
        if self._mouse_entry_slot == "BOTH":
            if set(self.HAND_SIDES).issubset(hands):
                signature = np.concatenate(
                    (
                        self._pose_signature(hands["LEFT"]),
                        self._pose_signature(hands["RIGHT"]),
                    )
                )
        elif self._mouse_entry_slot in self.HAND_SIDES:
            points = hands.get(self._mouse_entry_slot)
            if points is not None:
                signature = self._pose_signature(points)
        else:
            for points in hands.values():
                signature = self._pose_signature(points)
                break

        if (
            signature is not None
            and self._mouse_entry_signature is not None
            and self._signature_distance(
                signature, self._mouse_entry_signature
            )
            > self.POSE_CHANGE_THRESHOLD
        ):
            self._mouse_wait_for_release = False
            self._mouse_entry_signature = None

    def _is_waiting_entry_result(self, pose, side):
        if self.state is not GestureState.MOUSE or not self._mouse_wait_for_release:
            return False
        if self._mouse_entry_slot == "BOTH":
            return side == "BOTH" and pose == self._mouse_entry_pose
        return (
            (
                side == self._mouse_entry_slot
                or self._mouse_entry_slot is None and side in self.HAND_SIDES
            )
            and pose == self._mouse_entry_pose
        )

    def _prepare_hand(self, side, points):
        signature = self._pose_signature(points)
        state = self._slots.setdefault(
            side,
            {
                "signature": None,
                "pose": None,
                "confidence": 0.0,
                "candidate": None,
                "candidate_frames": 0,
                "last_seen": self._last_frame_time,
                "negative_cached": False,
            },
        )
        state["last_seen"] = self._last_frame_time
        previous_signature = state["signature"]

        if previous_signature is not None:
            distance = self._signature_distance(signature, previous_signature)
            if distance <= self.POSE_CHANGE_THRESHOLD:
                state["candidate"] = None
                state["candidate_frames"] = 0
                if state["pose"] is not None:
                    return (state["pose"], state["confidence"]), False
                if state["negative_cached"]:
                    return None, False
            else:
                if self._confirm_pose_change(state, signature):
                    self.neural_pose.reset(side)
                    state.update(
                        signature=None,
                        pose=None,
                        confidence=0.0,
                        negative_cached=False,
                    )
                else:
                    if state["pose"] is not None:
                        return (state["pose"], state["confidence"]), False
                    return None, False

        if state["signature"] is None:
            state["signature"] = signature
        return None, True

    def _prepare_both(self, hands, now):
        signature = np.concatenate(
            (
                self._pose_signature(hands["LEFT"]),
                self._pose_signature(hands["RIGHT"]),
            )
        )
        state = self._slots.setdefault(
            "BOTH",
            {
                "signature": None,
                "pose": None,
                "confidence": 0.0,
                "candidate": None,
                "candidate_frames": 0,
                "last_seen": now,
                "negative_cached": False,
            },
        )
        state["last_seen"] = now
        if state["signature"] is not None:
            distance = self._signature_distance(signature, state["signature"])
            if distance <= self.POSE_CHANGE_THRESHOLD:
                if state["pose"] is not None:
                    return (state["pose"], state["confidence"]), False
                if state["negative_cached"]:
                    return None, False
            elif not self._confirm_pose_change(state, signature):
                if state["pose"] is not None:
                    return (state["pose"], state["confidence"]), False
                return None, False
            else:
                self.neural_pose.reset("BOTH")
                state.update(
                    signature=None,
                    pose=None,
                    confidence=0.0,
                    negative_cached=False,
                )

        if state["signature"] is None:
            state["signature"] = signature
        return None, True

    def _confirm_pose_change(self, state, signature):
        candidate = state["candidate"]
        if (
            candidate is None
            or self._signature_distance(signature, candidate)
            > self.POSE_CHANGE_THRESHOLD
        ):
            state["candidate"] = signature
            state["candidate_frames"] = 1
            return False
        state["candidate_frames"] += 1
        if state["candidate_frames"] < self.STABLE_CHANGE_FRAMES:
            return False
        state["candidate"] = None
        state["candidate_frames"] = 0
        return True

    @staticmethod
    def _pose_signature(points):
        points = np.asarray(points, dtype=np.float32)
        if points.ndim != 2 or points.shape[0] != 21 or points.shape[1] < 2:
            raise ValueError("Координати руки мають мати форму (21, 2) або (21, 3).")
        xy = points[:, :2]
        origin = xy[0]
        palm_scale = float(np.linalg.norm(xy[5] - xy[17]))
        if palm_scale < 1e-5:
            palm_scale = 1.0
        return ((xy - origin) / palm_scale).reshape(-1)

    @staticmethod
    def _signature_distance(left, right):
        if left is None or right is None or len(left) != len(right):
            return float("inf")
        return float(np.mean(np.abs(left - right)))

    def _expire_missing_slots(self, visible_sides, now):
        for slot in tuple(self._slots):
            if slot == "BOTH":
                present = {"LEFT", "RIGHT"}.issubset(visible_sides)
            else:
                present = slot in visible_sides
            if not present:
                self._expire_slot(slot, now)

    def _expire_slot(self, slot, now):
        state = self._slots.get(slot)
        if state is None:
            return
        if now - state["last_seen"] >= self.MISSING_HAND_GRACE:
            self._slots.pop(slot, None)
            self.neural_pose.reset(slot)

    def _reset_slots(self):
        self._slots.clear()
        self.neural_pose.reset()
        self.hold_progress = 0.0

    def _set_state(self, state):
        if self.state is state:
            return
        self.state = state
        self.state_changed.emit(state.value)

    def stop(self):
        close_tracker = getattr(self.tracker, "close", None)
        if close_tracker is not None:
            close_tracker()
