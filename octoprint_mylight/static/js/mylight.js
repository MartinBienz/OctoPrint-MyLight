$(function() {
    function MyLightViewModel(parameters) {
        var self = this;

        self.loginState = parameters[0];
        self.settingsViewModel = parameters[1];
        
		self.LightStatus = ko.observable(false);
		self.LightStatus_text = ko.observable("");
		
		self.Light_nav_text = ko.observable("");
						
        self.testActive = ko.observable(false);
        self.testResult = ko.observable(false);
        self.testSuccessful = ko.observable(false);
        self.testMessage = ko.observable();
		
		
		self.create_status = function(status) {
			self.LightStatus(status);
			if (status) {
				self.LightStatus_text("Light: ON");
				self.Light_nav_text("On");
			}
			else {
				self.LightStatus_text("Light: OFF");
				self.Light_nav_text("Off");
			}
		}
		
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

            //var host = self.settings.plugins.growl.hostname();
            //var port = self.settings.plugins.growl.port();
            //var pass = self.settings.plugins.growl.password();

            var payload_light_set_off = {
                command: "light",
                on: false
            };
			
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
                    self.testResult(true);
                    self.testSuccessful(response.success);
                    self.testMessage("Light ON:"+response.light_status);
					self.create_status(response.light_status);
					//if (!response.success && response.hasOwnProperty("msg")) {
                    //    self.testMessage(response.msg);
                    //} else {
                    //    self.testMessage("");
                    //}
                },
                complete: function() {
                    self.testActive(false);
                }
            });
        };

        self.fromResponse = function(response) {
            self.testMessage("Light ON:"+response.light_status);
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
			//alert(data.light_status);
			self.create_status(data.light_status);
            
        };

        self.onSettingsShown = function() {
            self.requestData();
        };

    }

    // view model class, parameters for constructor, container to bind to
    ADDITIONAL_VIEWMODELS.push([MyLightViewModel, ["loginStateViewModel", "settingsViewModel"], ["#navbar_plugin_mylight", "#settings_plugin_mylight"]]);
});