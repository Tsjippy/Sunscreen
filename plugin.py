# Sunscreen script
# Author: Tsjippy
#
"""
<plugin key="SunScreen" name="Sunscreen plugin" author="Tsjippy" version="1.0.0" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://wiki.domoticz.com/wiki/Real-time_solar_data_without_any_hardware_sensor_:_azimuth,_Altitude,_Lux_sensor...">
    <description>
        <h2>Sunscreen plugin</h2><br/>
        This plugin calculates the virtual amount of LUX on your current location<br/>
        It turns on a sunscreen device based on that, based on which you perform actions<br/>
        All credits go to the author of the original lus script (see link)<br/><br/>
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Calculates the current sun location and stores them in Domoticz devices</li>
            <li>Calculates the virtual LUX and stores it in a Domoticz device</li>
            <li>Calculates based on your settings if a sunscreen device needs to go open, needs to close, or half closed</li>
        </ul>
        <h3>Configuration</h3>
        Fill in how often the sunscreen device should change.<br/>
        Fill in your thresholds in this order: Azimut low;Azimut high; Altitude low; Altitude mid; Altidtude high;Lux low; Lux high;Temp low; Temp high;Wind;Gust;Rain<br/>
        Fill in your weatherdevice names in this order: Temperature device;Wind device;Rain device;Pressure device<br/>
    </description>
    <params>
        <param field="Mode2" label="Switchtime threshold (minutes)" width="400px" required="true" default="30"/>
        <param field="Mode3" label="Thresholds" width="500px" required="true" default=""/>
        <param field="Mode4" label="Wheater devices" width="500px" required="true" default="Temp;Wind;Rain;Pressure"/>
        <param field="Mode5" label="Domoticz url and port" width="200px" required="true" default="http://127.0.0.1:8080"/>
    </params>
</plugin>
"""

import Domoticz
import sys
#sudo pip3 install requests -t /home/pi/domoticz/plugins/Sunscreen
import requests
import datetime
import math
import calendar
from urllib.request import urlopen
#sudo pip3 install lxml -t /home/pi/domoticz/plugins/Sunscreen
#sudo pip3 install pandas -t /home/pi/domoticz/plugins/Sunscreen
#sudo apt-get install libatlas-base-dev
import pandas

class BasePlugin:
    enabled = False
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        self.Error=False
        self.ArbitraryTwilightLux=6.32     # W/m² egal 800 Lux     (the theoritical value is 4.74 but I have more accurate result with 6.32...)
        self.ConstantSolarRadiation = 1361 # Solar Constant W/m²
        self.Year=datetime.datetime.now().year
        self.Yearday=datetime.datetime.now().timetuple().tm_yday
        if calendar.isleap(self.Year):
            self.DaysInYear=366
        else:
            self.DaysInYear=365
        self.AgularSpeed = 360/365.25
        self.Declinaison = math.degrees(math.asin(0.3978 * math.sin(math.radians(self.AgularSpeed) *(self.Yearday - (81 - 2 * math.sin((math.radians(self.AgularSpeed) * (self.Yearday - 2))))))))
        
        #Domoticz.Trace(True)
        createDevices()

        try:
            if not "Location" in Settings:
                self.Error="Location not set in Settings, please update your settings."
                Domoticz.Error(self.Error)
            else:
                Domoticz.Heartbeat(30)
                loc = Settings["Location"].split(";")
                self.Latitude=float(loc[0])
                self.Longitude=float(loc[1])
                Domoticz.Log("Current location is "+str(self.Latitude)+","+str(self.Latitude))

                self.switchtime=int(Parameters["Mode2"])
                self.Thresholds={}
                thresholds=Parameters["Mode3"].split(";")
                devices=Parameters["Mode4"].split(";")
                self.url=Parameters["Mode5"]
                self.Altitude=Altitude()
                Domoticz.Log("Found altitude of "+str(self.Altitude)+" meter")

                self.Thresholds["azimuth"]=[thresholds[0],thresholds[1]]
                self.Thresholds["alltitude"]=[thresholds[2],thresholds[3],thresholds[4]]
                self.Thresholds["lux"]=[thresholds[5],thresholds[6]]
                self.Thresholds["temp"]=[thresholds[7],thresholds[8]]
                self.Thresholds["wind"]=thresholds[9]
                self.Thresholds["gust"]=thresholds[10]
                self.Thresholds["rain"]=thresholds[11]

                Domoticz.Log("Will only perform an action every "+str(self.switchtime)+" minutes.")
                Domoticz.Log("Will only close the sunscreen if the azimuth is between "+self.Thresholds["azimuth"][0]+" and "+self.Thresholds["azimuth"][1]+" degrees, the altitude is between "+self.Thresholds["alltitude"][0]+" and "+self.Thresholds["alltitude"][2]+" degrees, the temperature is above "+self.Thresholds["temp"][1]+" degrees and the amount of lux is between "+self.Thresholds["lux"][0]+" and "+self.Thresholds["lux"][1]+" lux")
                Domoticz.Log("Will open the sunscreen if it is raining, the temprerture drops below "+self.Thresholds["temp"][0]+", the wind is more than "+self.Thresholds["wind"]+" or the gust are more than "+self.Thresholds["gust"]+"")

                if len(devices)==4:
                    self.TemperatureDevice=devices[0]
                    self.WindDevice=devices[1]
                    self.RainDevice=devices[2]
                    self.PressureDevice=devices[3]
                else:
                    self.Error="You should specify a temperature, wind, rain and pressure device, but you only defined "+str(len(devices))+" devices. Please update the hardware settings of this plugin."
                    Domoticz.Error(self.Error)

                if self.Error==False:
                    AllDevices = requests.get(url=self.url+"/json.htm?type=devices&used=true").json()['result']
                    for device in AllDevices:
                        if device["Name"]==self.TemperatureDevice:
                            self.TemperatureIDX=device["idx"]
                            self.Temperature=device["Temp"] 
                            Domoticz.Log("Found temperature device '"+self.TemperatureDevice+ "' Current temperature: "+str(self.Temperature))
                        if device["Name"]==self.WindDevice:
                            self.WindIDX=device["idx"]
                            self.Wind=device["Data"].split(";")[2]
                            self.Gust=device["Data"].split(";")[3]
                            Domoticz.Log("Found wind device '"+self.WindDevice+"' current wind: "+str(self.Wind)+". Current wind gust: " +str(self.Gust))
                        if device["Name"]==self.RainDevice:
                            self.RainIDX=device["idx"]
                            self.Rain=device["Data"]
                            Domoticz.Log("Found rain device '"+self.RainDevice+"' current expected rain: "+str(self.Rain))
                        if device["Name"]==self.PressureDevice:
                            self.PressureIDX=device["idx"]
                            self.Pressure=device["Barometer"]
                            Domoticz.Log("Found pressure device '"+self.PressureDevice+"' current pressure: "+str(self.Pressure))

                    try:
                        self.TemperatureIDX
                        self.WindIDX
                        self.RainIDX
                        self.PressureIDX
                    except AttributeError as Error:
                        device=str(Error).split("'")[3].replace("IDX","")
                        self.Error="Could not find "+getattr(self, device+"Device",device)+" device, please make sure it exists."
                        Domoticz.Error(self.Error)

                if self.Error==False:
                    self.Station = ""
                    self.Station=FindStation()
                    Domoticz.Log("Station is "+self.Station)
        except Exception as e:
            senderror(e)

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: " + Name + "," + Subject + "," + Text + "," + Status + "," + str(Priority) + "," + Sound + "," + ImageFile)

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        if self.Error==False:
            try:
                self.Temperature=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.TemperatureIDX).json()['result'][0]["Temp"]
                Wind=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.WindIDX).json()['result'][0]["Data"].split(";")
                self.Wind=Wind[2]
                self.Gust=Wind[3]
                self.Rain=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.RainIDX).json()['result'][0]["Data"]
                self.Pressure=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.PressureIDX).json()['result'][0]["Barometer"]

                SunLocation()

                Cloudlayer()
                Domoticz.Log("Current cloudlayer is "+str(self.Octa))

                VirtualLux()
            except Exception as e:
                senderror(e)
        else:
            Domoticz.Error(self.Error)


global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def senderror(e):
    Domoticz.Error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+" Error is "+str(e))
    return

def SunLocation():
        global _plugin
        #altitude of the Sun 
        timeDecimal = (datetime.datetime.utcnow().hour + datetime.datetime.utcnow().minute / 60)
        solarHour = timeDecimal + (4 * _plugin.Longitude / 60 )
        hourlyAngle = 15 * ( 12 - solarHour )          
        _plugin.sunAltitude = math.degrees(math.asin(math.sin(math.radians(_plugin.Latitude))* math.sin(math.radians(_plugin.Declinaison)) + math.cos(math.radians(_plugin.Latitude)) * math.cos(math.radians(_plugin.Declinaison)) * math.cos(math.radians(hourlyAngle))))
        UpdateDevice(2, int(round(_plugin.sunAltitude)), int(round(_plugin.sunAltitude)))
        
        #azimut of the Sun
        azimuth = math.acos((math.sin(math.radians(_plugin.Declinaison)) - math.sin(math.radians(_plugin.Latitude)) * math.sin(math.radians(_plugin.sunAltitude))) / (math.cos(math.radians(_plugin.Latitude)) * math.cos(math.radians(_plugin.sunAltitude) ))) * 180 / math.pi 
        sinAzimuth = (math.cos(math.radians(_plugin.Declinaison)) * math.sin(math.radians(hourlyAngle))) / math.cos(math.radians(_plugin.sunAltitude))
        if(sinAzimuth<0):
            azimuth=360-azimuth 
        UpdateDevice(1,int(round(azimuth)),int(round(azimuth)))

def Cloudlayer():
    global _plugin
    try:
        UTC=datetime.datetime.utcnow()
        if len(str(UTC.hour-1))==1:
            hour="0"+str(UTC.hour-1)
        else:
            hour=str(UTC.hour-1)
        UTC=str(UTC.year)+str(UTC.month)+str(UTC.day)+hour+"00"

        url="http://www.ogimet.com/cgi-bin/getsynop?block="+_plugin.Station+"&begin="+UTC
        #Domoticz.Log("Cloudlayer url is "+url)
        result=urlopen(url).read().decode('utf-8').split(" "+_plugin.Station+" ")[1].split(" ")[0][0]
        _plugin.Octa=int(result)
    except Exception as e:
        senderror(e)

def VirtualLux():
        global _plugin
        RadiationAtm = _plugin.ConstantSolarRadiation * (1 +0.034 * math.cos( math.radians( 360 * _plugin.Yearday / _plugin.DaysInYear )))   
        absolutePressure = _plugin.Pressure - round((_plugin.Altitude/ 8.3),1) # hPa
        sinusSunAltitude = math.sin(math.radians(_plugin.sunAltitude))
        M0 = math.sqrt(1229 + math.pow(614 * sinusSunAltitude,2)) - 614 * sinusSunAltitude
        M = M0 * _plugin.Pressure/absolutePressure
        
        Kc=1-0.75*math.pow(_plugin.Octa/8,3.4)  # Factor of mitigation for the cloud layer
        if _plugin.sunAltitude > 1: # Below 1° of Altitude , the formulae reach their limit of precision.
            directRadiation = RadiationAtm * math.pow(0.6,M) * sinusSunAltitude
            scatteredRadiation = RadiationAtm * (0.271 - 0.294 * math.pow(0.6,M)) * sinusSunAltitude
            totalRadiation = scatteredRadiation + directRadiation
            Lux = totalRadiation / 0.0079  # Radiation in Lux. 1 Lux = 0,0079 W/m²
            weightedLux = Lux * Kc   # radiation of the Sun with the cloud layer
        elif _plugin.sunAltitude <= 1 and _plugin.sunAltitude >= -7: #apply theoretical Lux of twilight
            directRadiation = 0
            scatteredRadiation = 0
            arbitraryTwilightLux=arbitraryTwilightLux-(1-_plugin.sunAltitude)/8*arbitraryTwilightLux
            totalRadiation = scatteredRadiation + directRadiation + arbitraryTwilightLux 
            Lux = totalRadiation / 0.0079 # Radiation in Lux. 1 Lux = 0,0079 W/m²
            weightedLux = Lux * Kc   #radiation of the Sun with the cloud layer
        elif _plugin.sunAltitude < -7:  # no management of nautical and astronomical twilight...
            directRadiation = 0
            scatteredRadiation = 0
            totalRadiation = 0
            Lux = 0
            weightedLux = 0  #  should be around 3,2 Lux for the nautic twilight. Nevertheless.
        
        UpdateDevice(3,int(round(weightedLux)),int(round(weightedLux)))
        Domoticz.Log("Virtual LUX is "+str(round(weightedLux)))

def FindStation():
    global _plugin
    try:
        #Find Country
        url="https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat="+str(_plugin.Latitude)+"&lon="+str(_plugin.Longitude)+"&accept-language=en-US"
        #Domoticz.Log("Location url is "+url)
        country=requests.get(url).json()["address"]["country"]
        Domoticz.Log("Country is "+country)

        #Find Ogimet station
        url="http://www.ogimet.com/display_stations.php?lang=en&tipo=AND&isyn=&oaci=&nombre=&estado="+country+"&Send=Send"
        #Domoticz.Log("url is "+url)
        #Parse the table
        html = requests.get(url).content
        df_list = pandas.read_html(html)

        mindist=1000
        for i, Latitude in enumerate(df_list[1][4]):
            if "51-" in Latitude:
                lat=str(Latitude.replace("N","").replace("-","."))[:5]
                lon = str(df_list[1][5][i].replace("E","").replace("-","."))[:5]
                dist = haversine(_plugin.Latitude, _plugin.Longitude, float(lat), float(lon))
                if dist<mindist:
                    mindist=dist
                    station=df_list[1][0][i]
        Domoticz.Log("Found station "+station+" on "+str(round(mindist,1))+"km of your location.")
        return station
    except Exception as e:
        senderror(e)
        return "12840"

#
# Calculate the great circle distance between two points
# on the earth (specified in decimal degrees)
#

def haversine(lat1, lon1, lat2, lon2):

    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [ lat1, lon1, lat2, lon2 ])

    # Haversine formula
    dlat = math.fabs(lat2 - lat1)
    dlon = math.fabs(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    km = c * 6367
    return km    

def Altitude():
    global _plugin
    try:
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        data = '{"locations":[{"latitude":'+str(_plugin.Latitude)+',"longitude":'+str(_plugin.Longitude)+'}]}'
        response = requests.post('https://api.open-elevation.com/api/v1/lookup', headers=headers, data=data).json()
        Altitude=int(response["results"][0]['elevation'])
        return Altitude
    except Exception as e:
        senderror(e)
        return 0

def createDevices():
    global _plugin
    #Check if variable needs to be created
    try:
        if 1 not in Devices:
            Domoticz.Log("Created 'Azimut' device")
            Domoticz.Device(Name="Azimut", Unit=1, TypeName="Custom", Used=1).Create()
            UpdateImage(1, 'ChromecastLogo')

        if 2 not in Devices:
            Domoticz.Log("Created 'Altitude' device")
            Domoticz.Device(Name="Altitude", Unit=2, TypeName="Custom", Used=1).Create()
            UpdateImage(2, 'ChromecastLogo')

        if 3 not in Devices:
            Domoticz.Log("Created 'Virtual Lux'")
            Domoticz.Device(Name="Virtual Lux", Unit=3, Type=246, Subtype=1, Used=1).Create()
            UpdateImage(3, 'ChromecastLogo')

        if 4 not in Devices:
            Domoticz.Log("Created 'Sunscreen' device")
            Domoticz.Device(Name="Sunscreen", Unit=4, TypeName="Switch", Switchtype=13, Used=1).Create()
            UpdateImage(4, 'ChromecastLogo')

    except Exception as e:
        senderror(e)

    Domoticz.Log("Devices check done")
    return

# Synchronise images to match parameter in hardware page
def UpdateImage(Unit, Logo):
    if Unit in Devices and Logo in Images:
        if Devices[Unit].Image != Images[Logo].ID:
            Domoticz.Log("Device Image update: 'Chromecast', Currently " + str(Devices[Unit].Image) + ", should be " + str(Images[Logo].ID))
            Devices[Unit].Update(nValue=Devices[Unit].nValue, sValue=str(Devices[Unit].sValue), Image=Images[Logo].ID)
    return

# Update Device into database
def UpdateDevice(Unit, nValue, sValue, AlwaysUpdate=False):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if Unit in Devices:
        if Devices[Unit].nValue != nValue or Devices[Unit].sValue != sValue or AlwaysUpdate == True:
            Devices[Unit].Update(nValue, str(sValue))
            Domoticz.Log("Update " + Devices[Unit].Name + ": " + str(nValue) + " - '" + str(sValue) + "'")
    return