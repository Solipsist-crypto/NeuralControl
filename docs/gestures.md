# Gesture Catalog

Gesture identifiers are stored in `data/gesture_registry.json`. A registry
entry records the pose ID, expected hand (`LEFT`, `RIGHT`, `ANY`, or `BOTH`),
enabled state, hold time, and a legacy action field. Runtime actions are
configured by rules in `data/rules.json`.

The registry is a catalog, not proof that a gesture has training examples.
The classifier can recognize only labels included in the currently trained
model. Record examples and retrain before assigning a newly added gesture.

## Single-hand poses

| ID | Meaning |
| --- | --- |
| `FIST` | Closed fist |
| `OPEN` | Open palm |
| `POINT` | Index finger pointing |
| `POINT_DOWN` | Index finger pointing down |
| `PINCH` | Thumb and index finger pinch |
| `PEACE` | Two-finger V pose |
| `THUMB_UP` | Thumb up |
| `THUMB_DOWN` | Thumb down |
| `ROCK` | Rock-horns pose |
| `OK` | Thumb and index finger form an OK sign |
| `THREE`, `FOUR`, `COUNT_1`, `COUNT_2`, `COUNT_3`, `COUNT_4`, `COUNT_5` | Finger-count poses |
| `PINKY_UP` | Little finger raised |
| `MIDDLE_UP` | Middle finger raised |
| `CALL_ME` | Thumb and little finger extended |
| `GUN` | Finger-gun pose |
| `CLAW` | Curled claw pose |
| `C_SHAPE` | C-shaped hand |
| `PINCH_MIDDLE` | Thumb and middle finger pinch |
| `PINCH_RING` | Thumb and ring finger pinch |
| `PINCH_PINKY` | Thumb and little finger pinch |
| `VULCAN` | Vulcan salute |
| `I_LOVE_YOU` | I-love-you hand sign |
| `CROSSED_FINGERS` | Crossed fingers |
| `WAVE` | Wave gesture |
| `SWIPE_LEFT`, `SWIPE_RIGHT`, `SWIPE_UP`, `SWIPE_DOWN` | Directional swipe |
| `CIRCLE_CW`, `CIRCLE_CCW` | Clockwise or counter-clockwise circle |
| `DRAW_CHECK`, `DRAW_X` | Draw a check mark or X in the air |
| `ЛІВА_ЛОДОНЬ` | User-trained left-palm class |
| `ЛІВИЙ_КУЛАК` | User-trained left-fist class |
| `ПРАВА_ЛОДОНЬ` | User-trained right-palm class |

## Two-hand poses

| ID | Meaning |
| --- | --- |
| `BOTH_PINCH` | Pinch with both hands |
| `BOTH_POINT` | Point with both hands |
| `BOTH_PEACE` | V pose with both hands |
| `BOTH_THUMB_UP` | Thumbs up with both hands |
| `CLAP_POSE` | Hands positioned for clapping |
| `T_SHAPE` | T-shaped two-hand pose |
| `FRAME` | Frame formed with both hands |
| `X_CROSS` | Crossed-hand pose |
| `BOTH_HEART` | Heart shape formed with both hands |
| `ZOOM_IN`, `ZOOM_OUT` | Two-hand zoom motions |

## Recognition and actions

The registry's `hand` field constrains which hand slots can produce a
prediction. The rule trigger must use the same hand side as the recorded
examples. Actions are not hard-coded to gesture IDs: a rule can bind any
trained pose or two-hand combination to a single action or an action sequence.

The release is built from the current dataset and model. Check the Training
tab to see which classes currently have examples; IDs listed above may still
need training before they can be recognized.
