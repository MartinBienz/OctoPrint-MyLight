# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import RPi.GPIO as GPIO
import math
import time
import flask

class MyLightPlugin(octoprint.plugin.StartupPlugin,
							octoprint.plugin.ShutdownPlugin,
							octoprint.plugin.EventHandlerPlugin,
							octoprint.plugin.SimpleApiPlugin,
							octoprint.plugin.TemplatePlugin,
							octoprint.plugin.SettingsPlugin,
							octoprint.plugin.AssetPlugin):

	def initialize(self):
		self._logger.info("MyLight - Running RPi.GPIO version '{0}'...".format(GPIO.VERSION))
		if GPIO.VERSION < "0.6":
			raise Exception("MyLight - RPi.GPIO must be greater than 0.6")
			
		self.light_on = False
		self.re_switch_prev_input=0
		self.last_delta = 0
		self.r_seq = 0 #self.rotation_sequence()
		
		self.end_press=0
		self.start_press=0
		
		self.pwm_dc=self._settings.get_int(['light_dc'])
		
		#self._logger.info("MyLight Plugin GPIO [%s] initialized..."%self._identifier)
	
	def gpio_cleanup(self):
		
		if self._settings.get(['light_use_pwm']) == True: 
			try:
				self.pwm.stop()
			except Exception:
				pass

		try:
			GPIO.remove_event_detect(int(self._settings.get(['re_switch_pin'])))
			GPIO.remove_event_detect(int(self._settings.get(['re_a_pin'])))
			GPIO.remove_event_detect(int(self._settings.get(['re_c_pin'])))
		except Exception:
			pass
		
		GPIO.cleanup()
	
	def get_light_status(self):
		return self.light_on
	def set_light_on(self, to):
		
		if to == True:
			if self._settings.get(['light_use_pwm']) == True:
				self.pwm.start(int(self._settings.get(['light_dc']))) # Set the duty cycle
			else:
				GPIO.output(int(self._settings.get(['light_pin'])), 1)
			self.light_on = True
		else:
			if self._settings.get(['light_use_pwm']) == True:
				self.pwm.stop()
			else:
				GPIO.output(int(self._settings.get(['light_pin'])), 0)
			self.light_on = False
		#On each change of the light send that change to the plugin manager for it to update in the frontend
		self._plugin_manager.send_plugin_message(self._identifier, dict(light_status=self.get_light_status(), light_dc=self.pwm_dc))
		
	def gpio_init(self):
		
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		
		# SETUP the PWM for the Lights
		if self._settings.get_int(['light_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['light_pin'])), GPIO.OUT)
			#GPIO.output(self._settings.get(['light_pin']), 1) #This is just high or low, USING PWM instead
			
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

		#Rotary Encoder - Switch
		if self._settings.get_int(['re_switch_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['re_switch_pin'])), GPIO.IN, pull_up_down = GPIO.PUD_UP)
			GPIO.add_event_detect(int(self._settings.get(['re_switch_pin'])), GPIO.BOTH, callback=self.check_re_switch, bouncetime=50)
			
		#ROTARY ENCODER - INPUT
		if self._settings.get_int(['re_a_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['re_a_pin'])), GPIO.IN, pull_up_down = GPIO.PUD_UP)
			GPIO.add_event_detect(int(self._settings.get(['re_a_pin'])), GPIO.BOTH, callback=self.check_re_encoder, bouncetime=1)
		if self._settings.get_int(['re_c_pin']) != -1:   # If a pin is defined, else just ignore it
			GPIO.setup(int(self._settings.get(['re_c_pin'])), GPIO.IN, pull_up_down = GPIO.PUD_UP)
			GPIO.add_event_detect(int(self._settings.get(['re_c_pin'])), GPIO.BOTH, callback=self.check_re_encoder, bouncetime=1)
		
	def rotation_sequence(self):
		a_state = GPIO.input(int(self._settings.get(['re_a_pin'])))
		b_state = GPIO.input(int(self._settings.get(['re_c_pin'])))
		r_seq = (a_state ^ b_state) | b_state << 1
		return r_seq
	
	def get_delta(self):
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
		self.pwm_dc=self.pwm_dc+value

		if self.pwm_dc > 100: self.pwm_dc = 100
		if self.pwm_dc < 0: self.pwm_dc = 0

		self.pwm.ChangeDutyCycle(self.pwm_dc)
		
	
	def check_re_encoder(self, channel):
		
		if self._settings.get(['light_use_pwm']) == True: 
			delta = self.get_delta()
			if delta!=0:
				self.inc_pwm(delta)
	
	def blink_4x(self):
		GPIO.output(int(self._settings.get(['re_r_led_pin'])), 0)
		time.sleep(0.2)
		GPIO.output(int(self._settings.get(['re_r_led_pin'])), 1)
		time.sleep(0.2)
		GPIO.output(int(self._settings.get(['re_r_led_pin'])), 0)
		time.sleep(0.2)
		GPIO.output(int(self._settings.get(['re_r_led_pin'])), 1)
		time.sleep(0.2)
		GPIO.output(int(self._settings.get(['re_r_led_pin'])), 0)
	
		
	def shutdown_system(self):
		shutdown_command = self._settings.global_get(["server", "commands", "systemShutdownCommand"])
		self._logger.info("Shutting down system with command: {command}".format(command=shutdown_command))
		try:
			import sarge
			p = sarge.run(shutdown_command, async=True)
		except Exception as e:
			self._logger.exception("Error when shutting down: {error}".format(error=e))
			return
	
	def check_re_switch(self, channel):
	
		state = GPIO.input(int(self._settings.get(['re_switch_pin'])))
				
		if state == 0:
			GPIO.output(int(self._settings.get(['re_r_led_pin'])), 1)
			self.start_press = time.time()
		if state == 1:
			GPIO.output(int(self._settings.get(['re_r_led_pin'])), 0)
			self.end_press = time.time()
			elapsed = self.end_press - self.start_press
		
			#shortpress / smaller 3 seconds (on up!)
			if elapsed<=3:
				self.set_light_on(not self.get_light_status())
			else:
				#Shutdown
				self.blink_4x()
				self.shutdown_system()
				
	# API Call handling----------------------------------------------------
	def get_api_commands(self):
		return dict(
			light=["on"],
			light_toggle=[]
		)

	def on_api_command(self, command, data):
		if command == "light":
			self.set_light_on(data["on"])
			if "dc" in data:
				#could set pwm here... but will not implement it atm
				self._logger.info("ligth command called, parameter is {parameter}".format(**locals()))
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
			light_pin=17,
			light_use_pwm=True,
			light_dc=80,
			light_freq=200,
			light_startup_on=False,
			light_start_on_print=True,
			light_dc_print_start=100,
			light_stop_on_print=True,
			re_switch_pin=21,
			re_a_pin=13,
			re_c_pin=12,
			re_g_led_pin=-1,
			re_r_led_pin=19
		)
	
	#settings changed, restart the whole thing
	def on_settings_save(self, data):
		
		#save it really
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
		
		self.gpio_cleanup()
		self.gpio_init()

		
		
		
	def get_template_configs(self):
		return [
			dict(type="navbar", custom_bindings=True),
			dict(type="settings", custom_bindings=True)
		]
		
	def get_assets(self):
		return dict(
			js=["js/mylight.js"],
			css=["css/mylight.css"]
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
	
	def get_update_information(self):
		return dict(
			growl=dict(
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

def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = MyLightPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}