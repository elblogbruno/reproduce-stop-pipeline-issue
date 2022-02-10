void ConnectWiFi_STA(bool useStaticIP = false)
{
	Serial.println("");
	WiFi.mode(WIFI_STA);
	WiFi.begin(ssid, password);
	if(useStaticIP) WiFi.config(ip, gateway, subnet);
	while (WiFi.status() != WL_CONNECTED) 
	{ 
		delay(100);  
		Serial.print('.'); 
	}

	Serial.println("");
	Serial.print("Iniciado STA:\t");
	Serial.println(ssid);
	Serial.print("IP address:\t");
	Serial.println(WiFi.localIP());
}

void ConnectWiFi_AP(bool useStaticIP = false)
{ 
	Serial.println("");
	WiFi.mode(WIFI_AP);
	while(!WiFi.softAP(ssid, password))
	{
		Serial.println(".");
		delay(100);
	}
	if(useStaticIP) WiFi.softAPConfig(ip, gateway, subnet);

	Serial.println("");
	Serial.print("Iniciado AP:\t");
	Serial.println(ssid);
	Serial.print("IP address:\t");
	Serial.println(WiFi.softAPIP());
}

// void InitMDNS(const char *MyName)
// {	
//   if (MDNS.begin(MyName))
//   {
//     Serial.println(F("mDNS responder started"));
//     Serial.print(F("I am: "));
//     Serial.println(MyName);
 
//     // Add service to MDNS-SD
//     MDNS.addService("n8i-mlp", "tcp", 23);
//   }
//   else
//   {
//     while (1) 
//     {
//       Serial.println(F("Error setting up MDNS responder"));
//       delay(1000);
//     }
//   }
// }

void handle_received_byte(int received_byte){

	printf("%c", received_byte);

	// if you received the end of transmission byte
	if (received_byte == '\n')
	{
		// print the received line
		Serial.println("");
		Serial.println("Received: ");
		Serial.println(received_byte);
	}

	// if you received the end of transmission byte
	if (received_byte == '\r')
	{
		// print the received line
		Serial.println("");
		Serial.println("Received: ");
		Serial.println(received_byte);
	}

	// see if you receive an stop mjpeg transmission
	if (received_byte == 's')
	{
		// print the received line
		Serial.println("");
		Serial.println("Received: ");
		Serial.println(received_byte);
	}
}