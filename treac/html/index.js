var Workout = Backbone.Model.extend({
        defaults: {
            speed: 0,
            timeLeft: 0,
            state: "stopped"
        },
        updateState: function(newState) {
            console.log("update state");
            this.set(newState.attributes);
        },
        send: function() {
            socket.emit("change-state", this.attributes);
        }
        });


var serverState = new Workout({});
var clientState = new Workout({});
clientState.on("change:speed", function(model) {
    var speed = model.get("speed");
    console.log("Changed speed: " + speed);
    speedSlider.noUiSlider.set(speed);
    document.getElementById('speed').textContent = speedFormat.to(speed);
    }, clientState);
clientState.on("change:timeLeft", function(model) {
    var timeLeft = model.get("timeLeft");
    console.log("Changed timeLeft: " + timeLeft);
    timerSlider.noUiSlider.set(timeLeft);
    document.getElementById('timer').textContent = formatTime(timeLeft);
    }, clientState);

function formatTime( seconds ) {
    var date = new Date(null);
    date.setSeconds(Math.round(seconds));
    return date.toISOString().substr(11, 8);
};

var speedSlider = document.getElementById('speed-slider');

var speedFormat = {
    to: function ( value ) {
        var newValue = value / 10.0;
        return newValue.toFixed(1);
    },
    from: function ( value ) {
        return value;
    }
};

var timerFormat = {
    to: function ( value ) {
        return formatTime(value);
    },
    from: function ( value ) {
        return value;
    }
};

noUiSlider.create(speedSlider, {
    start: 0,
    connect: 'lower',
    step: 1,
    range: {
        min: 0,
        max: 90
    },
    pips: {
        mode: 'values',
        values: [0, 10, 20, 30, 40, 50, 60, 70, 80],
        density: 1,
        format: speedFormat
    },
    format: speedFormat
});
var timerSlider = document.getElementById('timer-slider');


noUiSlider.create(timerSlider, {
    start: 0,
    connect: 'lower',
    orientation: 'vertical',
    direction: 'rtl',
    step: 1,
    range: {
        min: 0,
        max:1800 
    },
    pips: {
        mode: 'values',
        values: [0, 300, 600, 900, 1200, 1500, 1800],
        density: 1,
        format: timerFormat
    },
    format: timerFormat
});
speedSlider.noUiSlider.on('change', function ( values, handle, unencodedValues ) {
    var speed = unencodedValues[handle];
    if ( speed < 10 ) {
        clientState.set({"speed": 0});
    }
    if ( speed > 80 ) {
        clientState.set({"speed": 80});
    }
    clientState.send();
});
speedSlider.noUiSlider.on('update', function ( values, handle, unencodedValues ) {
    clientState.set({"speed": unencodedValues[handle]});
});


timerSlider.noUiSlider.on('slide', function ( values, handle, unencodedValues ) {
    isSlidingTimer = true;

    document.getElementById('timer').textContent = values[handle]
});

timerSlider.noUiSlider.on('update', function ( values, handle, unencodedValues ) {
    clientState.set({"timeLeft": unencodedValues[handle]});
});

timerSlider.noUiSlider.on('change', function ( values, handle, unencodedValues ) {
    isSlidingTimer = false;
    clientState.send();
});

var socket = io.connect("/api");
socket.on("initial", function(msg) {
    console.log("initial: " + msg.state);
    console.log("initial timeLeft: " + msg.timeLeft);
    serverState.set({
        "speed": msg.speed, "timeLeft": msg.timeLeft, "state": msg.state});
    clientState.updateState(serverState);
    if (msg.state == "running") {
        workoutEnd = new Date().getTime() + msg.timeLeft * 1000;
    } else if (msg.state == "stopped") {
        workoutEnd = null;
    }
});
socket.on("timer", function(msg) {
    clientState.set({"timeLeft": msg.timeLeft});
});

var workoutEnd = null;
var isSlidingTimer = false;

function timer() {
    if (workoutEnd !== null) {
        var currentDate = new Date().getTime();
        var secondsLeft = (workoutEnd - currentDate) / 1000;
        if (!isSlidingTimer) {
            clientState.set({"timeLeft": secondsLeft});
        }
    }
};
setInterval(timer, 1000);
$( "#stop" ).on("click", function () {
    socket.emit("change-state", {"state": "stopped"});
});
