import argparse
import math
import os
import sys
import time

import eventlet
eventlet.monkey_patch()

import flask
from flask.ext.socketio import SocketIO, emit

import smbus


class PWM(object):
    MODE1              = 0x00
    MODE2              = 0x01
    PRESCALE           = 0xFE
    LED0_ON_L          = 0x06
    LED0_ON_H          = 0x07
    LED0_OFF_L         = 0x08
    LED0_OFF_H         = 0x09
    ALL_LED_ON_L       = 0xFA
    ALL_LED_ON_H       = 0xFB
    ALL_LED_OFF_L      = 0xFC
    ALL_LED_OFF_H      = 0xFD

    SLEEP              = 0x10
    ALLCALL            = 0x01
    OUTDRV             = 0x04

    steps = 4096

    i2c_bus = None

    def __init__(self, address=0x40, busnum=1):
        self.address = address
        self.busnum = busnum

    def open(self):
        self.i2c_bus = smbus.SMBus(self.busnum)
        self.set_all_pwm(0, 0)
        self.i2c_bus.write_byte_data(self.address, self.MODE2, self.OUTDRV)
        self.i2c_bus.write_byte_data(self.address, self.MODE1, self.ALLCALL)
        time.sleep(0.005)  # wait for oscillator

        mode1 = self.i2c_bus.read_byte_data(self.address, self.MODE1)
        mode1 = mode1 & ~self.SLEEP  # wake up (reset sleep)
        self.i2c_bus.write_byte_data(self.address, self.MODE1, mode1)
        time.sleep(0.005)  # wait for oscillator

    def set_pwm_freq(self, freq):
        "Sets the PWM frequency"
        prescaleval = 25000000.0    # 25MHz
        prescaleval /= self.steps
        prescaleval /= float(freq)
        prescaleval -= 1.0
        prescale = math.floor(prescaleval + 0.5)

        oldmode = self.i2c_bus.read_byte_data(self.address, self.MODE1)
        newmode = (oldmode & 0x7F) | 0x10  # sleep
        self.i2c_bus.write_byte_data(self.address, self.MODE1, newmode)
        self.i2c_bus.write_byte_data(
            self.address, self.PRESCALE, int(math.floor(prescale)))
        self.i2c_bus.write_byte_data(self.address, self.MODE1, oldmode)
        time.sleep(0.005)
        self.i2c_bus.write_byte_data(
            self.address, self.MODE1, oldmode | 0x80)

    def set_pwm(self, channel, on, off):
        "Sets a single PWM channel"
        self.i2c_bus.write_byte_data(
            self.address, self.LED0_ON_L+4*channel, on & 0xFF)
        self.i2c_bus.write_byte_data(
            self.address, self.LED0_ON_H+4*channel, on >> 8)
        self.i2c_bus.write_byte_data(
            self.address, self.LED0_OFF_L+4*channel, off & 0xFF)
        self.i2c_bus.write_byte_data(
            self.address, self.LED0_OFF_H+4*channel, off >> 8)

    def set_all_pwm(self, on, off):
        "Sets a all PWM channels"
        self.i2c_bus.write_byte_data(
            self.address, self.ALL_LED_ON_L, on & 0xFF)
        self.i2c_bus.write_byte_data(
            self.address, self.ALL_LED_ON_H, on >> 8)
        self.i2c_bus.write_byte_data(
            self.address, self.ALL_LED_OFF_L, off & 0xFF)
        self.i2c_bus.write_byte_data(
            self.address, self.ALL_LED_OFF_H, off >> 8)


class FakeTreadmill(object):

    def init(self):
        self.speed = 0

    def set_speed(self, new_speed):
        self.speed = new_speed



class AdrealinTreadmill(object):

    # The treadmill can't go lower than 1.0 km/h and not higher than 8.0
    # km/h.
    MIN_SPEED = 10
    MAX_SPEED = 80

    # Don't change to the new speed directly. Instead we change it
    # by 0.1 km/h every 100 ms until we reach the desired speed.
    SPEED_INCREMENT = 1
    SPEED_INCREMENT_DELAY = 0.1

    # A 1ms pulse represents 1.0 km/h. It's all linear, but pulse is
    # always 0.2 ms longer than it should be. E.g. at 1.0 km/h, the
    # pulse length is 1.2 ms. At 2.0 km/h it's 2.2 ms. So we add 0.2
    # km/h when calculating the pulse length later.
    SPEED_OFFSET = 2

    def __init__(self, address, busnum):
        self.pwm = PWM(address=address, busnum=busnum)
        self.speed = 0

    def init(self):
        self.pwm.open()
        # Setting the frequency to 98 Hz results in a cycle of 9 ms,
        # which the treadmill expects.
        self.pwm.set_pwm_freq(98)

    def set_speed(self, new_speed):
        """Set the new speed of the treadmill.

        @param new_speed: The new speed in tenth of kilometers/hour.
        """
        new_speed = new_speed
        assert self.MIN_SPEED <= new_speed <= self.MAX_SPEED or new_speed == 0
        # 1 ms in the pulse represents 1 km/h.
        factor = 1.0/9.0/10
        offset = 2
        increment = self.SPEED_INCREMENT
        if new_speed < self.speed:
            increment *= -1
        while self.speed != new_speed:
            time.sleep(self.SPEED_INCREMENT_DELAY)
            self.speed += increment
            if self.speed < self.MIN_SPEED:
                self.speed = self.MIN_SPEED if increment > 0 else 0
            pulse_length = (
                (self.speed + self.SPEED_OFFSET) * factor * self.pwm.steps)
            pulse_length = int(math.floor(pulse_length + 0.5))
            self.pwm.set_pwm(0, 0, pulse_length)


def parse_args(raw_args):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "host",  type=str, default="localhost", nargs="?",
        help="The host address to bind.")
    parser.add_argument(
        "--port", type=int, default=8080, help="The port to listen on.")
    parser.add_argument(
        "--fake", action="store_true", default=False, help="Whether to use a fake treadmill for local testing.")
    return parser.parse_args(raw_args)


class Workout(object):

    def __init__(self, time_started, time_ended=None):
        self.time_started = time_started
        self.time_ended = time_ended

    def to_dict(self):
        return {
            "start_time": self.time_started,
            "duration": self.time_ended - self.time_started}


class Workouts(object):

    def __init__(self, file_path):
        self._file_path = file_path
        self._workouts = []

    def get_workout_dicts(self, limit=None):
        if limit is not None:
            return self._workouts[:limit]
        else:
            return list(self._workouts)

    def store_workout(self, workout):
       self._workouts.append(workout.to_dict())



class WorkoutState(object):

    state = "stopped"
    default_workout_time = 1800
    _start_time = None
    _pause_time = None
    _current_workout = None

    def __init__(self, treadmill, workouts):
        self.workout_time = self.default_workout_time
        self._treadmill = treadmill
        self._workouts = workouts

    def start(self):
        self.workout_time = self.default_workout_time
        self._start_time = time.time()
        self._current_workout = Workout(self._start_time)
        self._restart()

    def set_time_left(self, new_time_left):
        print("Updating time left: {}".format(new_time_left))
        if self.state == "stopped":
            self.default_workout_time = int(new_time_left)
        else:
            self.workout_time = int(new_time_left)
            if self.get_state() == "running":
                self._start_time = time.time()
                self._restart()

    def set_speed(self, new_speed):
        self._treadmill.set_speed(new_speed)
        if new_speed == 0:
            self.pause()
        else:
            if self.state == "paused":
                self._restart()

    def to_dict(self):
        latest_workouts = self._workouts.get_workout_dicts(limit=10)
        return {"state": self.state, "timeLeft": self.get_time_left(),
                "speed": self._treadmill.speed,
                "latest_workouts": latest_workouts}

    def get_state(self):
        if self._pause_time is not None:
            return "paused"
        if self._start_time is not None:
            return "running"
        return "stopped"

    def stop(self):
        self.state = "stopped"
        self._start_time = None
        self._treadmill.set_speed(0)
        self._current_workout.time_ended = time.time()
        self._workouts.store_workout(self._current_workout)
        self._current_workout = None
        self.workout_time = self.default_workout_time
        print("Stopped: {}".format(self.to_dict()))
        socketio.emit("initial", self.to_dict(), namespace="/api")

    def pause(self):
        print("Pausing workout.")
        self.state = "paused"
        self._pause_time = time.time()

    def _restart(self):
        print("Restarting the workout.")
        self._start_time = time.time()
        if self._pause_time is not None:
            pause_duration = time.time() - self._pause_time
            self._start_time += pause_duration
            self._pause_time = None
        self.state = "running"

    def get_time_left(self):
        if self.get_state() == "stopped":
            time_left = self.default_workout_time
        elif self.get_state() == "paused":
            time_left = self.workout_time
        else:
            elapsed = math.floor(time.time() - self._start_time + 0.5)
            time_left = self.workout_time - elapsed
        return time_left


def timer(workout):
    while True:
        time.sleep(1)
        #print("{}".format(workout.to_dict()))
        if workout.get_state() != "running":
            continue
        if workout.get_time_left() <= 0:
            workout.stop()
        else:
            socketio.emit(
                "initial", workout.to_dict(), namespace="/api")


treadmill = None
workout = None


def main(raw_args=None):
    if raw_args is None:
        raw_args = sys.argv[1:]
    args = parse_args(raw_args)
    global treadmill
    global workout
    if args.fake:
        treadmill = FakeTreadmill()
    else:
        treadmill = AdrealinTreadmill(0x40, 1)
    workouts = Workouts("")
    workout = WorkoutState(treadmill, workouts)
    treadmill.init()
    eventlet.spawn(timer, workout=workout)
    app.config["SECRET_KEY"] = "secret"
    socketio.run(app, host=args.host, port=args.port)

app = flask.Flask(__name__)
socketio = SocketIO(app)


@app.route("/speed/<int:new_speed>")
def speed(new_speed):
    if new_speed > 80:
        return "Speed can't be higher than 80"
    workout.set_speed(new_speed)
    return "New speed: {}\n".format(new_speed)


@app.route("/")
def index():
    import pkg_resources
    path = pkg_resources.resource_filename("treac", "html/" + "index.html")
    return flask.send_from_directory(os.path.dirname(path), "index.html")


@app.route("/static/<filename>")
def send_static(filename):
    import pkg_resources
    path = pkg_resources.resource_filename("treac", "html/" + filename)
    return flask.send_from_directory(os.path.dirname(path), filename)


@socketio.on('connect', namespace='/api')
def test_connect():
    msg = workout.to_dict()
    print('Client connected: {}'.format(msg))
    emit('initial', msg)


@socketio.on('disconnect', namespace='/api')
def test_disconnect():
    print('Client disconnected')

@socketio.on('change_state', namespace='/api')
def change_state(message):
    new_speed = message["speed"]
    if new_speed != treadmill.speed:
        print("Changing speed to "  + str(new_speed))
        if new_speed > 80:
            return "Speed can't be higher than 80"
        if workout.state == "stopped" and new_speed > 0:
            print("Starting workout.")
            workout.start()
        workout.set_speed(new_speed)
    new_timer = message["timeLeft"]
    print("Changing timer: {}".format(new_timer))
    workout.set_time_left(new_timer)
    emit('initial', workout.to_dict())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
