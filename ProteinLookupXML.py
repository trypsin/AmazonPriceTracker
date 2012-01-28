import pricelookupxml as pl
import csv


details = {}
order = []
db="db/test2.db"
idReader = csv.reader(open('ItemIDs.csv', 'rU'))

for row in idReader:

    while row.count(''):
        row.remove('')
    rdetails = pl.GetDetails(row[1:],db)

    order.append(row[0])    
    details[row[0]]=rdetails
output='../../www/protein/protein_prices.html'

template='templatepy3.html'

pl.HTMLGen(output,template,details,order)
