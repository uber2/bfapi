# bfapi
unoffical api for Börse Frankfurt (Frankfurt Stock Exchange) based on web scraping.

##Example
Apple is listed with ISIN US0378331005, WKN 865985, and ticker APC at the Deutsche Börse. 
We can user either one of them to retrieve the current market data:

```python
import bfapi
bfapi.get("APC")
```

##No Real Time Quotes
Note that bfapi cannot be used to get real time quotes from Deutsche Börse. There will always be a delay of a couple of seconds due to the nature of web scraping, and the quotes might be provided with a short delay by Deutsche Börse in the first place. **Do not base financial decisions on the use of this api**.

##Dependencies
the package will only work under pyhton 2.7, because bfapi uses mechanize to download the sources of web pages and mechanize has not yet been ported to python 3. Bfapi uses the following packages:

- selenium
- mechanize
- logging
- re
- bs4
- time
- json
- pprint
