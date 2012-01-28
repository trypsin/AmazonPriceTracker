import bottlenose, smtplib
from cStringIO import StringIO
from xml.etree.ElementTree import ElementTree
import sqlite3
from datetime import datetime, tzinfo
from time import time, sleep
from email.mime.text import MIMEText
import re
from urllib2 import build_opener
import traceback, sys
from BeautifulSoup import BeautifulSoup


amazon_info = open ('amazon.cfg','rU').readlines()
access_key_id=amazon_info[0].split('=')[1].strip()
secret_access_key=amazon_info[1].split('=')[1].strip()
associate_tag=amazon_info[2].split('=')[1].strip()


user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:8.0.1) \
                  Gecko/20100101 Firefox/8.0.1'
panics=0
amazon = bottlenose.Amazon(access_key_id, secret_access_key, associate_tag)

def GetDetails(ids,db):

    responses=[]
    start = time()
    for ID in ids:
        #print ID
        request_time = time()-start
        if request_time<1:
            sleep(1-request_time)
            #print "sleeping "+str(1-request_time)

        tree = ElementTree()

        tree.parse(StringIO(amazon.ItemLookup(ItemId=ID,ResponseGroup="OfferFull,ItemAttributes",Condition="New")))

        namespace = tree.getroot().tag[:tree.getroot().tag.find("}")+1]

        start=time()
        if len([t for t in tree.iter(namespace+"Errors")])>0:
            print "item missing or other error"
            pass
        if [t for t in tree.iter(namespace+'TotalOffers')][0].text=='0':
            print "no offers for item "+ID
            pass
        else:
            #
            offers_url = [t for t in tree.iter(namespace+'MoreOffersUrl')][0].text

            url = [t for t in tree.iter(namespace+'DetailPageURL')][0].text
            title = [t for t in tree.iter(namespace+'Title')][0].text
            if len([t for t in tree.iter(namespace+'Merchant')]) > 0:
                merchant = list([t for t in tree.iter(namespace+'Merchant')][0])[0].text
            else:
                merchant = ''
            try:
                price, shipping_price = soupThePrices(offers_url)
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                y=traceback.format_exception(exc_type, exc_value, exc_traceback)
                price =  float(list([t for t in tree.iter(namespace+"Price")][0])[0].text)/100.0
                if merchant == "Amazon.com":
                    shipping_price = 0
                else:
                    shipping_price = '???'

            if merchant == "Amazon.com":
                prime = True
            else:
                prime = False

            data = {'Title':title,'Price':price,'URL':url,'ID':ID,'Shipping':shipping_price,'Prime': prime, 'SS': getSS(url)}


            responses.append(data)

    responses.sort(key=lambda student: student['Price'])


    return responses

def HTMLGen(outputname,templatename,details,ordered=False):
    if panics>15:
        panic("SS scraping has died",'')
    #server.quit()
    if not ordered: ordered=details.keys()
    output = open(outputname,'w')
    template = open(templatename,'r').read().split("###")
    output.write(template[0])
    #csscodes=[]
    for key in details.keys():
        row = details[key]
        for i in row:
            i['LinkCode']=BuildLinkCode(i,0)
            #csscodes.append(i['csscode'])
    #for c in csscodes:
    #	output.write(c)
    output.write(template[1])

    for key in ordered:
        row = details[key]
        output.write('<h3><a href="#">Prices for '+key+'</a></h3>\n<div>')
        for i in row:
            output.write(i['LinkCode'])
        output.write('</div>')
    output.write(template[2])
    output.write('<p>Updated '+ datetime.now().strftime("%A, %d %B. %Y %I:%M%p")+' Eastern Time</p>\n')
    output.write(template[3])


    output.close()

def BuildLinkCode(protein,ss=False,giveThanks=False):

    ss=protein['SS']

    if ss:
        linkcode='<b><a class="thumbnail" href="'+protein['URL']+'">'+\
                 "%0.2f" % (protein['Price'])+' - '+protein['Title']+\
                 '<span><img src="http://charts.camelcamelcamel.com/us/'+protein['ID']+\
                 '/amazon.png?force=1&zero=0&w=500&h=350&desired=false&ilt=1"></span></a></b><br />\n'
    else:
        linkcode='<a class="thumbnail" href="'+protein['URL']+'">'+\
                 "%0.2f" % (protein['Price'])+\
                 ' - '+protein['Title']+'<span><img src="http://charts.camelcamelcamel.com/us/'+\
                 protein['ID']+\
                 '/amazon.png?force=1&zero=0&w=500&h=350&desired=false&ilt=1"></span></a><br />\n'

    return linkcode

def soupThePrices(url):

    opener = build_opener()
    opener.addheaders=[('User-agent',user_agent)]

    soup = BeautifulSoup(bs_preprocess(opener.open(url).read()))

    offers = soup.findAll('span',{'class':'price'})
    prices = [float(t.text.strip('$ ')) for t in offers]
    shipping_prices = [getShippingPrice(t) for t in offers]
    total_prices = []
    lowest_index = 0
    for i in range(len(prices)):
        price=prices[i]
        shipping_price=shipping_prices[i]
        total_prices.append(price+shipping_price)
        if total_prices[i]<total_prices[lowest_index]:
            lowest_index=i
    print str(len(total_prices))+' '+str(len(shipping_prices))
    return total_prices[lowest_index], shipping_prices[lowest_index]

def getShippingPrice(offer):
    if len(offer.parent.findAll('span',{'class':'supersaver'})) >0:
        shipping_price = 0.0
    else:
        if hasDigit(offer.parent.findAll('span',{'class':'price_shipping'})[0].text.strip('+ $')):
            shipping_price = float(offer.parent.findAll('span',{'class':'price_shipping'})[0].text.strip('+ $'))
        else:
        #TODO FIX THIS PLEASE
            print "Didn't find shipping price"
            shipping_price = 0.0
    return shipping_price

def bs_preprocess(html):
    """remove distracting whitespaces and newline characters"""
    pat = re.compile('(^[\s]+)|([\s]+$)', re.MULTILINE)
    html = re.sub(pat, '', html)       # remove leading and trailing whitespaces
    html = re.sub('\n', ' ', html)     # convert newlines to spaces
                                       # this preserves newline delimiters
    html = re.sub('[\s]+<', '<', html) # remove whitespaces before opening tags
    html = re.sub('>[\s]+', '>', html) # remove whitespaces after closing tags
    return html


def getSS(url):
    global panics
    opener = build_opener()
    opener.addheaders=[('User-agent',user_agent)]

    soup = BeautifulSoup(bs_preprocess(opener.open(url).read()))
    try:
        discounttext= soup.findAll('span',{'class':'sns-discounted-price'})
        discount=discounttext[0].text
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        y=traceback.format_exception(exc_type, exc_value, exc_traceback)
        discount=''
    try:
        discount2 =soup.findAll('span',{'class':'sns-discount'})[0].text
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        y=traceback.format_exception(exc_type, exc_value, exc_traceback)
        discount2=''

    return hasDigit(discount) or hasDigit(discount2)

def hasDigit(s):
    for c in s:
        if c.isdigit():
            return True
    return False