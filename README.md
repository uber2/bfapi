# bfapi
api for Börse Frankfurt based on mechanize and selenium

Quickstart
----------
<p>Apple is listed with ISIN US0378331005, WKN 865985, and ticker APC at the Deutsche Börse. 
We can user either one of them to retrieve the current market data</p>

<p>>>> import bfapi<br/>
>>> bfapi.get("APC)"</p>

Dependencies
------------
the package will only work under pyhton 2.7.9, because mechanize has only been written for pyhton 2.7. Bfapi uses the following packages

selenium, mechanize, logging, re, bs4, time, json, pprint
