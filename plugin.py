# Sunscreen script
# Author: Tsjippy
#
"""
<plugin key="SunScreen" name="Sunscreen plugin" author="Tsjippy" version="1.3.0" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://wiki.domoticz.com/wiki/Real-time_solar_data_without_any_hardware_sensor_:_azimuth,_Altitude,_Lux_sensor...">
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
        Fill in your sun thresholds in this order: Azimut low;Azimut high; Altitude low; Altitude mid; Altidtude high<br/>
        If you need more sunscreens, just add 5 extra sun thresholds like this:<br/>
        Azimut1 low;Azimut1 high; Altitude1 low; Altitude1 mid; Altidtude1 high;Azimut2 low;Azimut2 high; Altitude2 low; Altitude2 mid; Altidtude2 high<br/>
        Fill in your weather thresholds in this order: Lux low; Lux high;Temp low (°C); Temp high (°C);Wind (m/s);Gust(m/s);Rain(mm)<br/>
        Fill in your weatherdevice names in this order: Pressure device;Temperature device;Wind device;Rain device<br/>
    </description>
    <params>
        <param field="Mode1" label="Switchtime threshold (minutes)" width="200px" required="true" default="30"/>
        <param field="Mode2" label="Sun thresholds" width="1000px" default="Azimut low;Azimut high; Altitude low; Altitude mid; Altidtude high"/>
        <param field="Mode3" label="Weather thresholds" width="1000px" default=""/>
        <param field="Mode4" label="Wheater devices" width="1000px" required="true" default="Pressure;Temp;Wind;Rain"/>
        <param field="Mode5" label="Domoticz url and port" width="200px" required="true" default="http://127.0.0.1:8080"/>
        <param field="Mode6" label="Debug" width="100px">
            <options>
                <option label="True" value="True" />
                <option label="False" value="False" default="True"/>
            </options>
        </param>
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
from multiprocessing import Process, Queue
import time

class Sunscreen:
    global _plugin
    def __init__(self,DeviceID,AzimutThresholds,AltitudeThresholds):
        self.DeviceID=DeviceID
        self.AzimutThresholds=AzimutThresholds
        self.AltitudeThresholds=AltitudeThresholds

    def CheckClose(self):
        try:
            # If screen is down, check if it needs to go up due to the wheater
            if Devices[self.DeviceID].sValue!="Off":
                if _plugin.Wind > _plugin.Thresholds["wind"] or _plugin.Gust > _plugin.Thresholds["gust"]:
                    Domoticz.Status("Opening '"+Devices[self.DeviceID].Name+"' because of the wind. ("+str(_plugin.Wind)+" m/s).")
                    ShouldOpen = True
                elif _plugin.Rain > _plugin.Thresholds["rain"]:
                    Domoticz.Status("Opening '"+Devices[self.DeviceID].Name+"' because of the rain.("+str(_plugin.Rain)+" mm).")
                    ShouldOpen = True
                elif _plugin.weightedLux < _plugin.Thresholds["lux"][0]:
                    Domoticz.Status("Opening '"+Devices[self.DeviceID].Name+"' because of the light intensity. ("+str(round(_plugin.weightedLux))+" lux).")
                    ShouldOpen = True

                if ShouldOpen == True:
                    UpdateDevice(self.DeviceID, 0, "Off")
                else:
                    self.CheckOpen()
        except Exception as e:
            senderror(e)

    def CheckOpen(self):
        try:
            fmt = '%Y-%m-%d %H:%M:%S'
            d1 = datetime.datetime.strptime(Devices[self.DeviceID].LastUpdate, fmt)
            d2 = datetime.datetime.strptime(str(datetime.datetime.now().replace(second=0, microsecond=0)), fmt)
            LastChanged=int(round((d2-d1).seconds/60))
            
            #Only change when last change was more than x minutes ago
            if LastChanged > _plugin.switchtime:
                #Only close sunscreen if the sun is in a specific region
                if _plugin.Azimuth > self.AzimutThresholds[0] and _plugin.Azimuth < self.AzimutThresholds[1] and _plugin.sunAltitude > self.AltitudeThresholds[0] and _plugin.sunAltitude < self.AltitudeThresholds[2]:
                    Domoticz.Log("Sun is in region")
                    #Only close if weather is ok
                    if _plugin.Wind <= _plugin.Thresholds["wind"]:
                        if _plugin.Gust <= _plugin.Thresholds["gust"]:
                            if _plugin.Rain <= _plugin.Thresholds["rain"]:
                                if _plugin.weightedLux > _plugin.Thresholds["lux"][1] or _plugin.Temperature > _plugin.Thresholds["temp"][1]:
                                    #--------------------   Close sunscreen   -------------------- 
                                    if _plugin.sunAltitude > self.AltitudeThresholds[1] and Devices[self.DeviceID].sValue != 50:
                                        Domoticz.Log ("Half closing '"+Devices[self.DeviceID].Name+"'.")
                                        UpdateDevice(self.DeviceID, 50, "50")
                                        #self.LastUpdateTime=datetime.datetime.now().replace(second=0, microsecond=0)
                                    elif (Devices[self.DeviceID].sValue == "Off") and _plugin.sunAltitude < self.AltitudeThresholds[1]:
                                        Domoticz.Log ("Full closing '"+Devices[self.DeviceID].Name+"'.")
                                        UpdateDevice(self.DeviceID, 100, "On")
                                        #self.LastUpdateTime=datetime.datetime.now().replace(second=0, microsecond=0)
                                    else:
                                        Domoticz.Log("'"+Devices[self.DeviceID].Name+"' is already down.")
                                else:
                                    Domoticz.Log("Not closing '"+Devices[self.DeviceID].Name+"' because of the amount of LUX.")
                            else:
                                Domoticz.Log("Not closing '"+Devices[self.DeviceID].Name+"' because of the rain.")
                        else:
                            Domoticz.Log("Not closing '"+Devices[self.DeviceID].Name+"' because of the windgusts.")
                    else:
                        Domoticz.Log("Not closing '"+Devices[self.DeviceID].Name+"' because of the windspeed.")
                #Sun is not in the region
                elif Devices[self.DeviceID].sValue!="Off":
                    Domoticz.Log("Opening '"+Devices[self.DeviceID].Name+"', as it is no longer needed.")
                else:
                    Domoticz.Log("No need to close the '"+Devices[self.DeviceID].Name+"'.")
            else:
                Domoticz.Log("Last change was less than "+_plugin.switchtime+" minutes ago, no action will be performed.")
        except Exception as e:
            senderror(e)

class BasePlugin:
    enabled = False
    def __init__(self):
        self.Error                      = False
        self.ArbitraryTwilightLux       = 6.32     # W/m² egal 800 Lux     (the theoritical value is 4.74 but I have more accurate result with 6.32...)
        self.ConstantSolarRadiation     = 1361 # Solar Constant W/m²
        self.Year                       = datetime.datetime.now().year
        self.Yearday                    = datetime.datetime.now().timetuple().tm_yday
        if calendar.isleap(self.Year):
            self.DaysInYear             = 366
        else:
            self.DaysInYear             = 365
        self.AgularSpeed                = 360/365.25
        self.Declinaison                = math.degrees(math.asin(0.3978 * math.sin(math.radians(self.AgularSpeed) *(self.Yearday - (81 - 2 * math.sin((math.radians(self.AgularSpeed) * (self.Yearday - 2))))))))
        self.JustSun                    = False
        self.Station                    = ""
        self.Altitude                   = ""
        self.Octa                       = ""
        self.HeartbeatCount             = -1
        self.Sunscreens                 = []
        self.weightedLux                = 0
        if Parameters["Mode6"]=="True":
            self.Debug                  = True
        else:
            self.Debug                  = False
        return

    def onStart(self):
        Domoticz.Heartbeat(30)
        #Domoticz.Trace(True)
        try:
            if not "Location" in Settings:
                self.Error="Location not set in Settings, please update your settings."
                Domoticz.Error(self.Error)
            else:
                loc = Settings["Location"].split(";")
                self.Latitude=float(loc[0])
                self.Longitude=float(loc[1])
                Domoticz.Log("Current location is "+str(self.Latitude)+","+str(self.Longitude))
                self.q1 = Queue()
                self.p1 = Process(target=self.FindStation, args=(self.q1,))
                self.p1.deamon=True
                self.p1.start()
                Domoticz.Log("Started search for Ogimet station.")

                self.q2 = Queue()
                self.p2 = Process(target=Altitude, args=(self.q2,))
                self.p2.deamon=True
                self.p2.start()
                Domoticz.Log("Started search for Altitude.")

                self.switchtime=int(Parameters["Mode1"])
                self.Thresholds={}
                SunThresholds=Parameters["Mode2"].split(";")
                WeatherThresholds=Parameters["Mode3"].split(";")
                self.WeatherDevices=Parameters["Mode4"].split(";")
                self.url=Parameters["Mode5"]

                if SunThresholds==[""]:
                    self.JustSun=True
                    Domoticz.Status("No sun thresholds are given, so no sunscreen device will be created.")
                else:
                    self.NumberOfSunscreens=len(SunThresholds)/5
                    if self.NumberOfSunscreens.is_integer()==True:
                        self.NumberOfSunscreens=int(self.NumberOfSunscreens)
                        for i in range(self.NumberOfSunscreens):
                            self.Thresholds["azimuth"+str(i)]=[SunThresholds[i],SunThresholds[i+1]]
                            self.Thresholds["alltitude"+str(i)]=[SunThresholds[i+2],SunThresholds[i+3],SunThresholds[i+4]]
                    else:
                        self.JustSun=True
                        Domoticz.Error("You specified "+str(len(SunThresholds))+" sun thresholds, you should specify 5 or a multitude of 5. No sunscreen device will be created, until you update the hardware.")

                if WeatherThresholds!=[""] and self.JustSun==False:
                    if len(WeatherThresholds) == 7:
                        self.Thresholds["lux"]=[int(WeatherThresholds[0]),int(WeatherThresholds[1])]
                        self.Thresholds["temp"]=[int(WeatherThresholds[2]),int(WeatherThresholds[3])]
                        self.Thresholds["wind"]=int(WeatherThresholds[4])
                        self.Thresholds["gust"]=int(WeatherThresholds[5])
                        self.Thresholds["rain"]=int(WeatherThresholds[6])
                    else:
                        self.JustSun=True
                        Domoticz.Error("You specified "+str(len(WeatherThresholds))+" thresholds, you should specify 7. No sunscreen device will be created, until you update the hardware.")
                elif WeatherThresholds==[""] and self.JustSun==False:
                    self.JustSun=True
                    Domoticz.Status("No weather thresholds are given, so no sunscreen device will be created.")     

                if self.JustSun==False:
                    Domoticz.Log("Will only perform an action every "+str(self.switchtime)+" minutes.")
                    for i in range(self.NumberOfSunscreens):
                        Domoticz.Log("Will only close sunscreen"+str(i)+" if the azimuth is between "+str(self.Thresholds["azimuth"+str(i)][0])+" and "+str(self.Thresholds["azimuth"+str(i)][1])+" degrees, the altitude is between "+str(self.Thresholds["alltitude"+str(i)][0])+" and "+str(self.Thresholds["alltitude"+str(i)][2])+" degrees, the temperature is above "+str(self.Thresholds["temp"][1])+" degrees and the amount of lux is between "+str(self.Thresholds["lux"][0])+" and "+str(self.Thresholds["lux"][1])+" lux")
                    Domoticz.Log("Will open a sunscreen if it is raining, the temperature drops below "+str(self.Thresholds["temp"][0])+" °C, the wind is more than "+str(self.Thresholds["wind"])+" m/s or the gust are more than "+str(self.Thresholds["gust"])+" m/s")

                self.CheckWeatherDevices()

                createDevices()
        except Exception as e:
            self.Error="Something went wrong during boot. Please chack the logs."
            senderror(e)

    def onStop(self):
        Domoticz.Log("onStop called")

        try:
            self.p1.terminate()
            self.p2.terminate()
        except Exception as e:
            senderror(e)

        Domoticz.Log("Terminated running processes")

    def onCommand(self, Unit, Command, Level, Hue):
        try:
            #Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
            if str(Command)=='Set Level':
                UpdateDevice(Unit, 2, Level)
            else:
                if Command == "Off":
                    UpdateDevice(Unit, 0, str(Command))
                else:
                    UpdateDevice(Unit, 1, str(Command))
        except Exception as e:
            senderror(e)

    def onHeartbeat(self):
        try:
            if self.Error==False:
                if self.p1.exitcode == None or self.Station=="":
                    if self.q1.empty()==True:
                        Domoticz.Log("Parsing Ogimet station table data.")
                    while self.q1.empty()==False:
                        result=str(self.q1.get())
                        if "Error" in result:
                            Domoticz.Error(result)
                            self.Error="Could not find Ogimet station."
                        elif "Found station " in result:
                            Domoticz.Log(result)
                            self.Station=result.split(":")[1].split(" ")[0]
                        else:
                            Domoticz.Log(result)
                if self.p2.exitcode != None and self.Altitude=="":
                    result=self.q2.get()
                    if "Error" in str(result):
                        Domoticz.Error(result)
                        self.Altitude=1
                        Domoticz.Log("Could not find altitude, using default of 1 meter.")
                    else:
                        self.Altitude=int(result)
                        Domoticz.Log("Altitude is "+str(self.Altitude)+" meter.")
                elif self.Station!="" and self.Altitude!="":
                    self.Pressure=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.PressureIDX).json()['result'][0]["Barometer"]

                    SunLocation()

                    Cloudlayer()
                    if self.Debug==True:
                        Domoticz.Log("Current cloudlayer is "+str(self.Octa))

                    VirtualLux()

                    if self.JustSun==False and Devices[4].sValue=="Off":
                        self.Temperature=float(requests.get(url=self.url+"/json.htm?type=devices&rid="+self.TemperatureIDX).json()['result'][0]["Temp"])
                        Wind=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.WindIDX).json()['result'][0]["Data"].split(";")
                        self.Wind=float(Wind[2])/10
                        self.Gust=float(Wind[3])/10
                        self.Rain=float(requests.get(url=self.url+"/json.htm?type=devices&rid="+self.RainIDX).json()['result'][0]["Data"])

                        for screen in self.Sunscreens:
                            screen.CheckClose()
                    elif Devices[4].sValue=="On" and self.Debug==True:
                        Domoticz.Status("Not performing sunscreen actions as the override button is on.")
            else:
                Domoticz.Error(self.Error)
        except Exception as e:
            senderror(e)

    def CheckWeatherDevices(self):
        try:
            if self.Debug==True:
                Domoticz.Log("Checking weather devices.")

            if len(self.WeatherDevices)==1:
                self.PressureDevice=self.WeatherDevices[0]
                self.TemperatureDevice=""
                self.WindDevice=""
                self.RainDevice=""
                if self.JustSun==False:
                    self.JustSun=True
                    Domoticz.Status("Just found one weatherdevice, so no sunscreen device will be created.")
            elif len(self.WeatherDevices)==4:
                self.PressureDevice=self.WeatherDevices[0]
                self.TemperatureDevice=self.WeatherDevices[1]
                self.WindDevice=self.WeatherDevices[2]
                self.RainDevice=self.WeatherDevices[3]
            else:
                self.Error="You should specify at least a pressure device, and optional a temperature, wind and rain device, but you defined "+str(len(devices))+" devices. Please update the hardware settings of this plugin."
                Domoticz.Error(self.Error)

            if self.Error==False:
                try:
                    AllDevices = requests.get(url=self.url+"/json.htm?type=devices&used=true").json()['result']
                except Exception as e:
                    Domoticz.Error("Could not get all devces with url: "+self.url+"/json.htm?type=devices&used=true")
                    senderror(e)

                for device in AllDevices:
                    if device["Name"]==self.TemperatureDevice:
                        self.TemperatureIDX=device["idx"]
                        self.Temperature=float(device["Temp"])
                        Domoticz.Log("Found temperature device '"+str(self.TemperatureDevice)+ "' Current temperature: "+str(self.Temperature)+" °C.")
                    if device["Name"]==self.WindDevice:
                        self.WindIDX=device["idx"]
                        self.Wind=int(device["Data"].split(";")[2])/10
                        self.Gust=int(device["Data"].split(";")[3])/10
                        Domoticz.Log("Found wind device '"+str(self.WindDevice)+"' current wind: "+str(self.Wind)+" m/s. Current wind gust: " +str(self.Gust)+" m/s.")
                    if device["Name"]==self.RainDevice:
                        self.RainIDX=device["idx"]
                        self.Rain=int(device["Data"])
                        Domoticz.Log("Found rain device '"+str(self.RainDevice)+"' current expected rain: "+str(self.Rain)+" mm.")
                    if device["Name"]==self.PressureDevice:
                        self.PressureIDX=device["idx"]
                        self.Pressure=float(device["Barometer"])
                        Domoticz.Log("Found pressure device '"+str(self.PressureDevice)+"' current pressure: "+str(self.Pressure)+" hPa.")
                try:
                    self.PressureIDX
                    if self.JustSun==False:
                        self.TemperatureIDX
                        self.WindIDX
                        self.RainIDX
                except AttributeError as Error:
                    device=str(Error).split("'")[3].replace("IDX","")
                    self.Error="Could not find "+getattr(self, device+"Device",device)+" device, please make sure it exists."
                    Domoticz.Error(self.Error)
        except Exception as e:
            senderror(e)

    def FindStation(self,q):
        try:
            import pandas
            #Find Country
            url="https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat="+str(self.Latitude)+"&lon="+str(self.Longitude)+"&accept-language=en-US"
            if self.Debug==True:
                Domoticz.Log("Location url is "+url)
            country=requests.get(url).json()["address"]["country"]
            q.put("Checking all Ogimet stations in "+country+" to find the one closest to your location.")
        except Exception as e:
            q.put("Url used to find your country is"+url)
            q.put('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+" Error is: " +str(e))

        try:
            #Find Ogimet station
            url="http://www.ogimet.com/display_stations.php?lang=en&tipo=AND&isyn=&oaci=&nombre=&estado="+country+"&Send=Send"
            if self.Debug==True:
                q.put("Url to find all Ogimet stations is "+url)
            #Parse the table
            html = requests.get(url).content
            df_list = pandas.read_html(html)
            mindist=1000

            q.put("Calculating which station is the closest.")
            station="No station found."
            latdegree= int(str(self.Latitude).split(".")[0])
            if latdegree < 0:
                latdegree*=-1

            for i, Latitude in enumerate(df_list[1][4]):
                if str(latdegree) in Latitude:
                    #Convert from DMS to decimal coordinates
                    degrees=Latitude.split("-")[0]
                    minutes=Latitude.split("-")[1][:-1]
                    lat = float(degrees) + float(minutes)/60
                    if self.Latitude <0:
                        lat*=-1
                    degrees=df_list[1][5][i].split("-")[0]
                    minutes=df_list[1][5][i].split("-")[1][:-1]
                    lon = float(degrees) + float(minutes)/60
                    if self.Longitude <0:
                        lon*=-1
                    #Calculate the distance
                    dist = haversine(self.Latitude, self.Longitude, lat, lon)

                    #If it is the smallest distance so far
                    if dist<mindist:
                        #Check if station has data
                        url="https://www.ogimet.com/cgi-bin/gsynres?lang=en&ind="+df_list[1][0][i]
                        result=urlopen(url).read().decode('utf-8')
                        if not "No valid data found in database for " in result:
                            #Use station
                            mindist=dist
                            station=df_list[1][0][i]
                            stationname=df_list[1][2][i]
            q.put("Found station '"+stationname+"' with id:"+station+" on "+str(round(mindist,1))+"km of your location.",True)
        except Exception as e:
            q.put('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+" Error is: " +str(e))

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

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
    try:
        global _plugin

        if _plugin.Debug==True:
            Domoticz.Log("Calculating sunlocation.")

        #altitude of the Sun 
        timeDecimal = (datetime.datetime.utcnow().hour + datetime.datetime.utcnow().minute / 60)
        solarHour = timeDecimal + (4 * _plugin.Longitude / 60 )
        hourlyAngle = 15 * ( 12 - solarHour )          
        _plugin.sunAltitude = math.degrees(math.asin(math.sin(math.radians(_plugin.Latitude))* math.sin(math.radians(_plugin.Declinaison)) + math.cos(math.radians(_plugin.Latitude)) * math.cos(math.radians(_plugin.Declinaison)) * math.cos(math.radians(hourlyAngle))))
        UpdateDevice(2, int(round(_plugin.sunAltitude)), int(round(_plugin.sunAltitude)))
        
        #azimut of the Sun
        _plugin.azimuth = math.acos((math.sin(math.radians(_plugin.Declinaison)) - math.sin(math.radians(_plugin.Latitude)) * math.sin(math.radians(_plugin.sunAltitude))) / (math.cos(math.radians(_plugin.Latitude)) * math.cos(math.radians(_plugin.sunAltitude) ))) * 180 / math.pi 
        sinAzimuth = (math.cos(math.radians(_plugin.Declinaison)) * math.sin(math.radians(hourlyAngle))) / math.cos(math.radians(_plugin.sunAltitude))
        if(sinAzimuth<0):
            _plugin.azimuth=360-_plugin.azimuth 
        UpdateDevice(1,int(round(_plugin.azimuth)),int(round(_plugin.azimuth)))
    except Exception as e:
        senderror(e)

def Cloudlayer():
    try:
        global _plugin
        if _plugin.Debug==True:
            Domoticz.Log("Retrieving cloudlayer.")
        result=""
        UTC=datetime.datetime.utcnow()
        hour=UTC.hour

        while result=="":
            if len(str(int(hour)-1))==1:
                hour="0"+str(int(hour)-1)
            else:
                hour=str(int(hour)-1)
            UTCtime=str(UTC.year)+str(UTC.month)+str(UTC.day)+hour+"00"
            url="http://www.ogimet.com/cgi-bin/getsynop?block="+_plugin.Station+"&begin="+UTCtime

            if _plugin.Debug==True:
                Domoticz.Log("Ogimet url is: "+url)

            result=urlopen(url).read().decode('utf-8')
            if "Status:" in result:
                result=""

        result=result.split(" "+_plugin.Station+" ")
        Octa=int(result[len(result)-1].split(" ")[1][0])
        if Octa != _plugin.Octa:
            _plugin.Octa=Octa
            Domoticz.Log("Updated cloudlayer to "+str(_plugin.Octa))
    except Exception as e:
        Domoticz.Log("Cloudlayer url is "+url)
        Domoticz.Log(str(result))
        senderror(e)

def VirtualLux():
    try:
        global _plugin
        if _plugin.Debug==True:
            Domoticz.Log("Calculating virtual lux.")

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
            _plugin.weightedLux = Lux * Kc   # radiation of the Sun with the cloud layer
        elif _plugin.sunAltitude <= 1 and _plugin.sunAltitude >= -7: #apply theoretical Lux of twilight
            directRadiation = 0
            scatteredRadiation = 0
            _plugin.ArbitraryTwilightLux=_plugin.ArbitraryTwilightLux-(1-_plugin.sunAltitude)/8*_plugin.ArbitraryTwilightLux
            totalRadiation = scatteredRadiation + directRadiation + _plugin.ArbitraryTwilightLux 
            Lux = totalRadiation / 0.0079 # Radiation in Lux. 1 Lux = 0,0079 W/m²
            _plugin.weightedLux = Lux * Kc   #radiation of the Sun with the cloud layer
        elif _plugin.sunAltitude < -7:  # no management of nautical and astronomical twilight...
            directRadiation = 0
            scatteredRadiation = 0
            totalRadiation = 0
            Lux = 0
            _plugin.weightedLux = 0  #  should be around 3,2 Lux for the nautic twilight. Nevertheless.
        
        UpdateDevice(3,int(round(_plugin.weightedLux)),int(round(_plugin.weightedLux)))
    except Exception as e:
        senderror(e)

#
# Calculate the great circle distance between two points
# on the earth (specified in decimal degrees)
#
def haversine(lat1, lon1, lat2, lon2):
    try:
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [ lat1, lon1, lat2, lon2 ])

        # Haversine formula
        dlat = math.fabs(lat2 - lat1)
        dlon = math.fabs(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        km = c * 6367
        return km
    except Exception as e:
        senderror(e)  

def Altitude(q):
    try:
        global _plugin
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        data = '{"locations":[{"latitude":'+str(_plugin.Latitude)+',"longitude":'+str(_plugin.Longitude)+'}]}'
        response = requests.post('https://api.open-elevation.com/api/v1/lookup', headers=headers, data=data).json()
        Altitude=response["results"][0]['elevation']
        q.put(Altitude)
    except Exception as e:
        if "Expecting value" in str(e):
            q.put(1)
        else:
            q.put('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+" Error is: " +str(e))

def createDevices():
    try:
        global _plugin
        #Check if variable needs to be created
        if 1 not in Devices:
            Domoticz.Log("Created 'Azimut' device")
            Domoticz.Device(Name="Azimut", Unit=1, TypeName="Custom", Used=1).Create()

        if 2 not in Devices:
            Domoticz.Log("Created 'Sun altitude' device")
            Domoticz.Device(Name="Sun altitude", Unit=2, TypeName="Custom", Used=1).Create()

        if 3 not in Devices:
            Domoticz.Log("Created 'Virtual Lux'")
            Domoticz.Device(Name="Virtual Lux", Unit=3, Type=246, Subtype=1, Used=1).Create()

        if 4 not in Devices:
            Domoticz.Log("Created 'Override button")
            Domoticz.Device(Name="Override button", Unit=4, TypeName="Switch", Used=1).Create()

        if _plugin.JustSun==False:
            Domoticz.Log("Checking sunscreen devices")
            for i in range(_plugin.NumberOfSunscreens):
                x=i+5
                if x not in Devices:
                    Domoticz.Log("Created 'Sunscreen"+str(i)+"' device")
                    Domoticz.Device(Name="Sunscreen"+str(i), Unit=x, TypeName="Switch", Switchtype=13, Used=1).Create()

                _plugin.Sunscreens.append(Sunscreen(x,_plugin.Thresholds["azimuth"+str(i)],_plugin.Thresholds["alltitude"+str(i)]))
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
    global _plugin
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it
    if Unit in Devices:
        if Devices[Unit].nValue != nValue or Devices[Unit].sValue != str(sValue) or AlwaysUpdate == True:
            Devices[Unit].Update(nValue, str(sValue))
            if _plugin.Debug==True:
                Domoticz.Log("Update " + Devices[Unit].Name + ": " + str(nValue) + " - '" + str(sValue) + "'")
    return
