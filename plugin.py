# Sunscreen script
# Author: Tsjippy
#
"""
<plugin key="SunScreen" name="Sunscreen plugin" author="Tsjippy" version="1.7.0" wikilink="https://github.com/Tsjippy/Sunscreen" externallink="https://en.wikipedia.org/wiki/Horizontal_coordinate_system">
    <description>
        <h2>Sunscreen plugin</h2><br/>
        This plugin calculates the virtual amount of LUX on your current location<br/>
        It turns on a sunscreen device based on that, based on which you perform actions<br/><br/>

        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Calculates the current sun location and stores them in Domoticz devices</li>
            <li>Calculates the virtual LUX and stores it in a Domoticz device</li>
            <li>Calculates based on your settings if a sunscreen device needs to go open, needs to close, or half closed</li>
            <li>The sunscreen will go open if the wind, rain  comes above the optional set thresholds, or below the temperature threshold</li>
        </ul>
        <h3>Configuration</h3>
        You can just add the hardware, no values are required.<br/>
        But a sunscreen device will only be added if at least the azimuth and altitude thresholds are filled in. <br/>
        To find the correct values for those you can use the azimut and altitude devices that will be created. Just note the degrees values at the time you want to have your sunscreen closed. <br/>
        See for more indormation the external link above. <br/><br/>

        Here is a description how to fill in the fields below.<br/>
        Fill in your domoticz ip and port.<br/>
        Fill in how often the sunscreen device should change.<br/>
        Fill in your azimut thresholds in this order: Azimut low;Azimut high.<br/>
        Fill in your altitude thresholds in this order: Altitude low; Altitude mid; Altitude high.<br/>
        The sunscreen will be half closed if the altitude is between Altitude  mid and altitude high, it will be fully closed if the altitude is between Altitude  low and altitude mid.<br/>
        If you need more sunscreens, just add 5 extra sun thresholds like this:<br/>
        Azimut1 low;Azimut1 high; Azimut2 low;Azimut2 high.<br/>
        Altitude1 low; Altitude1 mid; Altidtude1 high; Altitude2 low; Altitude2 mid; Altidtude2 high.<br/>
        Fill in your LUX thresholds in this order: Lux low; Lux high (Optional).<br/>
        Fill in your temperature (°C) thresholds in this order: Temp low; Temp high (Optional).<br/>
        Fill in your wind (m/s) thresholds in this order: Wind; Gust (Optional).<br/>
        Fill in your rain (mm) threshold (Optional).<br/>
        Fill in your IDX values as found on the devices table in this order: Pressure device IDX;Temperature device IDX;Wind device IDX;Rain device IDX (Optional).<br/>
        Fill in an valid ogimet station id, see https://www.ogimet.com/index.phtml.en.<br/>
    </description>
    <params>
        <param field="Address"  label="Domoticz IP Address and port" width="200px" required="true" default="127.0.0.1:8080"/>
        <param field="Port" label="Switchtime threshold (minutes)" width="100px" required="true" default="30"/>
        <param field="Mode2" label="Azimut thresholds" width="500px"/>
        <param field="Password" label="Altitude thresholds" width="500px"/>
        <param field="Mode3" label="LUX thresholds" width="500px" default="60000;80000"/>
        <param field="Mode4" label="Temp thresholds" width="100px" default="15;25"/>
        <param field="Mode5" label="Wind thresholds" width="100px" default="10;15"/>
        <param field="Username" label="Rain threshold" width="50px" default="0"/>
        <param field="Mode6" label="Wheather devices IDX numbers" width="1000px"/>
        <param field="Mode1"  label="Ogimet Station" width="100px"/>
    </params>
</plugin>
"""

#############################################################################
#                      Imports                                              #
#############################################################################
try:
    import Domoticz
    debug = False
except ImportError:
    import fakeDomoticz as Domoticz
    debug = True
import sys
import datetime
import math
import calendar
import requests
from multiprocessing import Process, Queue
import time
import sqlite3

#############################################################################
#                      Sunscreen Class                                      #
#############################################################################

class Sunscreen:
    global _plugin
    def __init__(self,DeviceID,AzimutLow,AzimutHigh,AltitudeLow,AlltitudeMid,AlltitudeHigh,LuxLow,LuxHigh):
        self.DeviceID = DeviceID
        self.AzimutLow = AzimutLow
        self.AzimutHigh = AzimutHigh
        self.AltitudeLow = AltitudeLow
        self.AlltitudeMid = AlltitudeMid
        self.AlltitudeHigh = AlltitudeHigh
        self.LuxLow = LuxLow
        self.LuxHigh = LuxHigh

    def CheckClose(self):
        try:
            # If screen is down, check if it needs to go up due to the wheater
            if Devices[self.DeviceID].sValue!="Off":
                if _plugin.Wind > _plugin.Thresholds["Wind"] or _plugin.Gust > _plugin.Thresholds["Gust"]:
                    Domoticz.Status("Opening '"+Devices[self.DeviceID].Name+"' because of the wind. ("+str(_plugin.Wind)+" m/s).")
                    ShouldOpen = True
                elif _plugin.Rain > _plugin.Thresholds["Rain"]:
                    Domoticz.Status("Opening '"+Devices[self.DeviceID].Name+"' because of the rain.("+str(_plugin.Rain)+" mm).")
                    ShouldOpen = True
                elif _plugin.weightedLux < self.LuxLow:
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
                if _plugin.Azimuth > self.AzimutLow and _plugin.Azimuth < self.AzimutHigh and _plugin.sunAltitude > self.AltitudeLow and _plugin.sunAltitude < self.AlltitudeHigh:
                    Domoticz.Log("Sun is in region")
                    #Only close if weather is ok
                    if _plugin.Wind <= _plugin.Thresholds["wind"]:
                        if _plugin.Gust <= _plugin.Thresholds["gust"]:
                            if _plugin.Rain <= _plugin.Thresholds["rain"]:
                                if _plugin.weightedLux > self.LuxHigh or _plugin.Temperature > _plugin.Thresholds["TempHigh"]:
                                    #--------------------   Close sunscreen   -------------------- 
                                    if _plugin.sunAltitude > self.AlltitudeMid and Devices[self.DeviceID].sValue != 50:
                                        Domoticz.Log ("Half closing '"+Devices[self.DeviceID].Name+"'.")
                                        UpdateDevice(self.DeviceID, 50, "50")
                                    elif (Devices[self.DeviceID].sValue == "Off") and _plugin.sunAltitude < self.AlltitudeMid:
                                        Domoticz.Log ("Full closing '"+Devices[self.DeviceID].Name+"'.")
                                        UpdateDevice(self.DeviceID, 100, "On")
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
                Domoticz.Log("Last change was less than "+_plugin.SwitchTime+" minutes ago, no action will be performed.")
        except Exception as e:
            senderror(e)

#############################################################################
#                      Baseplugin class                                     #
#############################################################################
class BasePlugin:
    enabled = False
    def __init__(self):
        self.Error                              = False
        self.ArbitraryTwilightLux               = 6.32     # W/m² egal 800 Lux     (the theoritical value is 4.74 but I have more accurate result with 6.32...)
        self.ConstantSolarRadiation             = 1361 # Solar Constant W/m²
        self.Year                               = datetime.datetime.now().year
        self.Yearday                            = datetime.datetime.now().timetuple().tm_yday
        self.AgularSpeed                        = 360/365.25
        self.Declinaison                        = math.degrees(math.asin(0.3978 * math.sin(math.radians(self.AgularSpeed) *(self.Yearday - (81 - 2 * math.sin((math.radians(self.AgularSpeed) * (self.Yearday - 2))))))))
        self.JustSun                            = False
        self.Station                            = ""
        self.Altitude                           = ""
        self.Octa                               = 0
        self.HeartbeatCount                     = -1
        self.Sunscreens                         = []
        self.weightedLux                        = 0
        self.TemperatureIDX                     = 0
        self.WindIDX                            = 0
        self.RainIDX                            = 0
        self.Wind                               = 0
        self.Gust                               = 0
        self.Temperature                        = 0
        self.Rain                               = 0
        self.Pressure                           = 0

        if calendar.isleap(self.Year):
            self.DaysInYear                     = 366
        else:
            self.DaysInYear                     = 365

    def onStart(self):
        try:
            Domoticz.Heartbeat(30)
            import os
            if (os.name == 'nt'):
                Domoticz.Error("Windows is currently not supported.")

            #############################################################################
            #                      Parameters                                           #
            #############################################################################
            self.Debug                          = False
            #Domoticz.Trace(True)
            if not "Location" in Settings:
                self.Error="Location not set in Settings, please update your settings."
                Domoticz.Error(self.Error)
            else:
                loc                             = Settings["Location"].split(";")
                self.Latitude                   = float(loc[0])
                self.Longitude                  = float(loc[1])
                Domoticz.Log("Current location is "+str(self.Latitude)+","+str(self.Longitude))

                self.q2                         = Queue()
                self.p2                         = Process(target=Altitude, args=(self.q2,))
                self.p2.deamon                  = True
                self.p2.start()
                Domoticz.Log("Started search for Altitude.")

                self.Url                        = "http://"+Parameters["Address"]
                if self.Url == "":
                    self.Url                    = "http://127.0.0.1:8080"

                try:
                    self.SwitchTime             = int(Parameters["Port"])
                except ValueError:
                    self.SwitchTime             = 30
                    Domoticz.Error("Please specify a number for 'Switchtime' in the hardware settings. Now setting the default to 30 minutes.")

                try:
                    self.Station                = Parameters["Mode1"]
                    int(self.Station)
                except ValueError:
                    self.Station                = ""

                if self.Station == "":
                    Domoticz.Station("You did not specify a valid Ogimet station id, will try to find one myself now.")
                    self.q1                         = Queue()
                    self.p1                         = Process(target=self.FindStation, args=(self.q1,))
                    self.p1.deamon                  = True
                    self.p1.start()
                    Domoticz.Log("Started search for Ogimet station.")


                self.Thresholds                 = {}
                AzimutThresholds                = Parameters["Mode2"].split(";")
                AltitudeThresholds              = Parameters["Password"].split(";")
                LuxThresholds                   = Parameters["Mode3"].split(";")
                
                try:
                    self.Thresholds["TempLow"]  = Parameters["Mode4"].split(";")[0]
                    self.Thresholds["TempHigh"] = Parameters["Mode4"].split(";")[1]
                except IndexError:
                    Domoticz.Error("Please specify two values for 'Temperature' in the hardware settings.")
                    self.Thresholds["TempLow"]  = 99
                    self.Thresholds["TempHigh"] = 99
                
                self.Thresholds["Rain"]         = Parameters["Username"]
                
                self.Thresholds["Wind"]         = Parameters["Mode5"].split(";")[0]
                try:
                    self.Thresholds["Gust"]     = Parameters["Mode5"].split(";")[1]
                except IndexError:
                    Domoticz.Error("Please specify a value for 'Gust' in the hardware settings.")
                    self.Thresholds["Gust"]     = 99

                if AzimutThresholds==[""]:
                    self.JustSun=True
                    Domoticz.Status("No azimut thresholds are given. No sunscreen device will be created, until you update the hardware.")
                elif AltitudeThresholds==[""]:
                    self.JustSun=True
                    Domoticz.Status("No altitude thresholds are given. No sunscreen device will be created, until you update the hardware.")
                else:
                    self.NumberOfSunscreens=len(AzimutThresholds)/2
                    if self.NumberOfSunscreens.is_integer()==True:
                        self.NumberOfSunscreens=int(self.NumberOfSunscreens)
                        for i in range(self.NumberOfSunscreens):
                            try:
                                self.Thresholds["AzimuthLow_"+str(i)] = AzimutThresholds[i*2]
                                self.Thresholds["AzimuthHigh_"+str(i)] = AzimutThresholds[i*2+1]
                            except IndexError:
                                self.JustSun = True
                                Domoticz.Error("Please specify 2, or a multitude of 2 values for 'Azimuth' in the hardware settings. No sunscreen device will be created, until you update the hardware.")
                            
                            try:
                                self.Thresholds["AlltitudeLow_"+str(i)] = AltitudeThresholds[i*2]
                                self.Thresholds["AlltitudeMid_"+str(i)] = AltitudeThresholds[i*2+1]
                                self.Thresholds["AlltitudeHigh_"+str(i)] = AltitudeThresholds[i*2+2]
                            except IndexError:
                                if len(AltitudeThresholds) == 3 and i > 0:
                                    Domoticz.Status("You specified multiple azimuth values, but only 3 altitude values. I will reuse these three for all other sunscreens.")
                                    self.Thresholds["AlltitudeLow_"+str(i)] = AltitudeThresholds[0]
                                    self.Thresholds["AlltitudeMid_"+str(i)] = AltitudeThresholds[1]
                                    self.Thresholds["AlltitudeHigh_"+str(i)] = AltitudeThresholds[2]
                                else:
                                    self.JustSun = True
                                    Domoticz.Status("Please specify 3 or a multitude of 3 values for 'Alltitude' in the hardware settings. No sunscreen device will be created, until you update the hardware.")
                            
                            try:
                                self.Thresholds["LuxLow_"+str(i)]   = int(LuxThresholds[i*2])
                                self.Thresholds["LuxHigh_"+str(i)]  = int(LuxThresholds[i*2+1])
                            except IndexError:
                                if len(LuxThresholds) == 2 and i > 0:
                                    Domoticz.Status("You specified multiple azimuth values, but only 2 Lux values. I will reuse these 2 for all other sunscreens.")
                                    self.Thresholds["LuxLow_"+str(i)]   = int(LuxThresholds[0])
                                    self.Thresholds["LuxHigh_"+str(i)]  = int(LuxThresholds[1])
                                else:
                                    self.JustSun = True
                                    Domoticz.Status("Please specify 2 or a multitude of 2 values for 'Lux' in the hardware settings. No sunscreen device will be created, until you update the hardware.")
                
                if self.JustSun == False:
                    for key, value in self.Thresholds.items():
                        try:
                            self.Thresholds[key] = float(value)
                            if "High" in key and float(value) < float(self.Thresholds[key.replace("High","Low")]):
                                Domoticz.Error("The value '" + value + "' of " + key + " is smaller then the value '" + str(self.Thresholds[key.replace("High","Low")]) + "' of " + key.replace("High","Low") + ".")
                                self.Thresholds[key] = 99
                                self.Thresholds[key.replace("High","Low")] = 99
                        except ValueError:
                            if "Azimuth" in key or "Alltitude" in key:
                                if value == "":
                                    Domoticz.Error("Please specify a value for '" + key + "' in the hardware settings.")
                                else:
                                    Domoticz.Error("Please specify a number in stead of '" + value + "' for '" + key + "' in the hardware settings. No sunscreen device will be created, until you update the hardware.")
                                self.JustSun = True
                            else:
                                if value == "":
                                    Domoticz.Error("Please specify a value for '" + key + "' in the hardware settings.")
                                else:
                                    Domoticz.Error("Please specify a number in stead of '" + value + "' for '" + key + "' in the hardware settings.")
                                self.Thresholds[key] = 99


                #############################################################################
                #                      Initial checks                                       #
                #############################################################################

                self.CheckWeatherDevices()

                createDevices()
                
                if self.JustSun == False:
                    Domoticz.Log("Will only perform an action every "+str(self.SwitchTime)+" minutes.")
                    for i in range(self.NumberOfSunscreens):
                        Domoticz.Log("Will only close sunscreen '"+str(Devices[i+6].Name)+"' if the azimuth is between "+str(self.Thresholds["AzimuthLow_"+str(i)])+" and "+str(self.Thresholds["AzimuthHigh_"+str(i)])+" degrees, the altitude is between "+str(self.Thresholds["AlltitudeLow_"+str(i)])+" and "+str(self.Thresholds["AlltitudeHigh_"+str(i)])+" degrees, the temperature is above "+str(self.Thresholds["TempHigh"])+"°C and the amount of lux is above "+str(self.Thresholds["LuxHigh_"+str(i)])+" lux.")
                        Domoticz.Log("Will open sunscreen '"+str(Devices[i+6].Name)+"' if the sun is not in the region, it is raining more then " + str(self.Thresholds["Rain"]) + " mm, the temperature drops below "+str(self.Thresholds["TempLow"])+"°C, the wind is more than "+str(self.Thresholds["Wind"])+" m/s, the wind gusts are more than "+str(self.Thresholds["Gust"])+" m/s or the amount of lux is less than "+str(self.Thresholds["LuxLow_"+str(i)])+" lux")

                if self.Debug == True:
                    Domoticz.Log("On Start finished.")
        except Exception as e:
            senderror(e)
            self.Error = "Something went wrong during boot. Please check the logs."

    def onStop(self):
        try:
            if hasattr(self,"p1"):
                self.p1.terminate()

            if hasattr(self,"p2"):
                self.p2.terminate()

            if hasattr(self,"p_cloudlayer"):
                self.p_cloudlayer.terminate()
        except Exception as e:
            senderror(e)

        Domoticz.Status("Terminated running processes")

    #Update the sunscreen device
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

    #Run every 30 seconds
    def onHeartbeat(self):
        try:
            if self.Error==False:
                if self.Station == "" or (hasattr(self,"p1") and self.p1.exitcode == None):
                    if self.q1.empty()==True:
                        Domoticz.Log("Parsing Ogimet station table data.")
                    else:
                        while self.q1.empty()==False:
                            result=str(self.q1.get())
                            if "Error" in result:
                                Domoticz.Error(result)
                                self.Error="Could not find Ogimet station."
                            elif "Found station " in result:
                                Domoticz.Log(result)
                                self.Station=result.split(":")[1].split(" ")[0]

                                try:    
                                    # Open the Domoticz DB
                                    db = sqlite3.connect(Parameters["Database"])
                                    cursor = db.cursor()
                                    #Store station in DB
                                    cursor.execute('''UPDATE Hardware SET Mode1 = ? WHERE Extra=? ''',(self.Station,Parameters["Key"]))
                                    db.commit()
                                    Domoticz.Status("Stored the station id '" + self.Station + "' in the database.")
                                except Exception as e:
                                    senderror(e)
                                finally:
                                    # Close the db connection
                                    db.close()
                            else:
                                Domoticz.Log(result)
                if self.Altitude == "":
                    while self.q2.empty()==False:
                        result=self.q2.get()
                        if "Error" in str(result):
                            Domoticz.Error(result)
                            self.Altitude=1
                            Domoticz.Log("Could not find altitude, using default of 1 meter.")
                        elif "Altitude is " in result:
                            self.Altitude=int(result.split("Altitude is ")[1])
                            Domoticz.Log(result+" meter.")
                        else:
                            Domoticz.Log(result)
                elif self.Station != "" and self.Altitude != "":
                    if self.Debug == True:
                        Domoticz.Log("Updating cloudlayer.")
                    self.q_cloudlayer = Queue()
                    self.p_cloudlayer = Process(target=Cloudlayer, args=(self.q_cloudlayer,))
                    self.p_cloudlayer.deamon=True
                    self.p_cloudlayer.start()

                    DeviceValues = requests.get(self.Url+"/json.htm?type=devices").json()['result']
                    for Value in DeviceValues:
                        if Value["idx"] == self.TemperatureIDX:
                            self.Temperature=float(Value["Temp"])
                        elif Value["idx"] == self.WindIDX:
                            Wind = Value["Data"].split(";")
                            self.Wind = float(Wind[2])/10
                            self.Gust = float(Wind[3])/10
                        elif Value["idx"] == self.RainIDX:
                            self.Rain = float(Value["Rain"])
                        elif Value["idx"] == self.PressureIDX:
                            self.Pressure = float(Value["Barometer"])

                    SunLocation()

                    while self.q_cloudlayer.empty() == False:
                        result=str(self.q_cloudlayer.get())
                        if "Error" in result:
                            Domoticz.Error(result)
                        elif "Updated cloudlayer to " in result:
                            Domoticz.Log(result)
                            self.Octa = int(result.replace("Updated cloudlayer to ",""))
                            UpdateDevice(4,int(self.Octa),int(self.Octa))
                        else:
                            Domoticz.Log(result)

                    if self.Debug == True:
                        Domoticz.Log("Current cloudlayer is "+str(self.Octa))

                    VirtualLux()

                    if self.JustSun == False and Devices[5].sValue != "On":
                        for screen in self.Sunscreens:
                            screen.CheckClose()
                    elif Devices[5].sValue == "On" and self.Debug == True:
                        Domoticz.Status("Not performing sunscreen actions as the override button is on.")
            else:
                Domoticz.Error(self.Error)
        except Exception as e:
            senderror(e)

    def CheckWeatherDevices(self):
        try:
            if self.Debug == True:
                Domoticz.Log("Checking weather devices.")

            if self.Error == False:
                try:
                    self.AllDevices = requests.get(self.Url+"/json.htm?type=devices&used=true").json()['result']
                except Exception as e:
                    self.Error = "Could not get all devces with url: "+self.Url+"/json.htm?type=devices&used=true"
                    Domoticz.Error(self.Error)
                    senderror(e)

            if self.Error == False:
                #Check if devices are valid.
                #Barometer
                try:
                    self.PressureIDX            = int(Parameters["Mode6"].split(";")[0])
                    DeviceDetails = [x for x in self.AllDevices if x["idx"] == str(self.PressureIDX)][0]
                    if DeviceDetails["SubType"] != 'Barometer':
                        Domoticz.Error("You did specify a " + DeviceDetails["SubType"] + " device but it should be a pressure device, containing a Barometer field.")
                        self.PressureIDX        = 0
                except IndexError:
                    Domoticz.Status("No 'Pressure device' specified, going to find it myself.")
                    self.PressureIDX            = 0
                except ValueError:
                    if str(Parameters["Mode6"].split(";")[0]) == "":
                        Domoticz.Status("You did not specify a pressure device idx. Will try to find a device myself now.")
                    else:
                        Domoticz.Error("'" + str(Parameters["Mode6"].split(";")[0]) + "' is not a valid number for the presure idx, please specify a valid number. Will try to find one myself now.")
                    self.PressureIDX            = 0

                #Wind
                try:
                    self.WindIDX                = int(Parameters["Mode6"].split(";")[1])
                    DeviceDetails = [x for x in self.AllDevices if x["idx"] == str(self.WindIDX)][0]
                    if DeviceDetails["Type"] != 'Wind':
                        Domoticz.Error("You did specify a " + DeviceDetails["Type"] + " device but it should be a wind device.")
                        self.WindIDX            = 0
                except IndexError:
                    Domoticz.Status("No 'Wind device' specified, going to find it myself.")
                    self.WindIDX                = 0
                except ValueError:
                    if str(Parameters["Mode6"].split(";")[1]) == "":
                        Domoticz.Status("You did not specify a wind device idx. Will try to find a device myself now.")
                    else:
                        Domoticz.Error("'" + str(Parameters["Mode6"].split(";")[1]) + "' is not a valid number for the wind device idx, please specify a valid number. Will try to find one myself now.")
                    self.WindIDX                = 0

                #Temperature
                try:
                    self.TemperatureIDX         = int(Parameters["Mode6"].split(";")[2])
                    DeviceDetails = [x for x in self.AllDevices if x["idx"] == str(self.TemperatureIDX)][0]["Temp"]
                except IndexError:
                    Domoticz.Status("No 'Temperature device' specified, going to find it myself.")
                    self.TemperatureIDX         = 0
                except ValueError:
                    if str(Parameters["Mode6"].split(";")[2]) == "":
                        Domoticz.Status("You did not specify a temperature device idx. Will try to find a device myself now.")
                    else:
                        Domoticz.Error("'" + str(Parameters["Mode6"].split(";")[2]) + "' is not a valid number for the temperature device idx, please specify a valid number. Will try to find one myself now.")
                    self.TemperatureIDX         = 0
                except KeyError:
                    Domoticz.Error("You did specify a " + DeviceDetails["Type"] + " but it should be a temperature device.")
                    self.TemperatureIDX         = 0

                #Rain
                try:
                    self.RainIDX                = int(Parameters["Mode6"].split(";")[3])
                    DeviceDetails = [x for x in self.AllDevices if x["idx"] == str(self.RainIDX)][0]
                    if DeviceDetails["Type"] != 'Rain':
                        Domoticz.Error("You did specify a " + DeviceDetails["Type"] + " device but it should be a rain device.")
                        self.RainIDX            = 0
                except IndexError:
                    Domoticz.Status("No 'Rain device' specified, going to find it myself.")
                    self.RainIDX                = 0
                except ValueError:
                    if str(Parameters["Mode6"].split(";")[3]) == "":
                        Domoticz.Status("You did not specify a rain device idx. Will try to find a device myself now.")
                    else:
                        Domoticz.Error("'" + str(Parameters["Mode6"].split(";")[3]) + "' is not a valid number for the rain idx, please specify a valid number. Will try to find one myself now.")
                    self.RainIDX                = 0

                #Loop through all devices to find missing devices
                Found = False
                for device in self.AllDevices:
                    if "Temp" in device and self.TemperatureIDX == 0:
                        self.TemperatureIDX = device["idx"]
                        Domoticz.Status("Found temperature device '" + device["Name"] + "'")
                        Found = True
                    if device["Type"] == "Wind" and self.WindIDX == 0:
                        self.WindIDX        = device["idx"]
                        Domoticz.Status("Found wind device '" + device["Name"] + "'")
                        Found = True
                    elif device["Type"] == "Rain" and self.RainIDX == 0:
                        self.RainIDX        = device["idx"]
                        Domoticz.Status("Found rain device '"+device["Name"] + "'")
                        Found = True
                    elif "Barometer" in device and self.PressureIDX == 0:
                        self.PressureIDX    = device["idx"]
                        Domoticz.Status("Found pressure device '" + device["Name"] + "'")
                        Found = True

                    if str(self.TemperatureIDX) == device["idx"]:
                        self.Temperature    = float(device["Temp"])
                        Domoticz.Log("Using '" + device["Name"]+"' to get the temperature. Current temperature: " + str(self.Temperature) + "°C.")

                    if str(self.WindIDX) == device["idx"]:
                        self.Wind           = float(device["Speed"])
                        self.Gust           = float(device["Gust"])
                        Domoticz.Log("Using '" + device["Name"] + "' to get the windspeed and wind gusts. Current wind: " + str(self.Wind) + " m/s. Current wind gust: " + str(self.Gust) + " m/s.")
                    elif str(self.RainIDX) == device["idx"]:
                        self.Rain           = float(device["Rain"])
                        Domoticz.Log("Using '" + device["Name"] + "' to get the rain. Current expected rain: " + str(self.Rain) + " mm.")
                    elif str(self.PressureIDX) == device["idx"]:
                        self.Pressure       = float(device["Barometer"])
                        Domoticz.Log("Using '" + device["Name"] +"' to get the presure. Current pressure: " + str(self.Pressure) + " hPa.")

                if Found == True:
                    #Store found devices in DB
                    try:
                        IdxString = str(self.PressureIDX) + ";" + str(self.WindIDX) + ";" + str(self.TemperatureIDX)  + ";" + str(self.RainIDX)
                        # Open the Domoticz DB
                        db = sqlite3.connect(Parameters["Database"])
                        cursor = db.cursor()
                        #Store station in DB
                        cursor.execute('''UPDATE Hardware SET Mode6 = ? WHERE Extra = ? ''',(IdxString,Parameters["Key"]))
                        db.commit()
                        Domoticz.Status("Stored the device IDX values '" + IdxString + "' in the database.")
                    except Exception as e:
                        senderror(e)
                    finally:
                        # Close the db connection
                        db.close()
                
                if self.PressureIDX == 0:
                    Domoticz.Error("Please make sure you have a Pressure device available. This plugin cannot function without it.")
                    self.Error = "No pressure device found."

                if self.JustSun == False:
                    if self.TemperatureIDX == 0:
                        Domoticz.Error( "Could not find a temperature device, please make sure it exists, I will ignore the temperature thresholds untill then.")
                    if self.WindIDX == 0:
                        Domoticz.Error( "Could not find a wind device, please make sure it exists, I will ignore the wind thresholds untill then.")
                    if self.RainIDX == 0:
                        Domoticz.Error( "Could not find a rain device, please make sure it exists, I will ignore the rain threshold untill then.")
                    
        except Exception as e:
            senderror(e)

    def FindStation(self,q):
        try:
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
            if self.Debug == True:
                q.put("Importing pandas")
            import pandas

            if self.Debug == True:
                q.put("Importing pandas done")

            #Find Ogimet station
            stations=[]
            url="http://www.ogimet.com/display_stations.php?lang=en&tipo=AND&isyn=&oaci=&nombre=&estado="+country+"&Send=Send"
            if self.Debug==True:
                q.put("Url to find all Ogimet stations is "+url)
            #Parse the table
            html = requests.get(url).content
            #Read the staioncode as string, not as number, to keep leading zero's
            if self.Debug == True:
                q.put("Processing html table.")

            df_list = pandas.read_html(html, converters = {'WMO INDEX': str})
            mindist=1000

            q.put("Calculating which station is the closest.")
            station="No station found."
            latdegree= int(str(self.Latitude).split(".")[0])
            if latdegree < 0:
                latdegree*=-1

            Domoticz.Error("df_list is ")
            Domoticz.Error("df_list is "+str(df_list))
            for i, Latitude in enumerate(df_list[1]['Latitude']):
                if str(latdegree) in Latitude:
                    #Convert from DMS to decimal coordinates
                    degrees=Latitude.split("-")[0]
                    minutes=Latitude.split("-")[1][:-1]
                    lat = float(degrees) + float(minutes)/60
                    if self.Latitude <0:
                        lat*=-1
                    degrees=df_list[1]['Longitude'][i].split("-")[0]
                    minutes=df_list[1]['Longitude'][i].split("-")[1][:-1]
                    lon = float(degrees) + float(minutes)/60
                    if self.Longitude <0:

                        lon*=-1
                    #Calculate the distance
                    dist = haversine(self.Latitude, self.Longitude, lat, lon)

                    #If it is the smallest distance so far
                    if dist<mindist:
                        #Check if station has data
                        stationcode = str(df_list[1]['WMO INDEX'][i])
                        url="https://www.ogimet.com/cgi-bin/gsynres?lang=en&ind="+stationcode
                        result=requests.get(url).text

                        if not "No valid data found in database for " in result:
                            if self.Debug==True:
                                q.put("Checking station "+stationcode)
                                
                            UTC=datetime.datetime.utcnow()
                            UTCtime=datetime.datetime.strftime(UTC+datetime.timedelta(hours=-3),'%Y%m%d%H')+"00"
                            url="http://www.ogimet.com/cgi-bin/getsynop?block="+stationcode+"&begin="+UTCtime
                            result=requests.get(url)
                            if result.status_code == 200 and not "Status" in result.text and not "Max retries exceeded with url:"  in result.text:
                                result=result.text
                                if result == "":
                                    q.put("Empty result, url used is "+url)
                            else:
                                q.put("No result for station "+df_list[1]['Name'][i])
                                result =""

                            if result !="":
                                result=result.split(" "+stationcode+" ")
                                Octa=result[1].split(" ")[1][0]

                                if self.Debug==True:
                                    q.put("Found octa of "+str(Octa))
                                if Octa != "/":
                                    #Use station
                                    mindist=dist
                                    station=stationcode
                                    stationname=df_list[1]['Name'][i]
                                else:
                                    stations+=[[dist,stationcode,df_list[1]['Name'][i]]]


            if station=="No station found." or mindist > 50:
                mindist=1000
                for stat in stations:
                    if stat[0] < mindist:
                        mindist=stat[0]
                        station=stat[1]
                        stationname=stat[2]
                q.put("Found station '"+stationname+"' with id:"+station+" on "+str(round(mindist,1))+"km of your location. (This station does currently not supply any cloudlayer data, but non of the stations within 50 km of your location do.)",True)
            else:                
                q.put("Found station '"+stationname+"' with id:"+station+" on "+str(round(mindist,1))+"km of your location.",True)
        except Exception as e:
            q.put('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+" Error is: " +str(e))

def senderror(e):
    try:
        Domoticz.Error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+" Error is "+str(e))
    except:
        Domoticz.Error("sys.exc_info()[-1].tb_lineno: "+sys.exc_info()[-1].tb_lineno)
    return

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

def Cloudlayer(q):
    try:
        global _plugin
        if _plugin.Debug==True:
            q.put("Retrieving cloudlayer.")
        result=""
        UTC=datetime.datetime.utcnow()
        delta = 1

        while result=="":
            delta -= 1
            UTCtime=datetime.datetime.strftime(UTC+datetime.timedelta(hours=delta),'%Y%m%d%H')+"00"
            url="http://www.ogimet.com/cgi-bin/getsynop?block="+_plugin.Station+"&begin="+UTCtime

            if _plugin.Debug==True:
                q.put("Trying this Ogimet url: "+url)

            result=requests.get(url)
            if result.status_code == 200 and not "Status" in result.text and not "Max retries exceeded with url:"  in result.text:
                result=result.text
                if result=="" and _plugin.Debug==True:
                    q.put("Got an empty result, will try an hour earlier.")
            elif result.status_code == 501:
                result = ""
                if result=="" and _plugin.Debug==True:
                    q.put("Got an empty result, will try an hour earlier.")
            else:
                q.put("Could not retrieve cloudlayer, using previous value of "+str(_plugin.Octa)+". Error is "+ str(result.text)+" URL is "+url)
                result=""
                break

        if result !="":
            result=result.split(" "+_plugin.Station+" ")
            Octa=result[1].split(" ")[1][0]
            if Octa == "/":
                if _plugin.Debug==True:
                    Domoticz.Log("Cloud layer not available, using previous value.")
                Octa=_plugin.Octa
            else:
                Octa=int(Octa)

            if Octa == 9:
                Octa = 8
            if Octa != _plugin.Octa:
                _plugin.Octa=Octa
                q.put("Updated cloudlayer to "+str(_plugin.Octa))
    except Exception as e:
        if _plugin.Debug==False:
            Domoticz.Log("Ogimet url is: "+url)
        Domoticz.Log("Ogimet url is: "+url+" Result is "+str(result)+" Result status code is "+str(requests.get(url).status_code))
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

def Altitude(q,):
    x=0
    while True:
        x+=1
        try:
            global _plugin
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
            data = '{"locations":[{"latitude":'+str(_plugin.Latitude)+',"longitude":'+str(_plugin.Longitude)+'}]}'
            response = requests.post('https://api.open-elevation.com/api/v1/lookup', headers=headers, data=data).json()
            Altitude=response["results"][0]['elevation']
            q.put("Altitude is "+str(Altitude))
            break
        except Exception as e:
            if ("Expecting value" in str(e) or "Connection aborted" in str(e)) and x < 6:
                q.put("Retrying altitude.")
                time.sleep(10)
                continue
            #else:
                #q.put('Error on line {}'.format(sys.exc_info()[-1].tb_lineno)+" Error is: " +str(e))

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
            Domoticz.Log("Created 'Virtual Lux' device")
            Domoticz.Device(Name="Virtual Lux", Unit=3, Type=246, Subtype=1, Used=1).Create()

        if 4 not in Devices:
            Domoticz.Log("Created 'Cloudlayer' device")
            Domoticz.Device(Name="Cloudlayer", Unit=4, TypeName="Custom", Used=1).Create()

        if 5 not in Devices:
            Domoticz.Log("Created 'Override button")
            Domoticz.Device(Name="Override button", Unit=5, TypeName="Switch", Used=1).Create()

        if _plugin.JustSun==False:
            Domoticz.Log("Checking sunscreen devices")
            for i in range(_plugin.NumberOfSunscreens):
                x=i+6
                if x not in Devices:
                    Domoticz.Log("Created 'Sunscreen"+str(i)+"' device")
                    Domoticz.Device(Name="Sunscreen"+str(i), Unit=x, TypeName="Switch", Switchtype=13, Used=1).Create()

                _plugin.Sunscreens.append(Sunscreen(x,_plugin.Thresholds["AzimuthLow_"+str(i)],_plugin.Thresholds["AzimuthHigh_"+str(i)],_plugin.Thresholds["AlltitudeLow_"+str(i)],_plugin.Thresholds["AlltitudeMid_"+str(i)],_plugin.Thresholds["AlltitudeHigh_"+str(i)],_plugin.Thresholds["LuxLow_"+str(i)],_plugin.Thresholds["LuxHigh_"+str(i)]))
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
