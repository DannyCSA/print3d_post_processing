const sideMenu = document.querySelector("aside");
const menuBtn = document.querySelector("#menu-btn");
const closeBtn = document.querySelector("#close-btn");
const themeToggler = document.querySelector(".theme-toggler");
//constantes para la opción multipágina
const home = document.querySelector(".home");
const manual = document.querySelector(".manual");
const automatic = document.querySelector(".automatic");
const test = document.querySelector(".test");
const joysticks = document.querySelector(".joysticks");

menuBtn.addEventListener('click', () => {
    sideMenu.style.display = 'block';

});

closeBtn.addEventListener('click', () => {
    sideMenu.style.display = 'none';

});
//para cambiar el tema de la página
themeToggler.addEventListener('click', () => {
    document.body.classList.toggle('dark-theme-variables');
    themeToggler.querySelector('span:nth-child(1)').classList.toggle('active');
    themeToggler.querySelector('span:nth-child(2)').classList.toggle('active');
});


function updateSliderPWMmanual(element) {
    var sliderNumber = element.id.charAt(element.id.length-1);

    var sliderValue = document.getElementById(element.id).value;
    document.getElementById("sliderValue"+sliderNumber).innerHTML = sliderValue;
    websocket.send(sliderNumber+"manual"+sliderValue.toString());
    //console.log(sliderNumber+"s"+sliderValue.toString());
}
function updateSliderPWMtest(element) {
    var sliderNumber = element.id.charAt(element.id.length-1);

    var sliderValue = document.getElementById(element.id).value;
    document.getElementById("testValue"+sliderNumber).innerHTML = sliderValue;
    websocket.send(sliderNumber+"test"+sliderValue.toString());
    //console.log(sliderNumber+"s"+sliderValue.toString());
}

//solo actualiza los valores de la parte automática
function updateSliderPWMautomatic(element) {
    var sliderNumber = element.id.charAt(element.id.length-1);
    var sliderValue = document.getElementById(element.id).value;
    document.getElementById("automaticValue"+sliderNumber).innerHTML = sliderValue;

}
    

//cambio de ventana
function show(param_div_class) {
    if(param_div_class === "home"){
        home.style.display = 'block';
        manual.style.display = 'none';
        automatic.style.display = 'none';
        test.style.display = 'none';
        joysticks.style.display = 'none';

    } else if (param_div_class === "manual"){
        home.style.display = 'none';
        manual.style.display = 'block';
        automatic.style.display = 'none';
        test.style.display = 'none';
        joysticks.style.display = 'none';
    }
    else if (param_div_class === "automatic"){
        home.style.display = 'none';
        manual.style.display = 'none';
        automatic.style.display = 'block';
        test.style.display = 'none';
        joysticks.style.display = 'none';
    }
    else if (param_div_class === "test"){
        home.style.display = 'none';
        manual.style.display = 'none';
        automatic.style.display = 'none';
        test.style.display = 'block';
        joysticks.style.display = 'none';
    }
    else if (param_div_class === "joysticks"){
        home.style.display = 'none';
        manual.style.display = 'none';
        automatic.style.display = 'none';
        test.style.display = 'none';
        joysticks.style.display = 'block';
    }
   
};


//para los websockets

var url = "ws://192.168.43.161:1337/"; //dirección de la esp32
//var url = "ws://192.168.228.195:1337/"; //dirección de la esp32
var output;
var context;

// This is called when the page finishes loading
function init() {
    // Connect to WebSocket server
    wsConnect(url);
    home.style.display = 'block';
    manual.style.display = 'none';
    automatic.style.display = 'none';
    test.style.display = 'none';
    joysticks.style.display = 'none';

    document.querySelector('.rssi_4').style.display = 'none';
    document.querySelector('.rssi_3').style.display = 'none';
    document.querySelector('.rssi_2').style.display = 'none';
    document.querySelector('.rssi_1').style.display = 'block';

};
// Call this to connect to the WebSocket server
function wsConnect(url) {
    
    // Connect to WebSocket server
    websocket = new WebSocket(url);
    
    // Assign callbacks
    websocket.onopen = function(evt) { onOpen(evt) };
    websocket.onclose = function(evt) { onClose(evt) };
    websocket.onmessage = function(evt) { onMessage(evt) };
    websocket.onerror = function(evt) { onError(evt) };
};

// Called when a WebSocket connection is established with the server
function onOpen(evt) {
    console.log("Connected");
};

// Called when the WebSocket connection is closed
function onClose(evt) {

    // Log disconnection state
    console.log("Disconnected");
    
    // Try to reconnect after a few seconds
    setTimeout(function() { wsConnect(url) }, 2000);
};

// Called when a message is received from the server
var global_json;
function onMessage(evt) {

    // Print out our received message
    //console.log("Received: " + evt.data);
    var myObj = JSON.parse(evt.data);
    global_json = myObj;

    rssilogo(myObj["rssi"]);
    ip_l(myObj["ip"]);
    hostname_l(myObj["hostname"]);
    status_l(myObj["status"]);
    ssid_l(myObj["ssid"]);
    psk_l(myObj["psk"]);
    bssid_l(myObj["bssid"]);
    positions(myObj)
};

// Called when a WebSocket error occurs
function onError(evt) {
    console.log("ERROR: " + evt.data);
};
function rssilogo(pan) {

    var newdat =pan;

    document.querySelector('#RSSI').innerHTML= "rssi: "+newdat;

    if( newdat >= -35){
        document.querySelector('.rssi_4').style.display = 'block';
        document.querySelector('.rssi_3').style.display = 'none';
        document.querySelector('.rssi_2').style.display = 'none';
        document.querySelector('.rssi_1').style.display = 'none';
    } 
    else if (newdat >= -50 && newdat < -35){
        document.querySelector('.rssi_4').style.display = 'none';
        document.querySelector('.rssi_3').style.display = 'block';
        document.querySelector('.rssi_2').style.display = 'none';
        document.querySelector('.rssi_1').style.display = 'none';
    }
    else if (newdat >= -70 && newdat < -50){
        document.querySelector('.rssi_4').style.display = 'none';
        document.querySelector('.rssi_3').style.display = 'none';
        document.querySelector('.rssi_2').style.display = 'block';
        document.querySelector('.rssi_1').style.display = 'none';
    }
    else if (newdat < -70){
        document.querySelector('.rssi_4').style.display = 'none';
        document.querySelector('.rssi_3').style.display = 'none';
        document.querySelector('.rssi_2').style.display = 'none';
        document.querySelector('.rssi_1').style.display = 'block';
    }
};

function ip_l(pan) {
    document.querySelector('#IP').innerHTML ="IP: "+ pan;
};
function hostname_l(pan){
    document.querySelector('#HOSTNAME').innerHTML = "Hostname: " + pan;
};
function status_l(pan){
    document.querySelector('#STATUS').innerHTML = "Status: " +pan;
};
function ssid_l(pan){
    document.querySelector('#SSID').innerHTML = "SSID: "+pan;
};
function psk_l(pan){
    document.querySelector('#PSK').innerHTML = "PSK: "+pan;
};
function bssid_l(pan){
    document.querySelector('#BSSID').innerHTML = "BSSID: "+pan;
};
function positions(pan) {

 
    var x = (new Date()).getTime(), y1 = parseFloat(pan["servo1"]), y2 = parseFloat(pan["servo2"]), y3 = parseFloat(pan["servo3"]), y4 = parseFloat(pan["servo4"]);
    if(chartADC_auto.series[0].data.length > 10) {
        chartADC_auto.series[0].addPoint([x, y1], true, true, true);
        chartADC_auto.series[1].addPoint([x, y2], true, true, true);
        chartADC_auto.series[2].addPoint([x, y3], true, true, true);
        chartADC_auto.series[3].addPoint([x, y4], true, true, true);
      } else {
        chartADC_auto.series[0].addPoint([x, y1], true, false, true);
        chartADC_auto.series[1].addPoint([x, y2], true, false, true);
        chartADC_auto.series[2].addPoint([x, y2], true, false, true);
        chartADC_auto.series[3].addPoint([x, y4], true, false, true);
  
    }
};



function btn_test(btn_st){
    if(btn_st === "automatic-start"){
        var automatic1 = document.getElementById("automaticslider1").value;
        var automatic2 = document.getElementById("automaticslider2").value;
        var automatic3 = document.getElementById("automaticslider3").value;
        var automatic4 = document.getElementById("automaticslider4").value;
        var automatic5 = document.getElementById("automaticslider5").value;
        var automatic6 = document.getElementById("automaticslider6").value;
        var automatic7 = document.getElementById("automaticslider7").value;
        var automatic8 = document.getElementById("automaticslider8").value;

        websocket.send("automatic-start,"+automatic1.toString()+","+automatic2.toString()+","+automatic3.toString()+","+automatic4.toString()+","+automatic5.toString()+","+automatic6.toString()+","+automatic7.toString()+","+automatic8.toString());
    } else{
    
        websocket.send(btn_st);
    }
    
};






function Draw(event) {

    if (paint) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        background();
        var angle_in_degrees,x, y, speed;
        var angle = Math.atan2((coord.y - y_orig), (coord.x - x_orig));

        if (Math.sign(angle) == -1) {
            angle_in_degrees = Math.round(-angle * 180 / Math.PI);
        }
        else {
            angle_in_degrees =Math.round( 360 - angle * 180 / Math.PI);
        }


        if (is_it_in_the_circle()) {
            joystick(coord.x, coord.y);
            x = coord.x;
            y = coord.y;
        }
        else {
            x = radius * Math.cos(angle) + x_orig;
            y = radius * Math.sin(angle) + y_orig;
            joystick(x, y);
        }

    
        getPosition(event);

        var speed =  Math.round(100 * Math.sqrt(Math.pow(x - x_orig, 2) + Math.pow(y - y_orig, 2)) / radius);

        var x_relative = Math.round(x - x_orig);
        var y_relative = Math.round(y - y_orig);

        x_relative = Math.round(((x_relative + 200) * 255) / 400);
        y_relative = Math.round(((y_relative + 200) * 255) / 400);

        document.getElementById("x_coordinate").innerText =  x_relative;
        document.getElementById("y_coordinate").innerText =y_relative ;
        document.getElementById("speed").innerText = speed;
        document.getElementById("angle").innerText = angle_in_degrees;
/*
        websocket.send(1+"joy"+x_relative.toString());  
        websocket.send(2+"joy"+y_relative.toString());
*/
        websocket.send("automatic-start,");

        //send( x_relative,y_relative,speed,angle_in_degrees);
    }
}



var canvas, ctx;

window.addEventListener('load', () => {     

    canvas = document.getElementById('canvas');
    ctx = canvas.getContext('2d');          
    resize(); 

    document.addEventListener('mousedown', startDrawing);
    document.addEventListener('mouseup', stopDrawing);
    document.addEventListener('mousemove', Draw);

    document.addEventListener('touchstart', startDrawing);
    document.addEventListener('touchend', stopDrawing);
    document.addEventListener('touchcancel', stopDrawing);
    document.addEventListener('touchmove', Draw);
    window.addEventListener('resize', resize);

    document.getElementById("x_coordinate").innerText = 0;
    document.getElementById("y_coordinate").innerText = 0;
    document.getElementById("speed").innerText = 0;
    document.getElementById("angle").innerText = 0;
});




var width, height, radius, x_orig, y_orig;
function resize() {
    width = window.innerWidth;
    radius = 200;
    height = radius * 6.5;
    ctx.canvas.width = width;
    ctx.canvas.height = height;
    background();
    joystick(width / 2, height / 3);
}

function background() {
    x_orig = width / 2;
    y_orig = height / 3;

    ctx.beginPath();
    ctx.arc(x_orig, y_orig, radius + 20, 0, Math.PI * 2, true);
    ctx.fillStyle = '#ECE5E5';
    ctx.fill();
}

function joystick(width, height) {
    ctx.beginPath();
    ctx.arc(width, height, radius, 0, Math.PI * 2, true);
    ctx.fillStyle = '#F08080';
    ctx.fill();
    ctx.strokeStyle = '#F6ABAB';
    ctx.lineWidth = 8;
    ctx.stroke();
}

let coord = { x: 0, y: 0 };
let paint = false;

function getPosition(event) {
    var mouse_x = event.clientX || event.touches[0].clientX;
    var mouse_y = event.clientY || event.touches[0].clientY;
    coord.x = mouse_x - canvas.offsetLeft;
    coord.y = mouse_y - canvas.offsetTop;
}

function is_it_in_the_circle() {
    var current_radius = Math.sqrt(Math.pow(coord.x - x_orig, 2) + Math.pow(coord.y - y_orig, 2));
    if (radius >= current_radius) return true
    else return false
}


function startDrawing(event) {
    paint = true;
    getPosition(event);
    if (is_it_in_the_circle()) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        background();
        joystick(coord.x, coord.y);
        Draw();
    }
}


function stopDrawing() {
    paint = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    background();
    joystick(width / 2, height / 3);
    document.getElementById("x_coordinate").innerText = 0;
    document.getElementById("y_coordinate").innerText = 0;
    document.getElementById("speed").innerText = 0;
    document.getElementById("angle").innerText = 0;

}







//websocket.send(message); se usa para enviar un mensaje
// Called whenever the HTML button is pressed

// Call the init function as soon as the page loads
window.addEventListener("load", init, false);




//-------------------------------------------graficas para el test mode
//-----------------------------Posiocionamiento----------------------------------------------

var colors = ['#470ce8'];
  var chartADC_auto = new Highcharts.Chart({
    chart:{ renderTo:'chart-ADC_auto' },
    title: { text: 'Temperature Control' },
    series: [{
        data: [],
        name: 'Heater Temperature'
    }
  ],
  colors:colors,

    plotOptions: {
      line: { animation: false,
        dataLabels: { enabled: true }
      },
      pie: { //working here
            colors: colors
        }
    },
    xAxis: {
      type: 'datetime',
      dateTimeLabelFormats: { second:'%S' }
    },
    yAxis: {
      title: { text: 'Temperature [0°C - 80]' }
    },
    credits: { enabled: false }
  });