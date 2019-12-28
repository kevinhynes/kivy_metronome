from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import NumericProperty, ListProperty
from kivy.graphics import Ellipse, Color, InstructionGroup

from threading import Thread, Event
import time, wave, pyaudio, math


class BeatMarker(InstructionGroup):

    def __init__(self, cx, cy, r, **kwargs):
        super().__init__()
        self.anim_color = Color()
        self.anim_circle = Ellipse(pos=[cx, cy], size=[2*r, 2*r])
        self.color = Color()
        self.marker = Ellipse(pos=[cx, cy], size=[2*r, 2*r])

        self.add(self.anim_color)
        self.add(self.anim_circle)
        self.add(self.color)
        self.add(self.marker)

        self.pos = cx, cy
        self.size = [2*r, 2*r]
        self.r = r
        self.max_rdiff = r * 0.1

    @property
    def pos(self):
        return self.pos

    @pos.setter
    def pos(self, pos):
        self.anim_circle.pos = pos
        self.marker.pos = pos

    @property
    def size(self):
        return self.size

    @size.setter
    def size(self, size):
        self.anim_circle.size = size
        self.marker.size = size


    def update_animation(self, progress):
        rdiff = progress * self.max_rdiff
        cx, cy = self.anim_circle.pos
        d, d = self.anim_circle.size
        self.anim_circle.pos = cx - rdiff, cy - rdiff
        self.anim_circle.size = [2 * (d/2 + rdiff), 2 * (d/2 + rdiff)]
        self.anim_color.a = progress


class BeatBar(FloatLayout):
    num_beats = NumericProperty(4)

    def __init__(self, **kwargs):
        super().__init__()
        self.beatmarkers = InstructionGroup()
        r = (self.height / 2) * 0.75
        rdiff = self.height / 2 - r
        cx, cy = self.x + rdiff, self.y + rdiff
        step_x = self.width / 4
        for i in range(self.num_beats):
            beatmarker = BeatMarker(cx, cy, r)
            self.beatmarkers.add(beatmarker)
            cx += step_x
        self.canvas.add(self.beatmarkers)

    # def on_num_beats(self):
    #     self.circles.clear()
    #     r = (self.height / 2) * 0.75
    #     rdiff = self.height / 2 - r
    #     step_x = self.width / 4
    #     for i in range(self.num_beats):
    #         circle = Ellipse(pos=[self.x + rdiff + i * step_x , self.y + rdiff])
    #         self.circles.append(circle)
    #         self.canvas.add(circle)

    def on_size(self, *args):
        r = (self.height / 2) * 0.75
        rdiff = self.height / 2 - r
        cx, cy = self.x + rdiff, self.y + rdiff
        step_x = self.width / self.num_beats
        for beatmarker in self.beatmarkers.children:
            beatmarker.pos = [cx, cy]
            beatmarker.size = [2*r, 2*r]
            cx += step_x

class Metronome(FloatLayout):
    needle_angle = NumericProperty(0)

    def __init__(self, **kwargs):
        self.box = BoxLayout()
        self.beatbar = FloatLayout()
        self.buttonbar = BoxLayout()
        self.max_needle_angle = 35
        super().__init__()
        self.bpm = 200
        self.spb = 60 / self.bpm
        self.time_sig = 4
        self.stop_event = Event()
        self.accent_file = "./sounds/metronome-klack.wav"
        self.beat_file = "./sounds/metronome-click.wav"

        self.player = pyaudio.PyAudio()
        high = wave.open(self.accent_file, "rb")
        low = wave.open(self.beat_file, "rb")
        self.high_data = high.readframes(2048)
        self.low_data = low.readframes(2048)
        self.stream = self.player.open(
            format=self.player.get_format_from_width(high.getsampwidth()),
            channels=high.getnchannels(),
            rate=high.getframerate(),
            output=True)

    def play(self, *args):
        thread = Thread(target=self._play, daemon=True)
        thread.start()

    def _play(self, *args):
        '''Update the Metronome's needle angle on every iteration, play beat at appropriate times.

        Since progress goes from 0-1, and beats are being represented by max, min of cos wave,
        we are constantly traversing 0-pi in the wave. Keep track of parity so we know if needle
        angle needs to be negative.
        '''
        testmax = 0
        beat_num = 0
        beat_parity = 1
        start = time.time()
        while not self.stop_event.is_set():
            beats_so_far, t_after_b = divmod(time.time() - start, self.spb)
            progress = t_after_b / self.spb
            if beats_so_far > beat_num:
                beat_num = beats_so_far
                beat_parity *= -1
                if beat_num % self.time_sig == 0:
                    self.stream.write(self.high_data)
                else:
                    self.stream.write(self.low_data)
            self.needle_angle = self.max_needle_angle * math.cos(progress * math.pi) * beat_parity
            self.stop_event.wait(self.spb/50)  # prevents mouse hover from freezing needle (?)
        self.stop_event.clear()

    def stop(self, *args):
        self.stop_event.set()
        self.needle_angle = 0

    def close(self, *args):
        self.stream.close()
        self.player.terminate()

    def on_size(self, *args):
        target_ratio = 1.5
        width, height = self.size
        if width / height > target_ratio:
            self.box.height = height
            self.box.width = target_ratio * height
        else:
            self.box.width = width
            self.box.height = width / target_ratio

class MetronomeApp(App):
    def build(self):
        return Metronome()


if __name__ == "__main__":
    MetronomeApp().run()

