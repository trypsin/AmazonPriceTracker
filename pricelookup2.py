import bottlenose, smtplib
import simplejson as json
import sqlite3
from datetime import datetime, tzinfo
from time import time, sleep
from email.mime.text import MIMEText
access_key_id='AKIAJ5QNNFS7WXH3Q5AQ'
secret_access_key='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'
associate_tag='trypsin-20'

amazon = bottlenose.Amazon(access_key_id, secret_access_key, associate_tag)
fromaddr = "proteintracker@gmail.com"
toaddrs = ""
LOGIN = "proteintracker@gmail.com"
PASSWORD = "wakkawakka1"
server = smtplib.SMTP('smtp.gmail.com',587)
server.ehlo()
server.starttls()
server.login(LOGIN,PASSWORD)

def GetDetails(ids,db):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    responses=[]
    start = time()
    for ID in ids:
        request_time = time()-start
        if request_time<1:
            sleep(1-request_time)
            #print "sleeping "+str(1-request_time)
        response = json.loads(amazon.ItemLookup(ItemId=ID,
         ResponseGroup="OfferListings,ItemAttributes",
         Style="http://xml2json-xslt.googlecode.com/svn/trunk/xml2json.xslt"))
        start=time()
        if "Errors" in response['ItemLookupResponse']['Items']['Request']:
            print "item missing"
        else:
            item = response['ItemLookupResponse']['Items']['Item']
            price = item['Offers']['Offer']['OfferListing']['Price']['Amount']
            url = item['DetailPageURL']
            title = item['ItemAttributes']['Title']

            #This section just filters out bits of the protein names I don't like
            """if title.find('Standard, ') != -1:
                title = title[title.find('Standard,')+10:]
            if title.find('Protein, ') != -1:
                title = title[title.find('Protein,')+9:]
            if title.find('Whey, ') != -1:
                title = title[title.find('Whey,')+6:]"""

            data = {'Title':title,'Price':price,'URL':url,'ID':ID}

            #print data


            responses.append(data)
            email(data,c)

    responses.sort(key=lambda student: student['Price'])
    conn.commit()
    c.close()

    return responses

def HTMLGen(outputname,templatename,details,ordered=False):
    server.quit()
    if not ordered: ordered=details.keys()
    output = open(outputname,'w')
    template = open(templatename,'r').read().split("###")
    output.write(template[0])
    csscodes=[]
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

def BuildLinkCode(i,ss=False,giveThanks=False):
    if ss:
        linkcode='<i> </i><a class="aa" href="#" name="'+i['ID']+'">Track!</a><em> - </em>\n<a class="thumbnail" href="'+i['URL']+'">'+"%0.2f" % (i['Price']*.01)+' (S&S: '+"%0.2f" % (i['Price']*.0085)+') - '+i['Title']+'<span><img src="http://charts.camelcamelcamel.com/us/'+i['ID']+'/amazon.png?force=1&zero=0&w=500&h=350&desired=false&ilt=1"></span></a><br />\n'
    else:
        linkcode='<i> </i><a class="aa" href="#" name="'+i['ID']+'">Track!</a><em> - </em>\n<a class="thumbnail" href="'+i['URL']+'">'+"%0.2f" % (i['Price']*.01)+' - '+i['Title']+'<span><img src="http://charts.camelcamelcamel.com/us/'+i['ID']+'/amazon.png?force=1&zero=0&w=500&h=350&desired=false&ilt=1"></span></a><br />\n'
    if giveThanks:
        return ReplaceUrl(linkcode)
    return linkcode

def ReplaceUrl(url):
    return url[:url.index('SubscriptionId%3D')+17]+'AKIAJ5QNNFS7WXH3Q5AQ&tag=trypsin-20&linkCode=xm2'+url[url.index('%26creative%3D'):]

def email(data,c):
    c.execute('select * from Goons where asin="'+data['ID']+'"')
    for goon in c:
        if data['Price']<(goon[2]*100):
            sendEmail(goon,data)
            c.execute('DELETE FROM Goons where email="'+goon[0]+'" AND asin="'+goon[1]+'"')

def sendEmail(goon,data):
    print "emailing "+goon[0]+" about "+goon[1]
    msg = MIMEText("The price went down for <a href='"+data['URL']+"'>"+data['Title']+"</a> to $"+"%0.2f" % (data['Price']*.01),'html' )
    msg['Subject'] = "Protein price change"
    toaddrs=goon[0]
    msg['From'] = fromaddr
    msg['To'] = toaddrs


    server.sendmail(fromaddr,toaddrs,msg.as_string())




