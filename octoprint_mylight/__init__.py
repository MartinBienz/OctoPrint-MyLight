# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.util import RepeatedTimer

#import smbus
#import RPi.GPIO as GPIO
import math
import time
import flask

try:
	import smbus
except ImportError:
	raise Exception("smbus import Error, needed for i2c communication.")

try:
	import RPi.GPIO as GPIO
except ImportError:
	raise Exception("RPi.GPIO import Error, not running on the PI? Module not installed?")


class MyLightPlugin(octoprint.plugin.StartupPlugin,
							octoprint.plugin.ShutdownPlugin,
							octoprint.plugin.EventHandlerPlugin,
							octoprint.plugin.SimpleApiPlugin,
							octoprint.plugin.TemplatePlugin,
							octoprint.plugin.SettingsPlugin,
							octoprint.plugin.AssetPlugin):

	def initialize(self):
		self._logger.info("MyLight ("+self.get_version()+") - Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))
		if GPIO.VERSION < "0.6":
			raise Exception("MyLight - RPi.GPIO must be greater than 0.6")
		
		#check on the mode if GPIO already initialised by someone else
		#mode = GPIO.getmode()
		
		if self._settings.get(['gpio_use_board']) == True:
			GPIO.setmode(GPIO.BOARD)
		else:
			GPIO.setmode(GPIO.BCM)
		
		GPIO.setwarnings(True)
		
		#init timer for i2c communication
		self._checkI2CTimer = None
		
		self.i2c_bus = smbus.SMBus(1)
		self.i2c_slave_address = 0x04
		
		# Using a dictionary as a lookup table to give a name to gpio_function() return code  
		self.gpio_port_use = {0:"GPIO.OUT", 1:"GPIO.IN",40:"GPIO.SERIAL",41:"GPIO.SPI",42:"GPIO.I2C",  43:"GPIO.HARD_PWM", -1:"GPIO.UNKNOWN"}  
		
		self.light_on = False
		self.re_switch_prev_input=0
		self.last_delta = 0
		self.r_seq = 0 #self.rotation_sequence()
		
		self.end_press=0
		self.start_press=0
		self.switch_laststate=-1
				
		self.pwm_dc=self._settings.get_int(['light_dc'])
		
		self.defined_pins={}
		
		self.i2c_status=-1
		self.i2c_last_status=-1
		
		self.startI2CTimer(1)

	
	def checkI2C(self):
		try:
			self.i2c_status = self.i2c_bus.read_byte(self.i2c_slave_address)
		except IOError, (errno, strerror):
			print "i2c checkI2C - I/O error(%s): %s" % (errno, strerror)
			#return -1
		
		if self.i2c_status != self.i2c_last_status:
			
			self._logger.info("MyLight ("+self.get_version()+") - i2c status changed '{0}'...".format(self.i2c_status))
			if self.i2c_status == 1:
				self.light_on = False
			if self.i2c_status == 2:
				self.light_on = True
			if self.i2c_status == 4:
				if self._settings.get(['shutdown_longpress']) == True: 
					self.gpio_cleanup()
					self.shutdown_system()
			if  5 <= self.i2c_status <= 255:
				self.light_on = True
				self.pwm_dc = self.i2c_status
						
			self.i2c_last_status = self.i2c_status
			self._plugin_manager.send_plugin_message(self._identifier, dict(light_status=self.get_light_status(), light_dc=self.pwm_dc))
		
		return self.i2c_status
	
	def writeI2C(self, value):
		try:
			self.i2c_bus.write_byte(self.i2c_slave_address, value) # 5 = I/O error
		except IOError, (errno, strerror):
			print "i2c writeI2C - I/O error(%s): %s" % (errno, strerror)
			return -1
		return 0
	
	def stopI2CTimer(self):
		if self._checkI2CTimer is not None:
			try:
				self._checkI2CTimer.cancel()
			except:
				pass
	
	def startI2CTimer(self, interval):
		self._checkI2CTimer = RepeatedTimer(interval, self.checkI2C, None, None, True)
		self._checkI2CTimer.start()
		
	def get_light_status(self):
		return self.light_on
	
	def set_light_on(self, to):
		
		if to == True:
			self.writeI2C(2);
			if self._settings.get(['light_use_pwm']) == True:
				self.pwm.start(int(self._settings.get(['light_dc']))) # Set the duty cycle
			else:
				GPIO.output(int(self._settings.get(['light_pin'])), 1)
			self.light_on = True
		else:
			self.writeI2C(1);
			if self._settings.get(['light_use_pwm']) == True:
				self.pwm.stop()
			else:
				GPIO.output(int(self._settings.get(['light_pin'])), 0)
			self.light_on = False
		
		#On each change of the light send that change to the plugin manager for it to update in the frontend
		self._plugin_manager.send_plugin_message(self._identifier, dict(light_status=self.get_light_status(), light_dc=self.pwm_dc))
		
	
	def gpio_cleanup(self):
		
		#if pwm is currently used, shut it down
		if self._settings.get(['light_use_pwm']) == True: 
			self.pwm.stop()
				
		#remove all events / threads from the pins where defined as switch / input ID defined true
		if self._settings.get_int(['re_switch_pin']) != -1: GPIO.remove_event_detect(int(self._settings.get(['re_switch_pin'])))
		if self._settings.get_int(['re_a_pin']) != -1: GPIO.remove_event_detect(int(self._settings.get(['re_a_pin'])))
		if self._settings.get_int(['re_c_pin']) != -1: GPIO.remove_event_detect(int(self._settings.get(['re_c_pin'])))
					
		#after that reset all currently used pins to their default state (input, nopullup)
		if self._settings.get_int(['light_pin']) != -1: GPIO.cleanup(self._settings.get_int(['light_pin']))
		
		if self._settings.get_int(['re_switch_pin']) != -1: GPIO.cleanup(self._settings.get_int(['re_switch_pin']))
		if self._settings.get_int(['re_a_pin']) != -1: GPIO.cleanup(self._settings.get_int(['re_a_pin']))
		if self._settings.get_int(['re_c_pin']) != -1: GPIO.cleanup(self._settings.get_int(['re_c_pin']))
		
		if self._settings.get_int(['re_g_led_pin']) != -1: GPIO.cleanup(self._settings.get_int(['re_g_led_pin']))
		if self._settings.get_int(['re_r_led_pin']) != -1: GPIO.cleanup(self._settings.get_int(['re_r_led_pin']))
		
		#should be clean now for a fresh start!

		
		#try:	
		#except Exception as e:
		#		msg = "Could not clean up GPIO's. Error: {name} ({msg}).".format(name=e.__class__.__name__, msg=e)
		#		self._logger.info(msg)
		#except Exception as e:
		#	self._logger.exception("Error when shutting down: {error}".format(error=e))
	
	def gpio_init(self):
		
		#read settings into dict / primarily for checking / testing.
		self.defined_pins = {"light_pin": self._settings.get_int(['light_pin']),
							"re_r_led_pin": self._settings.get_int(['re_r_led_pin']),
							"re_g_led_pin": self._settings.get_int(['re_g_led_pin']),
							"re_b_led_pin": self._settings.get_int(['re_b_led_pin']),
							"re_switch_pin": self._settings.get_int(['re_switch_pin']),
							"re_a_pin": self._settings.get_int(['re_a_pin']),
							"re_c_pin": self._settings.get_int(['re_c_pin'])
		}
				
		# SETUP the PWM for the Lights
		if self._settings.get_int(['light_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['light_pin'])), GPIO.OUT)
						
			if self._settings.get(['light_use_pwm']) == True: 
				self.pwm = GPIO.PWM(int(self._settings.get(['light_pin'])), int(self._settings.get(['light_freq']))); #Set Frequency of PWM, soft. 200 Hz should be nice
			
			if self._settings.get(['light_startup_on']) == True:   # If a start on on is defined true, start it
				self.set_light_on(True)
			else:
				self.set_light_on(False)
				
		#Rotary Encoder - OUTPUT (Red LED) and Turn ON
		if self._settings.get_int(['re_r_led_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['re_r_led_pin'])), GPIO.OUT)
			GPIO.output(int(self._settings.get(['re_r_led_pin'])), 0)
		
		#Rotary Encoder - OUTPUT (Green LED) and Turn OFF
		if self._settings.get_int(['re_g_led_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['re_g_led_pin'])), GPIO.OUT)
			GPIO.output(int(self._settings.get(['re_g_led_pin'])), 0)
			
		#Rotary Encoder - OUTPUT (Green LED) and Turn OFF
		if self._settings.get_int(['re_b_led_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['re_b_led_pin'])), GPIO.OUT)
			GPIO.output(int(self._settings.get(['re_b_led_pin'])), 0)

		#Rotary Encoder - Switch
		if self._settings.get_int(['re_switch_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['re_switch_pin'])), GPIO.IN, pull_up_down = GPIO.PUD_UP)
			GPIO.add_event_detect(int(self._settings.get(['re_switch_pin'])), GPIO.BOTH, callback=self.check_re_switch, bouncetime=100)
			
		#ROTARY ENCODER - INPUT switches / grey code gen
		if self._settings.get_int(['re_a_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['re_a_pin'])), GPIO.IN, pull_up_down = GPIO.PUD_UP)
			GPIO.add_event_detect(int(self._settings.get(['re_a_pin'])), GPIO.BOTH, callback=self.check_re_encoder, bouncetime=1)
		
		if self._settings.get_int(['re_c_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['re_c_pin'])), GPIO.IN, pull_up_down = GPIO.PUD_UP)
			GPIO.add_event_detect(int(self._settings.get(['re_c_pin'])), GPIO.BOTH, callback=self.check_re_encoder, bouncetime=1)
	
	def indicator_light(self, state):
		if self._settings.get_int(['re_r_led_pin']) != -1: GPIO.output(int(self._settings.get(['re_r_led_pin'])), state)
	
	def check_re_switch(self, channel):
		#function called by the event attached to the switch, called every time the switch is touched
				
		state = GPIO.input(channel)
		#print "State :"+str(state)+ " Last :"+str(self.switch_laststate)
		
		if state==self.switch_laststate:
			#print "bounce, same state 2" #bounce, same state twice!
			if state == 0: self.switch_laststate == 1
			if state == 1: self.switch_laststate == 0
			return
	
				
		if state == 0:
			#Register the time for longpressing
			self.start_press = time.time()
			
			#for now, hardcoded indicator light ON
			self.indicator_light(1)
			
		
		if state == 1:
			#handle press_end event 
			self.end_press = time.time()
			elapsed = self.end_press - self.start_press
			
			#for now, hardcoded indicator light OFF
			self.indicator_light(0)
		
			#shortpress / smaller x seconds (on up!)
			if elapsed<=self._settings.get_int(['shutdown_longpress_s']) :
				self.set_light_on(not self.get_light_status())
			else:
				#blink, to let them know, we recognised it!
				self.blink_switch_led(5)
				
				#Shutdown, if this is what you want
				if self._settings.get(['shutdown_longpress']) == True: 
					self.gpio_cleanup()
					self.shutdown_system()
			
		self.switch_laststate=state
	
	def check_re_encoder(self, channel):
		#function called by the event attached to the 2 rotary encoder switches, called every time the encoder moves
		if self._settings.get(['light_use_pwm']) == True: 
			delta = self.get_delta()
			if delta!=0:
				self.inc_pwm(delta)	
	
	def rotation_sequence(self):
		a_state = GPIO.input(int(self._settings.get(['re_a_pin'])))
		b_state = GPIO.input(int(self._settings.get(['re_c_pin'])))
		r_seq = (a_state ^ b_state) | b_state << 1
		return r_seq
	
	def get_delta(self):
		#calcualtes the difference of the rotation sequence / how fast and direction
		delta = 0
		r_seq = self.rotation_sequence()
		if r_seq != self.r_seq:
			delta = (r_seq - self.r_seq) % 4
			if delta==3:
				delta = -1
			elif delta==2:
				delta = int(math.copysign(delta, self.last_delta))  # same direction as previous, 2 steps
                
			self.last_delta = delta
			self.r_seq = r_seq

		return delta
	
	def inc_pwm(self, value):
		#change the duty cycle / brightness of the LEDs according to the value received from the encoder
		
		self.pwm_dc=self.pwm_dc+value

		if self.pwm_dc > 100: self.pwm_dc = 100
		if self.pwm_dc < 0: self.pwm_dc = 0

		self.pwm.ChangeDutyCycle(self.pwm_dc)


	#blink led of the switch as an indicator
	def blink_switch_led(self, times):
		#blinks hardcoded the red led for now
		if self._settings.get_int(['re_r_led_pin']) != -1: 
		
			for num in range(1, times):
				GPIO.output(int(self._settings.get(['re_r_led_pin'])), 0)
				time.sleep(0.2)
				GPIO.output(int(self._settings.get(['re_r_led_pin'])), 1)
				time.sleep(0.2)
	
		
	def shutdown_system(self):
		#shuts the system down according to the octoprints preffered command
		shutdown_command = self._settings.global_get(["server", "commands", "systemShutdownCommand"])
		self._logger.info("Shutting down system with command: {command}".format(command=shutdown_command))
		try:
			import sarge
			p = sarge.run(shutdown_command, async=True)
		except Exception as e:
			self._logger.exception("Error when shutting down: {error}".format(error=e))
			return
	
					
	# API Call handling----------------------------------------------------
	def get_api_commands(self):
		return dict(
			light=["on"],
			light_toggle=[],
			pin_test=["pin"]
		)

	def on_api_command(self, command, data):
		if command == "light":
			self.set_light_on(data["on"])
			return flask.jsonify(dict(
								success=True,
								light_status=self.get_light_status(),
								light_dc=self.pwm_dc
			))
		
		elif command == "light_toggle":
			self.set_light_on(not self.get_light_status())
			return flask.jsonify(dict(
								success=True,
								light_status=self.get_light_status(),
								light_dc=self.pwm_dc
			))		
		
		elif command == "pin_test":
			
			msg=""
			success=False
			
			#current Pin defined... already configured within the plugin!
			if (int(data["pin"]) != -1) and (int(data["pin"]) in self.defined_pins.values()):
				msg="Pin "+str(data["pin"])+" already configured: "+str(self.defined_pins.keys()[self.defined_pins.values().index(int(data["pin"]))]).upper()
				success=False
			else:
			
				if int(data["pin"]) != -1:   # If a pin is defined, else just ignore it
					try:
						usage=GPIO.gpio_function(int(data["pin"]))
						
						if usage == 1: #1 is the default state for input, we just assume that if it's NOT default, it's used by something else
							GPIO.setup(int(data["pin"]), GPIO.OUT)
							msg="Pin "+str(data["pin"])+" set to "+self.gpio_port_use[usage]
							success=True
							GPIO.cleanup(int(data["pin"]))
						else:
							success=False
							msg="WARNING: Pin "+str(data["pin"])+" used! Function: "+self.gpio_port_use[usage]

					except Exception as e:
						msg="ERROR: "+str(data["pin"])+": {error}".format(error=e)
						success=False
					
					
				else:
					msg="No Pin defined (-1). Nothing tested."
					success=False
			
		
			return flask.jsonify(dict(
								success=success,
								msg=msg
			))
		
		else:		
			return flask.make_response("Unknown command", 400)
			
	def on_api_get(self, request):
		return flask.jsonify(dict(
			light_status=self.get_light_status(),
			light_dc=self.pwm_dc
		))

	# Plugin Basics--------------------------------------------------------
	def on_after_startup(self):
		self.gpio_init()
			
	def on_shutdown(self):
		self.gpio_cleanup()
	
	def get_settings_defaults(self):
		return dict(
			light_button_html_on="<i class='icon-lightbulb'></i> Light is On",
			light_button_html_on_color="black",
			light_button_html_off="<i class='icon-lightbulb'></i> Light is Off",
			light_button_html_off_color="grey",
			light_pin=-1,
			light_use_pwm=True,
			light_dc=80,
			light_freq=200,
			light_startup_on=False,
			light_start_on_print=True,
			light_dc_print_start=100,
			light_stop_on_print=True,
			re_switch_pin=-1,
			re_a_pin=-1,
			re_c_pin=-1,
			re_r_led_pin=-1,
			re_g_led_pin=-1,
			re_b_led_pin=-1,
			gpio_use_board=False,
			shutdown_longpress=False,
			shutdown_longpress_s=3
			
		)
		#My settings
		#	light_pin=17,
		#	re_switch_pin=21,
		#	re_a_pin=13,
		#	re_c_pin=12,
		#	re_g_led_pin=-1,
		#	re_r_led_pin=19
	
	#settings changed, restart the whole thing
	def on_settings_save(self, data):
		
		#cleanup first
		self.gpio_cleanup()
		
		#save it really
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
		
		#re-init with the new settings
		self.gpio_init()

		
		
		
	def get_template_configs(self):
		return [
			dict(type="navbar", custom_bindings=True),
			dict(type="settings", custom_bindings=True)
		]
		
	def get_assets(self):
		return dict(
			js=["js/mylight.js"]
			#css=["css/mylight.css"]
			)
	
	def on_event(self, event, payload):
		if event == "PrintDone":
			if self._settings.get(['light_stop_on_print']) == True:
				self.set_light_on(False)
			else:
				return
		
		if event == "PrintStarted":
			if self._settings.get(['light_start_on_print']) == True:
				self.set_light_on(True)
			else:
				return
	
	def get_version(self):
		return self._plugin_version
	
	def get_update_information(self):
		return dict(
			mylight=dict(
				displayName="MyLight",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="MartinBienz",
				repo="OctoPrint-MyLight",
				current=self._plugin_version,

				# update method: pip
				pip="https://github.com/MartinBienz/OctoPrint-MyLight/archive/{target_version}.zip"
			)
	)

__plugin_name__ = "MyLight"
__plugin_version__= "0.0.4"


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = MyLightPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}