$(function() {
    function MyLightViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];
        
		self.LightStatus = ko.observable(false);
		
		self.Light_nav_text = ko.observable("");
		self.Light_nav_text_color = ko.observable("");
									
        self.testActive = ko.observable(false);
        self.testResult = ko.observable(false);
        self.testSuccessful = ko.observable(false);
        self.testMessage = ko.observable();
		
		//Get and set the current Gradient / Backgroundcolor according to the current theme / color (more or less)
		self.CurrentGradient = function() {
			currentOctoprintTheme=self.settings.appearance.color();
			GradFrom="#eeeeee";
			
			if (currentOctoprintTheme == "default") {
				currentOctoprintTheme="#bbbbbb";
				GradFrom="white";
				}
			
			gradient="linear-gradient(to bottom,"+GradFrom+", "+currentOctoprintTheme+")";
			return gradient;
		}
		
		self.CurrentBGColor = function() {
			c=self.settings.appearance.color();
			return c;
		}
		
		//update the status / text based on the current settings
		self.create_status = function(status) {
			self.LightStatus(status);
						
			if (status) {
				self.Light_nav_text(self.settings.plugins.mylight.light_button_html_on());
				self.Light_nav_text_color(self.settings.plugins.mylight.light_button_html_on_color());				
			}
			else {
				self.Light_nav_text(self.settings.plugins.mylight.light_button_html_off());
				self.Light_nav_text_color(self.settings.plugins.mylight.light_button_html_off_color());		
			}
			
			
		}
		
		//function to toggle the light on click in the navbar
		self.toggle_light = function() {
		
			var payload_light_toggle = {
                command: "light_toggle"
            };

            $.ajax({
                url: API_BASEURL + "plugin/mylight",
                type: "POST",
                dataType: "json",
                data: JSON.stringify(payload_light_toggle),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    self.create_status(response.light_status);
                },
                complete: function() {
                    
                }
            });
        };
		
        self.testConfiguration = function() {
			self.testActive(true);
            self.testResult(false);
            self.testSuccessful(false);
            self.testMessage("");
			
			test_pin=self.settings.plugins.mylight.light_pin();
			
			var payload = {
			    command: "pin_test",
                pin: self.settings.plugins.mylight.light_pin()
			};
			
            $.ajax({
                url: API_BASEURL + "plugin/mylight",
                type: "POST",
                dataType: "json",
                data: JSON.stringify(payload),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    self.testResult(true);
                    self.testSuccessful(response.success);
                    self.testMessage(response.msg);
					//self.create_status(response.light_status);

                },
                complete: function() {
                    self.testActive(false);
                }
            });
        };

        self.fromResponse = function(response) {
           self.create_status(response.light_status);
        };

        self.requestData = function () {
            $.ajax({
                url: API_BASEURL + "plugin/mylight",
                type: "GET",
                dataType: "json",
                success: self.fromResponse
            });
        };

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
			self.requestData();
        };
		
		self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin != "mylight") {
                return;
            }
			self.create_status(data.light_status);
            
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([MyLightViewModel, ["loginStateViewModel", "settingsViewModel"], ["#navbar_plugin_mylight", "#settings_plugin_mylight"]]);
});