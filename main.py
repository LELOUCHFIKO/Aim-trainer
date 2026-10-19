"""Aim Trainer: tap the balls before their timing ring closes in."""
import json
import math
import os
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.widget import Widget

BG = (0.06, 0.07, 0.11, 1)
PANEL = (0.11, 0.13, 0.19, 1)
ACCENT = (0.2, 0.55, 0.95, 1)
BALL = (0.2, 0.65, 1, 1)
RING = (1, 1, 1, 0.85)
TEXT = (0.95, 0.96, 0.98, 1)
MUTED = (0.6, 0.65, 0.75, 1)
GOOD = (0.35, 0.9, 0.5, 1)
BAD = (1, 0.4, 0.4, 1)

FRAME = 1 / 60.0
ROUND_SECONDS = 30
START_LIVES = 3
HITS_PER_LEVEL = 8


def make_label(**kwargs):
    kwargs.setdefault("halign", "center")
    kwargs.setdefault("valign", "middle")
    kwargs.setdefault("color", TEXT)
    label = Label(**kwargs)
    label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
    return label


def make_button(text, callback, color=ACCENT):
    button = Button(
        text=text,
        font_size=sp(20),
        color=TEXT,
        background_normal="",
        background_color=color,
        size_hint_y=None,
        height=dp(56),
    )
    button.bind(on_release=callback)
    return button


def scores_path():
    return os.path.join(App.get_running_app().user_data_dir, "scores.json")


def load_scores():
    try:
        with open(scores_path()) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def save_scores(data):
    try:
        with open(scores_path(), "w") as handle:
            json.dump(data, handle)
    except OSError:
        pass


class Target:
    def __init__(self, x, y, radius, shrink_time):
        self.x = x
        self.y = y
        self.radius = radius
        self.shrink_time = shrink_time
        self.lifetime = shrink_time + 0.25
        self.age = 0.0

    def ring_radius(self):
        progress = min(self.age / self.shrink_time, 1.0)
        return self.radius * (3.0 - 2.0 * progress)

    def accuracy(self):
        extra = self.ring_radius() - self.radius
        return max(0.0, 1.0 - extra / (2.0 * self.radius))


class PlayArea(Widget):
    def __init__(self, hit_cb, miss_cb, tick_cb, **kwargs):
        super().__init__(**kwargs)
        self.hit_cb = hit_cb
        self.miss_cb = miss_cb
        self.tick_cb = tick_cb
        self.targets = []
        self.playing = False
        self.paused = False
        self.base_radius = dp(40)
        self.ticker = None
        self.since_spawn = 0.0
        self.set_level(0)

    def set_level(self, level):
        self.ball_radius = max(dp(24), self.base_radius * max(0.7, 1 - 0.03 * level))
        self.shrink_time = max(0.8, 1.6 - 0.05 * level)
        self.spawn_gap = max(0.35, 1.0 - 0.05 * level)
        self.max_targets = min(5, 2 + level // 3)

    def start(self):
        self.stop()
        self.base_radius = min(max(min(self.width, self.height) * 0.09, dp(28)), dp(64))
        self.set_level(0)
        self.since_spawn = self.spawn_gap
        self.playing = True
        self.paused = False
        self.ticker = Clock.schedule_interval(self.tick, FRAME)

    def stop(self):
        self.playing = False
        self.paused = False
        if self.ticker:
            self.ticker.cancel()
            self.ticker = None
        self.targets = []
        self.canvas.clear()

    def pause(self):
        if self.playing and not self.paused:
            self.paused = True
            if self.ticker:
                self.ticker.cancel()
                self.ticker = None

    def resume(self):
        if self.playing and self.paused:
            self.paused = False
            self.ticker = Clock.schedule_interval(self.tick, FRAME)

    def tick(self, dt):
        if not self.playing or self.paused:
            return False
        self.tick_cb(dt)
        if not self.playing:
            return False

        self.since_spawn += dt
        if self.since_spawn >= self.spawn_gap and len(self.targets) < self.max_targets:
            self.since_spawn = 0.0
            self.spawn()

        for target in list(self.targets):
            target.age += dt
            if target.age >= target.lifetime:
                self.targets.remove(target)
                self.miss_cb()
                if not self.playing:
                    return False

        self.draw()
        return True

    def spawn(self):
        r = self.ball_radius
        margin = r * 3
        if self.width < margin * 2 or self.height < margin * 2:
            return
        for _ in range(30):
            x = random.uniform(self.x + margin, self.right - margin)
            y = random.uniform(self.y + margin, self.top - margin)
            if all(math.hypot(x - t.x, y - t.y) > r * 3 for t in self.targets):
                self.targets.append(Target(x, y, r, self.shrink_time))
                return

    def on_touch_down(self, touch):
        if not (self.playing and not self.paused) or not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)

        best = None
        for target in self.targets:
            if math.hypot(touch.x - target.x, touch.y - target.y) <= target.radius:
                if best is None or target.accuracy() > best.accuracy():
                    best = target

        if best is None:
            self.miss_cb()
        else:
            self.targets.remove(best)
            self.hit_cb(best.accuracy())
        return True

    def draw(self):
        self.canvas.clear()
        with self.canvas:
            Color(*BG)
            Rectangle(pos=self.pos, size=self.size)
            for target in self.targets:
                r = target.radius
                Color(*BALL)
                Ellipse(pos=(target.x - r, target.y - r), size=(r * 2, r * 2))
                Color(*RING)
                Line(circle=(target.x, target.y, target.ring_radius()), width=dp(2))


class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        box = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(10))
        box.add_widget(Image(source="assets/logo.png", allow_stretch=True, keep_ratio=True))
        box.add_widget(make_label(text="Tap to start", font_size=sp(18), color=MUTED,
                                  size_hint_y=None, height=dp(40)))
        self.add_widget(box)
        self.timer = Clock.schedule_once(self.go_menu, 2.5)

    def go_menu(self, *args):
        if self.timer:
            self.timer.cancel()
            self.timer = None
        if self.manager and self.manager.current == "splash":
            self.manager.current = "menu"

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.go_menu()
            return True
        return super().on_touch_down(touch)


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        box = BoxLayout(orientation="vertical", padding=dp(30), spacing=dp(14))
        box.add_widget(make_label(text="AIM TRAINER", font_size=sp(36), bold=True, size_hint_y=0.3))
        self.best_label = make_label(font_size=sp(16), color=MUTED, size_hint_y=0.12)
        box.add_widget(self.best_label)
        box.add_widget(make_button("Timed  (30 seconds)", lambda *_: self.start_round("timed")))
        box.add_widget(make_button("Survival  (3 lives)", lambda *_: self.start_round("survival")))
        box.add_widget(make_button("Quit", lambda *_: App.get_running_app().stop(), color=PANEL))
        self.add_widget(box)

    def on_pre_enter(self, *args):
        scores = load_scores()
        self.best_label.text = "Best   timed {}   survival {}".format(
            scores.get("timed", 0), scores.get("survival", 0))

    def start_round(self, mode):
        self.manager.get_screen("game").prepare(mode)
        self.manager.current = "game"


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active = False
        self.popup = None

        root = BoxLayout(orientation="vertical")
        hud = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(10), dp(6)], spacing=dp(8))
        self.score_label = make_label(font_size=sp(18), bold=True)
        self.info_label = make_label(font_size=sp(16), color=MUTED)
        self.streak_label = make_label(font_size=sp(16), color=MUTED)
        pause_button = Button(text="II", font_size=sp(18), size_hint_x=None, width=dp(56),
                              background_normal="", background_color=PANEL, color=TEXT)
        pause_button.bind(on_release=lambda *_: self.pause())
        for widget in (self.score_label, self.info_label, self.streak_label, pause_button):
            hud.add_widget(widget)

        self.feedback = make_label(font_size=sp(20), bold=True, size_hint_y=None, height=dp(36))
        self.area = PlayArea(hit_cb=self.handle_hit, miss_cb=self.handle_miss, tick_cb=self.handle_tick)

        root.add_widget(hud)
        root.add_widget(self.feedback)
        root.add_widget(self.area)
        self.add_widget(root)
        self.prepare("timed")

    def prepare(self, mode):
        self.mode = mode
        self.score = 0
        self.hits = 0
        self.misses = 0
        self.streak = 0
        self.best_streak = 0
        self.lives = START_LIVES
        self.time_left = float(ROUND_SECONDS)
        self.feedback.text = ""
        self.refresh_hud()

    def on_enter(self, *args):
        self.active = True
        self.area.start()

    def refresh_hud(self):
        self.score_label.text = "Score {}".format(self.score)
        self.streak_label.text = "Streak {}".format(self.streak)
        if self.mode == "timed":
            self.info_label.text = "Time {}".format(int(self.time_left))
        else:
            self.info_label.text = "Lives {}".format(self.lives)

    def show_feedback(self, text, color):
        self.feedback.text = text
        self.feedback.color = color
        Clock.unschedule(self.clear_feedback)
        Clock.schedule_once(self.clear_feedback, 0.4)

    def clear_feedback(self, *args):
        self.feedback.text = ""

    def handle_tick(self, dt):
        if not self.active or self.mode != "timed":
            return
        before = int(self.time_left)
        self.time_left -= dt
        if self.time_left <= 0:
            self.finish()
        elif int(self.time_left) != before:
            self.refresh_hud()

    def handle_hit(self, accuracy):
        if not self.active:
            return
        self.hits += 1
        self.streak += 1
        self.best_streak = max(self.best_streak, self.streak)
        self.score += 20 + int(180 * accuracy) + 5 * min(self.streak, 20)
        if accuracy >= 0.8:
            text = "PERFECT"
        elif accuracy >= 0.45:
            text = "GOOD"
        else:
            text = "OK"
        self.area.set_level(self.hits // HITS_PER_LEVEL)
        self.show_feedback(text, GOOD)
        self.refresh_hud()

    def handle_miss(self):
        if not self.active:
            return
        self.misses += 1
        self.streak = 0
        if self.mode == "survival":
            self.lives -= 1
            if self.lives <= 0:
                self.finish()
                return
        self.show_feedback("MISS", BAD)
        self.refresh_hud()

    def finish(self):
        if not self.active:
            return
        self.active = False
        self.area.stop()

        shots = self.hits + self.misses
        accuracy = round(100.0 * self.hits / shots) if shots else 0
        scores = load_scores()
        previous = scores.get(self.mode, 0)
        new_best = self.score > previous
        if new_best:
            scores[self.mode] = self.score
            save_scores(scores)

        App.get_running_app().last_result = {
            "mode": self.mode,
            "score": self.score,
            "accuracy": accuracy,
            "best_streak": self.best_streak,
            "best": max(self.score, previous),
            "new_best": new_best,
        }
        self.manager.current = "result"

    def pause(self):
        if not self.active or self.popup is not None:
            return
        self.area.pause()
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        box.add_widget(make_label(text="Paused", font_size=sp(24), bold=True))
        box.add_widget(make_button("Resume", lambda *_: self.resume()))
        box.add_widget(make_button("Quit to menu", lambda *_: self.quit_to_menu(), color=PANEL))
        self.popup = Popup(title="", content=box, separator_height=0,
                           size_hint=(0.85, 0.45), auto_dismiss=False)
        self.popup.open()

    def resume(self):
        self.close_popup()
        self.area.resume()

    def quit_to_menu(self):
        self.close_popup()
        self.active = False
        self.area.stop()
        self.manager.current = "menu"

    def close_popup(self):
        if self.popup is not None:
            self.popup.dismiss()
            self.popup = None

    def on_back(self):
        if self.popup is not None:
            self.resume()
        else:
            self.pause()


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        box = BoxLayout(orientation="vertical", padding=dp(30), spacing=dp(14))
        self.title_label = make_label(font_size=sp(30), bold=True, size_hint_y=0.25)
        self.stats_label = make_label(font_size=sp(18), size_hint_y=0.4)
        box.add_widget(self.title_label)
        box.add_widget(self.stats_label)
        box.add_widget(make_button("Play again", self.play_again))
        box.add_widget(make_button("Menu", lambda *_: setattr(self.manager, "current", "menu"),
                                   color=PANEL))
        self.add_widget(box)

    def on_pre_enter(self, *args):
        result = App.get_running_app().last_result
        if not result:
            return
        self.title_label.text = "NEW BEST!" if result["new_best"] else "Round over"
        self.stats_label.text = (
            "Score  {score}\n"
            "Accuracy  {accuracy}%\n"
            "Best streak  {best_streak}\n"
            "Best {mode}  {best}"
        ).format(**result)

    def play_again(self, *args):
        result = App.get_running_app().last_result
        self.manager.get_screen("game").prepare(result["mode"])
        self.manager.current = "game"


class AimTrainerApp(App):
    title = "Aim Trainer"

    def build(self):
        Window.clearcolor = BG
        self.last_result = None
        self.sm = ScreenManager(transition=FadeTransition(duration=0.25))
        self.sm.add_widget(SplashScreen(name="splash"))
        self.sm.add_widget(MenuScreen(name="menu"))
        self.sm.add_widget(GameScreen(name="game"))
        self.sm.add_widget(ResultScreen(name="result"))
        Window.bind(on_keyboard=self.handle_key)
        return self.sm

    def handle_key(self, window, key, *args):
        if key != 27:  # Android back button or Esc on desktop
            return False
        if self.sm.current == "game":
            self.sm.get_screen("game").on_back()
            return True
        if self.sm.current == "result":
            self.sm.current = "menu"
            return True
        return False

    def on_pause(self):
        # Keep the app alive in the background, but pause the round.
        if self.sm.current == "game":
            self.sm.get_screen("game").pause()
        return True


if __name__ == "__main__":
    AimTrainerApp().run()
