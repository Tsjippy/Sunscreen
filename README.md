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
sudo pip3 install requests
sudo pip3 install pandas
sudo apt-get install libatlas-base-dev
```
3) Restart domoticz: 
```bash
sudo service domoticz.sh restart
```
4) Add hardware, fill in the required fields.

Known bugs
----------
* 

Releases
----------
2019-03-31 (1.7.0): Store autmatically found info in the database.
2019-03-25 (1.6.0): Better hardware page and device checks.<br/>
2019-02-15 (1.5.0): No longer a need to specify wheather devices.<br/>
2019-01-02 (1.4.1): Ogimet url bug fix, it now uses leading zeros for month and day in the url.<br/>
2018-12-18 (1.1.3): Fixes a problem resulting not being able to update the hardware, added a sunscreen override button.<br/>
2018-12-17 (1.1.0): Now supports multiple sunscreens, and searches for the best Ogimet station automatically. Also retrieves the altitude automatically.<br/>
2018-12-13 (1.0.0): Initial release  <br/>

Donations
----------
If you want, you can thank me by donating via https://www.paypal.me/Tsjippy
