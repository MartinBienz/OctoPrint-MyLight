# Mylight plugin for Octoprint

Simple Plugin that places a button in the navigation bar of OctoPrint to enable / disable a light(s) connected to the GPIOs of your Raspberry Pi. Also supports a connected rotary encoder with integrated switch, and LED's (you can also just connect a Switch and and indicator LED if you want. By using the rotary encoder and enabling Soft PWM on the "Light" Pin, you can control the brightness of the LED's / Light. Click the switch once to toggle the light(s) on or off. Enable the longpress function to shutdown the pi (configurable duration). The red LED output in the settings is used as indicator light to register clicks and longpress events visually.
![alt plugin off](/pics/mylight_off.png)


## Setup

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager)
or manually using this URL:

    https://github.com/MartinBienz/OctoPrint-MyLight/archive/master.zip


## Configuration

![alt config screen 1](/pics/mylight_config_1.png)
![alt config screen 2](/pics/mylight_config_2.png)
