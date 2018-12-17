# Sunscreen script
# Author: Tsjippy
#
"""
<plugin key="SunScreen" name="Sunscreen plugin" author="Tsjippy" version="1.0.2" wikilink="http://www.domoticz.com/wiki/plugins/plugin.html" externallink="https://wiki.domoticz.com/wiki/Real-time_solar_data_without_any_hardware_sensor_:_azimuth,_Altitude,_Lux_sensor...">
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
        Fill in your weather thresholds in this order: Lux low; Lux high;Temp low; Temp high;Wind;Gust;Rain<br/>
        Fill in your weatherdevice names in this order: Pressure device;Temperature device;Wind device;Rain device<br/>
    </description>
    <params>
        <param field="Mode1" label="Switchtime threshold (minutes)" width="200px" required="true" default="30"/>
        <param field="Mode2" label="Sun thresholds" width="1000px" default="Azimut low;Azimut high; Altitude low; Altitude mid; Altidtude high"/>
        <param field="Mode3" label="Weather thresholds" width="1000px" default=""/>
        <param field="Mode4" label="Wheater devices" width="1000px" required="true" default="Pressure;Temp;Wind;Rain"/>
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
#sudo pip3 install html5lib -t /home/pi/domoticz/plugins/Sunscreen
#sudo pip3 install BeautifulSoup4 -t /home/pi/domoticz/plugins/Sunscreen
#sudo apt-get install libatlas-base-dev
import pandas
from multiprocessing import Process, Queue
import time

class BasePlugin:
    enabled = False
    def __init__(self):
        #self.var = 123
        return

    def onStart(self):
        global q1
        global q2
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
        Domoticz.Heartbeat(30)
        self.JustSun=False
        self.Station=""
        self.Altitude=""
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
                q1 = Queue()
                self.p1 = Process(target=self.FindStation, args=(q1,))
                self.p1.deamon=True
                self.p1.start()
                Domoticz.Log("Started search for Ogimet station.")

                q2 = Queue()
                self.p2 = Process(target=Altitude, args=(q2,))
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
                    self.NumberOfSunscreens=int(len(SunThresholds)/5)
                    for i in range(self.NumberOfSunscreens):
                        self.Thresholds["azimuth"+str(i)]=[SunThresholds[i],SunThresholds[i+1]]
                        self.Thresholds["alltitude"+str(i)]=[SunThresholds[i+2],SunThresholds[i+3],SunThresholds[i+4]]

                if WeatherThresholds!=[""] and self.JustSun==False:
                    self.Thresholds["lux"]=[WeatherThresholds[0],WeatherThresholds[1]]
                    self.Thresholds["temp"]=[WeatherThresholds[2],WeatherThresholds[3]]
                    self.Thresholds["wind"]=WeatherThresholds[4]
                    self.Thresholds["gust"]=WeatherThresholds[5]
                    self.Thresholds["rain"]=WeatherThresholds[6]
                elif (WeatherThresholds==[""]):
                    self.JustSun=True
                    Domoticz.Status("No weather thresholds are given, so no sunscreen device will be created.")     

                if self.JustSun==False:
                    Domoticz.Log("Will only perform an action every "+str(self.switchtime)+" minutes.")
                    for i in range(self.NumberOfSunscreens):
                        Domoticz.Log("Will only close sunscreen"+str(i)+" if the azimuth is between "+self.Thresholds["azimuth"+str(i)][0]+" and "+self.Thresholds["azimuth"+str(i)][1]+" degrees, the altitude is between "+self.Thresholds["alltitude"+str(i)][0]+" and "+self.Thresholds["alltitude"+str(i)][2]+" degrees, the temperature is above "+self.Thresholds["temp"][1]+" degrees and the amount of lux is between "+self.Thresholds["lux"][0]+" and "+self.Thresholds["lux"][1]+" lux")
                    Domoticz.Log("Will open a sunscreen if it is raining, the temperature drops below "+self.Thresholds["temp"][0]+", the wind is more than "+self.Thresholds["wind"]+" or the gust are more than "+self.Thresholds["gust"]+"")

                    self.CheckWeatherDevices()

                    createDevices()
                    #self.Station=FindStation()
        except Exception as e:
            self.Error="Something went wrong during boot. Please chack the logs."
            senderror(e)

    def onStop(self):
        Domoticz.Log("onStop called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onHeartbeat(self):
        global q1
        global q2

        if self.Error==False:
            try:
                if self.p1.exitcode == None or self.Station=="":
                    if q1.empty()==True:
                        Domoticz.Log("Parsing Ogimet station table data.")
                    while q1.empty()==False:
                        result=str(q1.get())
                        if "Error" in result:
                            Domoticz.Error(result)
                            self.Error="Could not find Ogimet station."
                        elif "Found station " in result:
                            Domoticz.Log(result)
                            self.Station=result.split(" ")[2]
                        else:
                            Domoticz.Log(result)
                if self.p2.exitcode != None and self.Altitude=="":
                    self.Altitude=int(q2.get())
                    Domoticz.Log("Altitude is "+str(self.Altitude)+" meter.")
                elif (self.Station!=""):
                    self.Pressure=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.PressureIDX).json()['result'][0]["Barometer"]

                    SunLocation()

                    Cloudlayer()
                    #Domoticz.Log("Current cloudlayer is "+str(self.Octa))

                    VirtualLux()

                    if self.JustSun==False:
                        self.Temperature=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.TemperatureIDX).json()['result'][0]["Temp"]
                        Wind=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.WindIDX).json()['result'][0]["Data"].split(";")
                        self.Wind=Wind[2]
                        self.Gust=Wind[3]
                        self.Rain=requests.get(url=self.url+"/json.htm?type=devices&rid="+self.RainIDX).json()['result'][0]["Data"]
            except Exception as e:
                senderror(e)
        else:
            Domoticz.Error(self.Error)

    def CheckWeatherDevices(self):
        if len(self.WeatherDevices)==1:
            self.PressureDevice=self.WeatherDevices[0]
            self.TemperatureDevice=""
            self.WindDevice=""
            self.RainDevice=""
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
                self.PressureIDX
                if self.JustSun==False:
                    self.TemperatureIDX
                    self.WindIDX
                    self.RainIDX
            except AttributeError as Error:
                device=str(Error).split("'")[3].replace("IDX","")
                self.Error="Could not find "+getattr(self, device+"Device",device)+" device, please make sure it exists."
                Domoticz.Error(self.Error)

    def FindStation(self,q):
        try:
            #Find Country
            url="https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat="+str(self.Latitude)+"&lon="+str(self.Longitude)+"&accept-language=en-US"
            #Domoticz.Log("Location url is "+url)
            country=requests.get(url).json()["address"]["country"]
            q.put("Checking all Ogimet stations in "+country+" to find the one closest to your location.")
            #Find Ogimet station
            url="http://www.ogimet.com/display_stations.php?lang=en&tipo=AND&isyn=&oaci=&nombre=&estado="+country+"&Send=Send"
            #q.put("url is "+url)
            #Parse the table
            html = requests.get(url).content
            df_list = pandas.read_html(html)
            mindist=1000

            q.put("Calculating which station is the closest")
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
            q.put("Found station "+stationname+" with id:"+station+" on "+str(round(mindist,1))+"km of your location.",True)
        except Exception as e:
            q.put('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+" Error is: " +str(e))

global _plugin
global q1
global q2
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
            result=urlopen(url).read().decode('utf-8')

        _plugin.Octa=int(result.split(" "+_plugin.Station+" ")[1].split(" ")[0][0])
    except Exception as e:
        Domoticz.Log("Cloudlayer url is "+url)
        Domoticz.Log(str(result)+str(result==""))
        senderror(e)

def VirtualLux():
        global _plugin
        try:
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
                _plugin.ArbitraryTwilightLux=_plugin.ArbitraryTwilightLux-(1-_plugin.sunAltitude)/8*_plugin.ArbitraryTwilightLux
                totalRadiation = scatteredRadiation + directRadiation + _plugin.ArbitraryTwilightLux 
                Lux = totalRadiation / 0.0079 # Radiation in Lux. 1 Lux = 0,0079 W/m²
                weightedLux = Lux * Kc   #radiation of the Sun with the cloud layer
            elif _plugin.sunAltitude < -7:  # no management of nautical and astronomical twilight...
                directRadiation = 0
                scatteredRadiation = 0
                totalRadiation = 0
                Lux = 0
                weightedLux = 0  #  should be around 3,2 Lux for the nautic twilight. Nevertheless.
            
            UpdateDevice(3,int(round(weightedLux)),int(round(weightedLux)))
            #Domoticz.Log("Virtual LUX is "+str(round(weightedLux)))
        except Exception as e:
            senderror(e)

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

def Altitude(q):
    global _plugin
    try:
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        data = '{"locations":[{"latitude":'+str(_plugin.Latitude)+',"longitude":'+str(_plugin.Longitude)+'}]}'
        response = requests.post('https://api.open-elevation.com/api/v1/lookup', headers=headers, data=data).json()
        Altitude=response["results"][0]['elevation']
        q.put(Altitude)
    except Exception as e:
        q.put('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+" Error is: " +str(e))

def createDevices():
    global _plugin
    #Check if variable needs to be created
    try:
        if 1 not in Devices:
            Domoticz.Log("Created 'Azimut' device")
            Domoticz.Device(Name="Azimut", Unit=1, TypeName="Custom", Used=1).Create()
            UpdateImage(1, 'ChromecastLogo')

        if 2 not in Devices:
            Domoticz.Log("Created 'Sun altitude' device")
            Domoticz.Device(Name="Sun altitude", Unit=2, TypeName="Custom", Used=1).Create()
            UpdateImage(2, 'ChromecastLogo')

        if 3 not in Devices:
            Domoticz.Log("Created 'Virtual Lux'")
            Domoticz.Device(Name="Virtual Lux", Unit=3, Type=246, Subtype=1, Used=1).Create()
            UpdateImage(3, 'ChromecastLogo')

        if _plugin.JustSun==False:
            Domoticz.Log("Checking sunscreen devices")
            for i in range(_plugin.NumberOfSunscreens):
                x=i+4
                if x not in Devices:
                    Domoticz.Log("Created 'Sunscreen"+str(i)+"' device")
                    Domoticz.Device(Name="Sunscreen"+str(i), Unit=x, TypeName="Switch", Switchtype=13, Used=1).Create()
                    UpdateImage(x, 'ChromecastLogo')
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
        if Devices[Unit].nValue != nValue or Devices[Unit].sValue != str(sValue) or AlwaysUpdate == True:
            Devices[Unit].Update(nValue, str(sValue))
            Domoticz.Log("Update " + Devices[Unit].Name + ": " + str(nValue) + " - '" + str(sValue) + "'")
    return
