[app]
title = Aim Trainer
package.name = aimtrainer
package.domain = org.aimtrainer
source.dir = .
source.include_exts = py,png,jpg,ttf
version = 1.0.0
requirements = python3,kivy==2.3.0
orientation = sensor
fullscreen = 0
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/logo.png
presplash.color = 0.06, 0.07, 0.11, 1

android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1
