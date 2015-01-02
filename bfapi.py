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
	logger = logging.getLogger(__name__)
	ls_bidandask = []
	logger.debug("data type of isin is %s",type(isin))
	if type(isin) is not list:
		isin = [isin]
		
	for asset in isin:
		try:
			if type(asset) is str or type(asset) is unicode:
				page = _get_asset_page(asset)
				bidandask = _parse_asset_page(page)
				bidandask["exchange"] = "Frankfurt"
				logger.debug("Result from parser:\n%s" % pprint.pformat(bidandask))
				ls_bidandask.append(bidandask)
			else:
				logger.error('string or list of strings expected as input')
				return ls_bidandask
		except:
			logger.error(asset + " SKIPPED!!")
			next
	return ls_bidandask

def _get_asset_page(isin):
	logger = logging.getLogger(__name__)
	logger.info("get page for isin %s",isin)
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
	logger = logging.getLogger(__name__)
	nothing_found = "no data" # this value will be set whenever no value is found on the product page
	logger.debug("start parsing page ...")
	soup = BeautifulSoup(page)
	
	bidandask={}

	# Find bid and ask
	try:
		baa = soup.findAll('td',text='Geld / Brief')[0].parent.findAll(text=re.compile('\d{1,3}[,]\d{2}'))
		logger.debug("bid and ask (baa): %s",baa)

		bidandask["ask"]= baa[0].strip()
		bidandask["bid"]= baa[1].strip()

		# Find time and date
		timeanddate = soup.findAll('td',text='Zeit')[0].parent.findAll(text=re.compile("\d"))
		bidandask["date"]= timeanddate[0].strip()
		bidandask["time"]= timeanddate[1].strip()
	except:
		logger.warning("no data for Geld / Brief")
		bidandask["date"]= nothing_found
		bidandask["time"]= nothing_found
		bidandask["ask"]= nothing_found
		bidandask["bid"]= nothing_found
	
	# Find ISIN
	try:
		ISIN = soup.findAll("h4")[0]
		pattern=re.compile("[A-z]{2}\S{10}")
		ISIN = pattern.search(str(ISIN)).group(0)
		bidandask["ISIN"] = unicode(ISIN)
	except:
		logger.warning("ISIN not found")
		bidandask["ISIN"] = nothing_found
		
	# Find Name
	try: 
		bidandask["Name"] = soup.findAll("h1",{"class":None})[0].string	
	except:
		logger.warning("Name for %s not found",bidandask["ISIN"])
		bidandask["Name"] = nothing_found
	
	# Find data which happens to be in the first row of the tables
	td =  ({"In Millionen Euro":"NAV",
			"Handelsw":"CUR",
			"Anlageklasse":"Asset Class",
			"Auflagedatum":"Launch Date"})
	for key in td:
		try:
			bidandask[td[key]] = _get_column_datavalue_first(soup,key)
		except:
			logger.warning("_get_column_datavalue first: %s not found",key)
			bidandask[td[key]]=nothing_found	
	
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
			bidandask[td[key]] = _get_column_datavalue(soup,key)
		except:
			logger.warning("_get_column_datavalue: %s not found",key)
			bidandask[td[key]]=nothing_found	
	
	logger.debug("finished parsing page")
	return bidandask

# inspection of soup shows that there are two types of table row classes: 
# (1) right column-datavalue lastColOfRow
# (2) right column-datavalue lastColOfRow first

# (1) right column-datavalue lastColOfRow
def _get_column_datavalue(soup,name):
	return soup.findAll('td',text=re.compile(name))[0].parent.findAll("td",{"class":"right column-datavalue lastColOfRow "})[0].string.strip()

# (2) right column-datavalue lastColOfRow first
def _get_column_datavalue_first(soup,name):
	return soup.findAll('td',text=re.compile(name))[0].parent.findAll("td",{"class":"right column-datavalue lastColOfRow first"})[0].string.strip()
	
def get_dict_of_all_etfs():
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
	logger = logging.getLogger(__name__)
	browser = webdriver.Firefox()
	browser.implicitly_wait(10);
	browser.get(URL)
	time.sleep(1)
	html = browser.page_source	
	browser.quit()
	return html

def _parse_html_list_of_etfs(html):
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

	