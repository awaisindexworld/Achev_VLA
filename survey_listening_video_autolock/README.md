# Survey Listening Video Start Button (Odoo 18)

This module adds a per-question listening video that starts only after the user clicks **Start Watching** once.

## What it does

- Adds per-question video fields on `survey.question`
- Supports either external video URL or uploaded video file
- Injects a **Start Watching** button before the video in the question description
- Hides answer options until the video finishes
- Disables replay/seek controls from the native video UI
- Locks the video when it ends
- Reveals the answer options after completion

## Intended flow

1. User opens the question
2. User clicks **Start Watching**
3. Button disables after the first click
4. Video plays without native controls
5. When the video ends, it locks
6. Answer options appear

## Installation

1. Copy this module into your custom addons path
2. Update Apps List
3. Install **Survey Listening Video Autolock**

## Notes

- Best used with **One page per question** in Survey settings
- Browser dev tools can never be fully prevented, but normal UI skipping is blocked
- The module keeps the current description-sync approach and only changes the trigger flow
