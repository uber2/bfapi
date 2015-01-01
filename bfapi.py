import re
import mechanize
from bs4 import BeautifulSoup
import urllib2
from selenium import webdriver
import time
from bs4 import SoupStrainer
import logging
import json

logging.basicConfig(level=logging.ERROR)

def get(isin):
	logger = logging.getLogger(__name__)
	ls_bidandask = []
	
	if type(isin) is not list:
		if type(isin) is str:
			isin = [isin]
		else:
			logger.error("string or list of strings expected as input")
			return
	for asset in isin:
		try:
			if type(asset) is str or type(asset) is unicode:
				logger.debug("Asset: %s of type %s", asset, type(asset))
				page = _get_asset_page(asset)
				bidandask = _parse_asset_page(page)
				bidandask["exchange"] = "Frankfurt"
				logger.debug("bidandask: %s" % bidandask)
				ls_bidandask.append(bidandask)
			else:
				logger.error('string or list of strings expected as input')
				return ls_bidandask
		except:
			logger.error(asset + " SKIPPED!!")
			next
	return ls_bidandask

def _get_asset_page(isin):
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
	
def asset_exists(isin):
	page = _get_asset_page(isin)
	soup = BeautifulSoup(page)
	if not len(soup.findAll('h1',text="Suchergebnisse")) == 0:
		return False
	else:
		# Find ISIN
		ISIN = soup.findAll("h4")[0]
		pattern=re.compile("[A-z]{2}\S{10}")
		ISIN = pattern.search(str(ISIN)).group(0)
		logging.info("Asset_exists found the following ISIN: %s",ISIN)
		return ISIN

def _parse_asset_page(page):
	nothing_found = "no data"
	logger = logging.getLogger(__name__)
	logger.debug("start parsing page")
	soup = BeautifulSoup(page)
	
	bidandask={}
	

		# Find bid and ask
	try:
		baa = soup.findAll('td',text='Geld / Brief')[0].parent.findAll(text=re.compile('\d{1,3}[,]\d{2}'))
		logging.debug("bid and ask (baa): %s",baa)

		bidandask["ask"]= baa[0].strip()
		bidandask["bid"]= baa[1].strip()

		# Find time and date
		timeanddate = soup.findAll('td',text='Zeit')[0].parent.findAll(text=re.compile("\d"))
		
		bidandask["date"]= timeanddate[0].strip()
		bidandask["time"]= timeanddate[1].strip()
	except:
		bidandask["date"]= nothing_found
		bidandask["time"]= nothing_found
		bidandask["ask"]= nothing_found
		bidandask["bid"]= nothing_found
		
	# Find TER
	try:
		TER=soup.findAll('td',text=re.compile('Gesamtkostenquote'))[0].parent.findAll(text=re.compile("\d{1,2}[,]\d{1,2}%"))
		bidandask["TER"]= TER[0].strip()
	except:
		bidandask["TER"]= nothing_found
	
	# Find NAV
	try:
		NAV= soup.findAll('td',text=re.compile('In Millionen Euro'))[0].parent.findAll(text=re.compile("\d"))
		bidandask["NAV"]= NAV[0].strip()
	except:
		bidandask["NAV"]= nothing_found
	
	# Find CUR
	try:
		CUR=soup.findAll('td',text=re.compile('Handelsw.'))[0].parent.findAll(text=re.compile("[A-Z]{2,3}"))
		bidandask["CUR"]= CUR[0].strip()
	except:
		bidandask["CUR"]= nothing_found
	
	# Find ISIN
	try:
		ISIN = soup.findAll("h4")[0]
		pattern=re.compile("[A-z]{2}\S{10}")
		ISIN = pattern.search(str(ISIN)).group(0)
		bidandask["ISIN"] = unicode(ISIN)
	except:
		bidandask["ISIN"] = nothing_found
		
	# Find Name
	try: 
		Name = soup.findAll("h1")[1].findAll(text=True)[0]
		bidandask["Name"] = Name.strip()	
	except:
		bidandask["Name"] = nothing_found
	
	# Find Max.Spread
	try:
		max_Spread = soup.findAll('td',text=re.compile('Max. Spread'))[0].parent.findAll(text=re.compile("\d{1,2}[,]\d{1,2}%"))
		bidandask["Max. Spread"]= max_Spread[0].strip()
	except:
		bidandask["Max. Spread"] = nothing_found
		
	# Product Family
	try:
		product_family = soup.findAll('td',text=re.compile('Produktfamilie'))[0].parent.findAll(text=True)
		bidandask["product_family"]= product_family[3].strip()	
	except:
		bidandask["product_family"]=nothing_found
	
	# Ertragsverwendung
	try:
		ertragsverwendung = soup.findAll('td',text=re.compile('Ertragsverwendung'))[0].parent.findAll(text=True)
		bidandask["Ertragsverwendung"]= ertragsverwendung[3].strip()		
	except:
		bidandask["Ertragsverwendung"]= nothing_found
		
	# Art der Indexabbildung
	try:
		art_der_indexabbildung = soup.findAll('td',text=re.compile('Art der Indexabbildung'))[0].parent.findAll(text=True)
		bidandask["Art der Indexabbildung"]= art_der_indexabbildung[3].strip()
	except:
		bidandask["Art der Indexabbildung"]=nothing_found	
	
	logger.debug("end parsing page")
	return bidandask
	
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
			logger.error("one or more entries could not be parsed")
			next
	return(etfs)

	