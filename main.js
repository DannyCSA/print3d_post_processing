const sideMenu = document.querySelector("aside");
const menuBtn = document.querySelector("#menu-btn");
const closeBtn = document.querySelector("#close-btn");
const themeToggler = document.querySelector(".theme-toggler");

// Page sections
const home = document.querySelector(".home");
const control = document.querySelector(".control");
const test = document.querySelector(".test");

menuBtn.addEventListener('click', () => {
    sideMenu.style.display = 'block';
});

closeBtn.addEventListener('click', () => {
    sideMenu.style.display = 'none';
});

themeToggler.addEventListener('click', () => {
    document.body.classList.toggle('dark-theme-variables');
    themeToggler.querySelector('span:nth-child(1)').classList.toggle('active');
    themeToggler.querySelector('span:nth-child(2)').classList.toggle('active');
});

function updateSliderPWMcontrol(element) {
    var sliderNumber = element.id.charAt(element.id.length - 1);
    var sliderValue = document.getElementById(element.id).value;
    document.getElementById("sliderValue" + sliderNumber).innerHTML = sliderValue;
    // Update setpoint in Firebase
    firebase.database().ref('control/setpoint').set({ setpoint: parseFloat(sliderValue) });
}

function updateSliderPWMtest(element) {
    var sliderNumber = element.id.charAt(element.id.length - 1);
    var sliderValue = document.getElementById(element.id).value;
    document.getElementById("sliderValue" + sliderNumber).innerHTML = sliderValue;
    // Update test setpoint in Firebase
    firebase.database().ref('test/setpoint').set({ setpoint: parseFloat(sliderValue) });
}

function show(param_div_class) {
    home.style.display = 'none';
    control.style.display = 'none';
    test.style.display = 'none';

    if (param_div_class === "home") {
        home.style.display = 'block';
    } else if (param_div_class === "control") {
        control.style.display = 'block';
    } else if (param_div_class === "test") {
        test.style.display = 'block';
    }

    // Remove the 'active' class from all sidebar links
    const sidebarLinks = document.querySelectorAll("aside .sidebar a");
    sidebarLinks.forEach(link => link.classList.remove('active'));

    // Add the 'active' class to the clicked link
    const activeLink = document.querySelector(`aside .sidebar a[onclick="show('${param_div_class}')"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
}

function init() {
    // Initialize Firebase
    const firebaseConfig = {
        apiKey: "AIzaSyBVyd1eUNcQWDOSVMGeISXJi9DftWrpCHg",
        authDomain: "post-proce.firebaseapp.com",
        databaseURL: "https://post-proce-default-rtdb.firebaseio.com",
        projectId: "post-proce",
        storageBucket: "post-proce.appspot.com",
        messagingSenderId: "88399104207",
        appId: "1:88399104207:web:7d7d94a5f0edc5ddf30fba",
        measurementId: "G-N26ZD0VQD0"
    };

    firebase.initializeApp(firebaseConfig);
    const database = firebase.database();
    
    // Connect to MQTT broker
    const mqttClient = mqtt.connect('wss://test.mosquitto.org:8081');

    mqttClient.on('connect', () => {
        console.log('Connected to MQTT broker');
        mqttClient.subscribe('pp_heater_temp');
        mqttClient.subscribe('pp_acetone_temp');
        mqttClient.subscribe('pp_time');
        mqttClient.subscribe('pp_sp_heater');
        mqttClient.subscribe('pp_sp_acetone');
    });

    mqttClient.on('message', (topic, message) => {
        if (topic === 'pp_acetone_temp') {
            const acetoneTemp = parseFloat(message.toString());
            document.getElementById('currentTemperature').innerText = acetoneTemp.toFixed(2);

            var x = (new Date()).getTime(), y = acetoneTemp;
            if (chartADC_auto.series[0].data.length > 40) {
                chartADC_auto.series[0].addPoint([x, y], true, true, true);
            } else {
                chartADC_auto.series[0].addPoint([x, y], true, false, true);
            }
        } else if (topic === 'pp_time') {
            const time = parseInt(message.toString(), 10);
            const formattedTime = formatTime(time);
            document.getElementById('timeLeft').innerText = formattedTime;
            document.getElementById('controlTimeLeft').innerText = formattedTime;
        } else if (topic === 'pp_sp_acetone') {
            const setpoint = parseFloat(message.toString());
            chartADC_auto.yAxis[0].removePlotLine('setpoint-line');
            chartADC_auto.yAxis[0].addPlotLine({
                id: 'setpoint-line',
                value: setpoint,
                color: 'red',
                dashStyle: 'Dash',
                width: 2,
                label: {
                    text: 'Setpoint: ' + setpoint.toFixed(2) + '°C',
                    align: 'right',
                    verticalAlign: 'bottom', // Set the vertical alignment to bottom
                    style: {
                        color: 'red'
                    }
                }
            });
        } else if (topic === 'pp_heater_temp') {
            const heaterTemp = parseFloat(message.toString());
            var x = (new Date()).getTime(), y = heaterTemp;
            if (chartADC_heater.series[0].data.length > 40) {
                chartADC_heater.series[0].addPoint([x, y], true, true, true);
            } else {
                chartADC_heater.series[0].addPoint([x, y], true, false, true);
            }
        } else if (topic === 'pp_sp_heater') {
            const setpoint = parseFloat(message.toString());
            chartADC_heater.yAxis[0].removePlotLine('setpoint-line');
            chartADC_heater.yAxis[0].addPlotLine({
                id: 'setpoint-line',
                value: setpoint,
                color: 'red',
                dashStyle: 'Dash',
                width: 2,
                label: {
                    text: 'Setpoint: ' + setpoint.toFixed(2) + '°C',
                    align: 'right',
                    verticalAlign: 'bottom', // Set the vertical alignment to bottom
                    style: {
                        color: 'red'
                    }
                }
            });
        }
    });

    show('home');
}

// Function to format time from seconds to hh:mm:ss
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
}

// Function to set time from hh:mm:ss input
function setTime() {
    const hours = parseInt(document.getElementById('timeInputHours').value) || 0;
    const minutes = parseInt(document.getElementById('timeInputMinutes').value) || 0;
    const seconds = parseInt(document.getElementById('timeInputSeconds').value) || 0;
    const totalSeconds = (hours * 3600) + (minutes * 60) + seconds;
    mqttClient.publish('pp_time', str(totalSeconds));
    firebase.database().ref('time').set({ time: totalSeconds });
}

// Highcharts configuration for ADC auto chart
var colors = ['#470ce8'];
var chartADC_auto = new Highcharts.Chart({
    chart: { renderTo: 'chart-ADC_auto' },
    title: { text: 'Acetone Temperature Control' },
    series: [{
        data: [],
        name: 'Acetone Temperature'
    }],
    colors: colors,
    plotOptions: {
        line: { animation: false, dataLabels: { enabled: true } },
        pie: { colors: colors }
    },
    xAxis: {
        type: 'datetime',
        dateTimeLabelFormats: { second: '%H:%M:%S' }
    },
    yAxis: {
        title: { text: 'Temperature [°C]' },
        min: 15,
        max: 50,
        plotLines: [{
            id: 'setpoint-line',
            color: 'red',
            dashStyle: 'Dash',
            width: 2,
            label: {
                text: 'Setpoint',
                align: 'right',
                verticalAlign: 'bottom', // Set the vertical alignment to bottom
                style: {
                    color: 'red'
                }
            }
        }]
    },
    credits: { enabled: false }
});

// Highcharts configuration for Heater temperature chart
var chartADC_heater = new Highcharts.Chart({
    chart: { renderTo: 'chart-ADC_heater' },
    title: { text: 'Heater Temperature Control' },
    series: [{
        data: [],
        name: 'Heater Temperature'
    }],
    colors: ['#e8470c'],
    plotOptions: {
        line: { animation: false, dataLabels: { enabled: true } },
        pie: { colors: ['#e8470c'] }
    },
    xAxis: {
        type: 'datetime',
        dateTimeLabelFormats: { second: '%H:%M:%S' }
    },
    yAxis: {
        title: { text: 'Temperature [°C]' },
        min: 15,
        max: 240,
        plotLines: [{
            id: 'setpoint-line',
            color: 'red',
            dashStyle: 'Dash',
            width: 2,
            label: {
                text: 'Setpoint',
                align: 'right',
                verticalAlign: 'bottom', // Set the vertical alignment to bottom
                style: {
                    color: 'red'
                }
            }
        }]
    },
    credits: { enabled: false }
});

function btn_control(action) {
    const control = action === 'control-start' ? true : false;
    firebase.database().ref('control').set({ control: control });
}

function btn_test(action) {
    const fanControl = action.includes('on');
    const fanType = action.split('-')[0];
    firebase.database().ref(`test/${fanType}_fan`).set({ fan: fanControl });
}

function btn_emergency_stop() {
    // Send the MQTT message to indicate the STOP action
    mqttClient.publish('pp_emergency_stop', '1');
    // Update Firebase with the STOP action
    firebase.database().ref('stop').set({ stop: true });
}

window.onload = init;
