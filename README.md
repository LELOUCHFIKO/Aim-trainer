# Aim Trainer

A small offline aim trainer for Android phones and tablets. Balls appear and
shrink on a timing ring. Tap a ball when the ring touches its edge for the
best score.

## Modes
- **Timed**: 30 seconds, as many hits as you can get.
- **Survival**: 3 lives. Each miss costs a life.

## Build the APK with GitHub Actions
1. Create a new GitHub repository and upload these files.
2. Open the **Actions** tab and run **Build APK** (it also runs on each push).
3. The first build takes 30 to 60 minutes. Download `aim-trainer-apk` from the run page.
4. Copy the APK to your phone and install it. Allow installs from unknown sources.

## Run on a computer (optional)
```
pip install kivy==2.3.0
python main.py
```

Best scores are saved on the device, so the game works fully offline.
# Aim-trainer
