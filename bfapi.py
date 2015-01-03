import logging
logging.basicConfig(level=logging.WARNING)
import re
import mechanize
from bs4 import BeautifulSoup
import urllib2
from selenium import webdriver
import time
import json
import pprint

logger = logging.getLogger("bfapi")
	
def get(isin):
	"""Main Function: downloads market data from Deutsche Boerse for one ISIN or a list of ISINs."""
	logger = logging.getLogger(__name__)
	ls_bidandask = []
	logger.debug("data type of isin is %s",type(isin))
	if type(isin) is not list:
		isin = [isin]
	
	for asset in isin:
		try:
			if type(asset) is str or type(asset) is unicode:
				page = _get_asset_page(asset)
				document = _parse_asset_page(page)
				document["exchange"] = "Frankfurt"
				logger.debug("Result from parser:\n%s" % pprint.pformat(document))
				ls_bidandask.append(document)
			else:
				logger.error('string or list of strings expected as input')
				return ls_bidandask
		except:
			logger.error(asset + " SKIPPED!!")
			next
	return ls_bidandask

def _get_asset_page(isin):
	"""Downloads the source of the asset's web page."""
	logger = logging.getLogger(__name__)
	logger.debug("get page for isin %s",isin)
	b = mechanize.Browser()
	b.set_handle_robots(False)
	b.open("http://www.boerse-frankfurt.de/")
	# select form, number found by trial and error
	b.select_form(nr=1)
	# fill in the form
	b['name_isin_wkn'] = isin
	# submit form
	page = b.submit().read()
	return page
	
def asset_exists(asset):
	"""Checks if an asset has a proper web-page at Deutsche Boerse"""
	logger = logging.getLogger(__name__)
	logger.debug("check if asset exists")
	page = _get_asset_page(asset)
	soup = BeautifulSoup(page)
	if not len(soup.findAll('h1',text="Suchergebnisse")) == 0:
		logger.debug("No, the asset does not exist")
		return False
	else:
		# Find ISIN
		ISIN = soup.findAll("h4")[0]
		pattern=re.compile("[A-z]{2}\S{10}")
		ISIN = pattern.search(str(ISIN)).group(0)
		logger.info("I found the ISIN %s for your asset %s",ISIN, asset)
		return ISIN

def _parse_asset_page(page):
	"""Scraps data our of downloaded source of web page"""
	logger = logging.getLogger(__name__)
	nothing_found = "no data" # this value will be set whenever no value is found on the product page
	logger.debug("start parsing page ...")
	soup = BeautifulSoup(page)
	
	document={}

	# Find ISIN
	try:
		ISIN = soup.findAll("h4")[0]
		pattern=re.compile("[A-z]{2}\S{10}")
		ISIN = pattern.search(str(ISIN)).group(0)
		document["ISIN"] = unicode(ISIN)
	except:
		logger.warning("ISIN not found")
		document["ISIN"] = nothing_found
		
	# Find Name
	try: 
		document["Name"] = soup.findAll("h1",{"class":None})[0].string	
	except:
		logger.warning("Name for %s not found",document["ISIN"])
		document["Name"] = nothing_found
	
	# Find bid and ask
	try:
		baa = soup.findAll('td',text='Geld / Brief')[0].parent.findAll(text=re.compile('\d{1,3}[,]\d{2}'))
		logger.debug("bid and ask (baa): %s",baa)

		document["Realtime ask"]= baa[0].strip()
		document["Realtime bid"]= baa[1].strip()

		# Find time and date
		timeanddate = soup.findAll('td',text='Zeit')[0].parent.findAll(text=re.compile("\d"))
		document["Realtime date"]= timeanddate[0].strip()
		document["Realtime time"]= timeanddate[1].strip()
	except:
		logger.warning("no data for Geld / Brief for asset %s: %s",document["ISIN"],document["Name"])
		document["Realtime date"]= nothing_found
		document["Realtime time"]= nothing_found
		document["Realtime ask"]= nothing_found
		document["Realtime bid"]= nothing_found
	
	# Last Price Xetra & Frankfurt
	try:
		last_price = soup.findAll("b",text="Letzter Preis")[0].parent.parent.findAll("span")
		document["last price Xetra"]=last_price[0].string
		document["last price Frankfurt"]=last_price[1].string
	except:
		logger.warning("no data for Last Price for asset %s: %s",document["ISIN"],document["Name"])
		document["last price Xetra"]= nothing_found
		document["last price Frankfurt"]= nothing_found
		
	try:
		last_date = soup.findAll("span",text="Datum, Zeit")[0].parent.parent.findAll("span")
		document["last price date"]= last_date[1].string
		document["last price time"]= last_date[2].string
	except:
		logger.warning("no data for Last Price Date or Time for asset %s: %s",document["ISIN"],document["Name"])
		document["last price date"]= nothing_found
		document["last price time"]= nothing_found
		
	
	# Find data which happens to be in the first row of the tables
	td =  ({"In Millionen Euro":"NAV",
			"Handelsw":"CUR",
			"Anlageklasse":"Asset Class",
			"Auflagedatum":"Launch Date"})
	for key in td:
		try:
			document[td[key]] = _get_column_datavalue_first(soup,key)
		except:
			logger.warning("_get_column_datavalue first: %s not found for asset %s: %s",key,document["ISIN"],document["Name"])
			document[td[key]]=nothing_found	
	
	# Find data which happens NOT to be in the first row of the tables		
	td =  ({"Kategorie":"category",
			"Region/Land":"region/country",
			"Art der Indexabbildung":"replication type",
			"Ertragsverwendung":"use of profits",
			"Produktfamilie":"product family",
			"Gesamtkostenquote":"TER",
			"Max. Spread":"Max. Spread"})
	for key in td:
		try:
			document[td[key]] = _get_column_datavalue(soup,key)
		except:
			logger.warning("_get_column_datavalue: %s not found for asset %s: %s",key,document["ISIN"],document["Name"])
			document[td[key]]=nothing_found	
	
	logger.debug("finished parsing page")
	return document

""" 
inspection of soup shows that for a lot of the data, there are two types of table row classes: 
# ~> "right column-datavalue lastColOfRow"
# ~> "right column-datavalue lastColOfRow first"

The two functions below extract the data for these two types from a given soup
"""

def _get_column_datavalue(soup,name):
	"""Finds all elements with class: right column-datavalue lastColOfRow"""
	return soup.findAll('td',text=re.compile(name))[0].parent.findAll("td",{"class":"right column-datavalue lastColOfRow "})[0].string.strip()

def _get_column_datavalue_first(soup,name):
	"""Finds all elements with class: right column-datavalue lastColOfRow first"""
	return soup.findAll('td',text=re.compile(name))[0].parent.findAll("td",{"class":"right column-datavalue lastColOfRow first"})[0].string.strip()
	
def get_dict_of_all_etfs():
	"""returns a dictionary containing a list of etfs listed online at Deutsche Boerse"""
	logger = logging.getLogger(__name__)
	etfs ={}
	ext = ({
			"aktien_laender_long":"1111",
			"aktien_regionen_long":"1211",
			"aktien_sektoren_long":"1311",
			"aktien_strategien_long":"1411",
			"renten_geldmarkt":"2111",
			"renten_pfandbriefe":"2211",
			"renten_staatsanleihen":"2311",
			"renten_unternehmensanleihen":"2411",
			"renten_sonstige":"2511",
			"rohstoffe_long":"3111"
			})
	base_url = "http://www.boerse-frankfurt.de/de/etfs/etfs+indexfonds"

	for key in ext:
		url	 = base_url + "#" + ext[key]
		logger.debug("Asset class: %s",key)
		html = _get_html_list_of_etfs(url)
		etfs.update(_parse_html_list_of_etfs(html))
	return etfs

def _get_html_list_of_etfs(URL):
	"""Downloads the source of a web page with selenium"""
	logger = logging.getLogger(__name__)
	browser = webdriver.Firefox()
	browser.implicitly_wait(10);
	browser.get(URL)
	time.sleep(1)
	html = browser.page_source	
	browser.quit()
	return html

def _parse_html_list_of_etfs(html):
	"""Scraps ISINs and Names out of the downloaded html from Deutsche Boerse"""
	logger = logging.getLogger(__name__)
	soup = BeautifulSoup(html)
	etfs={}
	etfs_raw = soup.findAll("td",{"class":"column-name"})
	logger.debug("all td-tags of class column-name %s",etfs_raw)
	for element in etfs_raw:
		try:
			etf=element.findAll(text=True)
			etfs.update({etf[0]:etf[1]})
		except:
			logger.warning("one or more entries could not be parsed")
			next
	return(etfs)
	
if __name__ == "__main__":
	print(pprint.pformat(get(["etf123","eunm"])))