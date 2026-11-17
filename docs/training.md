# Training the Gesture Model

The Training tab records named gesture examples and trains the classifier
stored at `data/models/gesture_model.joblib`.

## Recording examples

1. Open **Training** and enter a stable gesture label.
2. Keep the hand(s) fully visible in the preview.
3. Use the single-sample button for one frame or the five-second capture
   button to gather successive frames.
4. Record varied examples for every class, including the hand side and
   camera distance expected during use.
5. Repeat for all gesture classes that should be available to rules.

The model input contains 126 values: 21 three-dimensional landmarks for the
left hand followed by 21 three-dimensional landmarks for the right hand.
Missing hand slots are zero-filled. Training samples are stored in
`data/samples/gesture_samples.npz`.

## Training and verification

Select **Train Neural Network** and wait for the training result. The trained
model and sample data are stored in the portable `data/` folder. Check the
model status in the Training tab, then verify each gesture in the Control tab.
Only recorded model classes can be predicted; adding a registry entry alone
does not train or add a class to the model.

For best results, keep lighting consistent, avoid covering landmarks, and
record examples from both left and right hands when the gesture is intended
for either side. Save a backup of `data/samples/` before clearing or replacing
training data.
