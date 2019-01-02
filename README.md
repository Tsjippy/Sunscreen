Sunscreen plugin for Domoticz
============================================


Short summary
-------------
This plugin calculates the location of the sun, stores them in devices.
Calculates the virtual lux based on the sun location, the cloud layer and your altitude.

Installation and setup
----------------------
1)  Install Plugin: 
```bash
cd domoticz/plugins
git clone https://github.com/Tsjippy/Sunscreen
```
2) Install dependecies: 
```bash
sudo pip3 install requests -t /home/pi/domoticz/plugins/Sunscreen
sudo pip3 install lxml -t /home/pi/domoticz/plugins/Sunscreen
sudo pip3 install pandas -t /home/pi/domoticz/plugins/Sunscreen
sudo apt-get install libatlas-base-dev
```
3) Restart domoticz: 
```bash
sudo service domoticz.sh restart
```
4) Add hardware, fill in the required fields.

Known issues
----------
* 

Known bugs
----------
* 

Releases
----------
2018-12-13: Initial release (1.0.0) <br/>
2018-12-17: Now supports multiple sunscreens, and searches for the best Ogimet station automatically. Also retrieves the altitude automatically.<br/>
2018-12-18 (1.1.3): Fixes a problem resulting not being able to update the hardware, added a sunscreen override button.<br/>
2019-01-02 (1.4.1): Ogimet url bug fix, it now uses leading zeros for month and day in the url
