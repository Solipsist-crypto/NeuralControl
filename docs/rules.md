# Action Rules

`data/rules.json` stores the gesture-to-action configuration. The Settings
tab edits this file; editing it manually is optional.

## Rule structure

The document has `version: 1` and a `rules` array. Each rule contains:

- `id`: unique identifier.
- `name`: optional label displayed in the Settings tab.
- `triggers`: one gesture/hand trigger, or two triggers for a combination.
- `combination`: `true` when both triggers must be present simultaneously.
- `hold_ms`: how long the trigger must remain stable before firing.
- `enabled`: whether the rule is active.
- `actions`: ordered action steps.

Example:

```json
{
  "version": 1,
  "rules": [
    {
      "id": "example",
      "name": "Open calculator",
      "triggers": [
        { "pose": "ПРАВА_ЛОДОНЬ", "hand": "RIGHT" }
      ],
      "combination": false,
      "hold_ms": 500,
      "enabled": true,
      "actions": [
        { "action": "Відкрити Калькулятор", "params": {} }
      ]
    }
  ]
}
```

Each action step has an `action` name and a `params` object. A sequence runs
in order. The **Wait** step pauses before the next action. Two-trigger rules
require separate left and right hands. Make sure each trigger uses the side
on which its gesture was recorded.

## Action catalog

The Settings dialog exposes these action names:

- **Applications, browser, and files:** Open Telegram; Open Chrome; Open
  Steam; Open Discord; Open OBS Studio; Open Calculator; Open Notepad; Open
  File Explorer; Open Task Manager; Open Terminal; Open System Settings; Open
  application (executable path); Close active application; Force-close
  application; Open URL; Open new tab; Close current tab; Restore closed tab;
  Next tab; Previous tab; Refresh page (F5); Open folder; Open Downloads; Open
  Desktop; Open Recycle Bin; Empty Recycle Bin.
- **Media, audio, and microphone:** Volume up; Volume down; Set volume to a
  percentage; Toggle mute; Toggle microphone; Play/Pause; Next track; Previous
  track; Stop playback; Seek backward 10 seconds; Seek forward 10 seconds;
  Switch audio output device.
- **Windows and desktops:** Minimize window; Maximize window; Restore window;
  Minimize all windows; Close current window; Switch application (Alt+Tab);
  Snap window left; Snap window right; Create virtual desktop; Next virtual
  desktop; Previous virtual desktop; Delete current virtual desktop; Show Task
  View (Win+Tab).
- **Mouse, keyboard, and input:** Mouse mode; Move cursor to coordinates; Left
  click; Right click; Double click; Triple click; Hold left button; Release
  left button; Scroll up; Scroll down; Scroll left; Scroll right; Press
  hotkeys; Type text; Press Enter; Press Escape; Press Space; Press Backspace;
  Press Tab.
- **Screenshots, recording, and clipboard:** Full-screen screenshot; Active
  window screenshot; Region screenshot; Save screenshot to file; Copy
  screenshot to clipboard; Start/Stop screen recording; Save last N minutes of
  replay; Copy selection; Paste from clipboard; Cut selection; Copy custom
  text to clipboard; Clear clipboard.
- **System, display, and power:** Brightness up; Brightness down; Set
  brightness to a percentage; Toggle Night Light; Toggle Wi-Fi; Toggle
  Bluetooth; Toggle Do Not Disturb; Lock screen (Win+L); Sleep; Hibernate;
  Restart PC; Shut down PC; Shut down after N minutes; Cancel shutdown timer;
  Sign out; Switch monitor input.
- **Utilities and scripts:** Run console command; Run Python script; Reload
  configuration; Show system toast notification; No action; Wait.

Some system-dependent catalog actions are platform-specific or may report
that they are not implemented. Actions that can close applications, clear
data, run arbitrary commands, or change power state request confirmation.

## Mouse mode

Assign **Mouse mode** as an action in a gesture rule. While active, the
index-finger tip controls the cursor. The gesture that entered the mode is
also its exit gesture; change the pose and present it again to exit. Normal
gesture rules are suppressed while mouse mode is active. Bind click actions
to separate gesture rules if desired.
