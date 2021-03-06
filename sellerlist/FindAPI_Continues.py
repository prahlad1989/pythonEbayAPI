import copy
import concurrent.futures
import getpass
import sys
from sys import exc_info

from ebaysdk.finding import Connection as Finding
from ebaysdk.shopping import Connection as Shopping
import logging

import threading
import datetime
import time
import gspread.client
from oauth2client.service_account import ServiceAccountCredentials

thread_local=threading.local()

logging.basicConfig(filename="FindAPI.log",

                   filemode='w')
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
# Creating an object
logger = logging.getLogger()
# Setting the threshold of logger to DEBUG
logger.setLevel(logging.DEBUG)

def __updateToGSheet(data ,error=None,sellerIdFromSheet="",noOfMonths="0"):
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("ebayPractice-f9627f3e653b.json", scope)
    client = gspread.authorize(creds)

    outputSheet = client.open("OrderInformationsWork").worksheet("Output")
    allRowsValues = [
                     ['','','','Seller Details : '+str(sellerIdFromSheet)+' For '+str(noOfMonths)+' Month(s)','','','Sheet Last Updated at: '+str(datetime.datetime.now())+' by '+getpass.getuser()],
                     [],
                     ['Title', 'Price', 'Watch','Sold', 'CategoryID','Duration', 'Viewed','TimeLeft before Listing Ends' ]]

    if (error is not None):
        errors = ['Failed to update sheet with reason : ', str(error), ' at ', str(datetime.datetime.now())]
        logger.exception(f"error with {error}")
        outputSheet.clear()
        outputSheet.append_row(errors)
        raise Exception(error)
        return

    #allRowsValues.append(eachRow1)
    for eachItem in data:
        #print(eachItem)
        watchCont=0 if eachItem['listingInfo'].get('watchCount') is None else int(eachItem['listingInfo']['watchCount'])
        QuantitySold=0 if eachItem.get(''
                                       '') is None else int(eachItem['QuantitySold'])
        HitCount=0 if eachItem.get('HitCount') is None else int(eachItem['HitCount'])
        eachRow = [eachItem.get('title'), float(eachItem['sellingStatus']['currentPrice']['value']),
                   watchCont,
                   QuantitySold,
                   int(eachItem['primaryCategory']['categoryId']),
                   int(eachItem.get('DurationCalc'))
            ,HitCount, eachItem['sellingStatus']['timeLeft']]
        allRowsValues.append(eachRow)

    outputSheet.clear()
    outputSheet.append_rows(allRowsValues)

    #For starting heading
    outputSheet.format("A1:F1", {"textFormat": {"bold": True, "fontSize": 12, "foregroundColor": {
        "red": 1.0,
        "green": 0.0,
        "blue": 0.0
    }}})

    #for each attribute
    outputSheet.format("A3:I3", {"textFormat": {"bold": True, "fontSize": 12, "foregroundColor": {
        "red": 1.0,
        "green": 0.0,
        "blue": 0.0
    }}})
    #to print timestamp at right side of sheet
    outputSheet.format("I1:M1", {"textFormat": {"bold": False, "fontSize": 12, "foregroundColor": {
        "red": 0.0,
        "green": 1.0,
        "blue": 0.0
    }}})#ok
    # reset format

    outputSheet.merge_cells('D1:F1')
    outputSheet.merge_cells('G1:I1')

    inputSheet=client.open("OrderInformationsWork").worksheet("Input")

    inputSheet.format("B4:B4", {"backgroundColor": {
    "red": 1.0,
    "green": 0.8,
    "blue": 0.3
    },"textFormat": {"bold": False, "fontSize": 12}})
    inputSheet.update_cell(4,2,"")
    # clearing input value so that script will not process repeatedly.

def get_session():
    if not hasattr(thread_local, "api"):
        thread_local.api = Shopping(config_file=None, domain='open.api.ebay.com',
                                    appid="SatyaPra-MyEBPrac-PRD-abce464fb-dd2ae5fe",
                                    devid="6c042b69-e90f-4897-9045-060858248665",
                                    certid="PRD-bce464fbd03b-273a-4416-a299-7d41"
                                    )
    return thread_local.api


def getFromSheet():
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("ebayPractice-f9627f3e653b.json", scope)

    client = gspread.authorize(creds)

    input = client.open("OrderInformationsWork").worksheet("Input")
    sellerIdFromSheet = input.cell(4,2).value.strip()
    noOfMonths = int(input.cell(5,2).value)
    return (sellerIdFromSheet,noOfMonths)


thread_local_FindingApi_Session=threading.local()
def __getFindingApiSession():
    if not hasattr(thread_local_FindingApi_Session,"api"):
        thread_local_FindingApi_Session.api=Finding(config_file=None, domain='svcs.ebay.com', appid="SatyaPra-MyEBPrac-PRD-abce464fb-dd2ae5fe",
                  devid="6c042b69-e90f-4897-9045-060858248665",
                  certid="PRD-bce464fbd03b-273a-4416-a299-7d41"
                  )
    return thread_local_FindingApi_Session.api

def __retrieveFromSecondPage(inputObj):
    api=__getFindingApiSession()
    response = api.execute('findItemsAdvanced', inputObj).dict()
    #logger.debug(f" thread name {threading.currentThread().name } result is : {response}")
    return response


def main():

        try:
            ebayFunction()
            time.sleep(100)
        except:logger.exception("Exception at processing")

def ebayFunction():
    api = Finding(config_file=None, domain='svcs.ebay.com', appid="SatyaPra-MyEBPrac-PRD-abce464fb-dd2ae5fe",
                  devid="6c042b69-e90f-4897-9045-060858248665",
                  certid="PRD-bce464fbd03b-273a-4416-a299-7d41"
                  )

    items = list()

    inputObj = {
        "itemFilter": {
            "name": "Seller",
            "value": ""
        },
        "OutputSelector": [
            "Title",
            "itemId",
            "ViewItemURL",
            "SellingStatus",
            "ListingDuration",
            "listingInfo"
            "StartTime",
            "EndTime",
            "WatchCount",
            "ItemsPerPage",
            "PrimaryCategory",
            "HasMoreItems",
            "PageNumber",
            "ReturnedItemCountActual",
            "PaginationResult"
        ],
        "StartTimeFrom": "",
        "StartTimeTo": "",
        "IncludeWatchCount": "true",

        "paginationInput": {
            "entriesPerPage": "100",
            "pageNumber": "0"

        }
    }


    startDateTo = datetime.datetime.now()
    startDateFrom = startDateTo - datetime.timedelta(15)
    sellerIdFromSheet, noOfMonths = getFromSheet();
    logger.debug(f"seller id fro sheet  {sellerIdFromSheet}")
    logger.debug(f"no of months {str(noOfMonths)}")
    if sellerIdFromSheet is not None and len(sellerIdFromSheet) > 0:

        inputObj["itemFilter"]["value"] = sellerIdFromSheet
        # queryRepeats = int(noOfMonths / 3)
        # if (noOfMonths == 1):  # one month only
        #     queryRepeats = queryRepeats + 1
        #     startDateFrom = startDateTo - datetime.timedelta(30)
        # elif (queryRepeats == 4):  # need to include (4*90) obvious and 6 days for a year
        #     queryRepeats = 5
        tic=time.perf_counter()
        for i in range(int(noOfMonths*2)):
            inputObj["StartTimeTo"] = startDateTo
            inputObj["StartTimeFrom"] = startDateFrom
            inputObj["paginationInput"]["pageNumber"] = 1
            logger.debug(f"iteration number {i}")
            logger.debug(f"sad{inputObj['StartTimeTo']} and {inputObj['StartTimeFrom']}")
            response = api.execute('findItemsAdvanced', inputObj)
            #print(response)
            response=response.dict()
            #print(inputObj)

            if response.get("searchResult") is None:
                logger.debug(f"no result at i {i}")
                break
            elif response.get("searchResult").get("item") is None:
                logger.debug(f"no result:at {i}")
                break
            #print(response["searchResult"])
            currentItems = response["searchResult"]["item"]
            items.extend(currentItems)
                # print("lenght of items , ", len(items))
                # print("page number is ", response["PageNumber"])
                # print("remaining pages", response["PaginationResult"])
                # print("has more number ", response["HasMoreItems"])
            remainingPages = int(response["paginationOutput"]["totalPages"]) - int(
                    response["paginationOutput"]["pageNumber"])

            if remainingPages == 0:
                break
            logger.debug(f"remaining pages: {remainingPages}")
            # query allows only upto max 100 pages
            remainingPages=min(99,remainingPages)
            multiThreadInputObjects=[copy.deepcopy(inputObj) for _ in range(remainingPages)]
            for i in range(remainingPages):
                multiThreadInputObjects[i]["paginationInput"]["pageNumber"]=i+2
            #logger.debug(multiThreadInputObjects)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(5,remainingPages/20)) as executor:
                searchResults=[]
                searchResults=executor.map(__retrieveFromSecondPage,multiThreadInputObjects)
                logger.debug("underr multithread")
                for searchResult in searchResults:

                    items.extend(searchResult["searchResult"]["item"])
                executor.shutdown()

            startDateFrom = startDateFrom - datetime.timedelta(15)
            startDateTo = startDateTo - datetime.timedelta(15)



        for item in items:
            # print("start time and ",item['listingInfo']['startTime']," end time; ", item['listingInfo']['endTime'])
            startTime = datetime.datetime.strptime(item['listingInfo']['startTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
            endTime = datetime.datetime.strptime(item['listingInfo']['endTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
            #item['DurationCalc']= (endTime.__sub__(startTime)).days
            item['DurationCalc'] = (endTime.__sub__(startTime)).days
        toc=time.perf_counter()
        logger.debug(f"search took {toc-tic} time with items: {len(items)}")
        logger.debug("now adding details like hit count and quantity sold")
        items=__getGood(items)

        __updateToGSheet(items, None, sellerIdFromSheet, noOfMonths)
        logger.debug("completed")

def __getGood(items):
    logger.debug("shopping")
    itemIdSet = set(map(lambda x: x['itemId'], items))
    noDuplicates = list()
    print("set size is ",len(itemIdSet))
    for x in items:
        if x['itemId'] in itemIdSet:
            itemIdSet.remove(x['itemId'])
            noDuplicates.append(x)

    logger.debug(f"no of duplicates: {len(items)-len(noDuplicates)}")
    items = noDuplicates
    inputObj = {"ItemID": [], "IncludeSelector": "Details"}
    inputObjects = []
    j = 0
    _ = 0
    for item in items:
        # print("start time and ",item['listingInfo']['startTime']," end time; ", item['listingInfo']['endTime'])
        startTime = datetime.datetime.strptime(item['listingInfo']['startTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
        endTime = datetime.datetime.strptime(item['listingInfo']['endTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
        item['DurationCalc'] = (endTime.__sub__(startTime)).days
        item['QuantitySold']=0
        item['HitCount']=0
        logger.debug(item['itemId'])
    tic = time.perf_counter()
    while _ < (len(items)):
        logger.debug(f"{_} out of {len(items)}")
        if _ + 20 > len(items):
            j = len(items)
        else:
            j = _ + 20
        inputObj["ItemID"] = list(map(lambda x: x['itemId'], items[_:j]))

        # print("before adding sold, hitcount ",items[_:j])
        try:
            response = get_session().execute('GetMultipleItems', inputObj).dict()
        # print("response after executing multiple api call: ",response)

        except ConnectionError as err:
            logger.debug("got exception while getmultipleitems",exc_info=True)
            print("exception at connection",err)
            print(err.response().dict())
            break
        except:
            print("exception at connection")
            logger.exception("got exeption not ConnectionError")
            break
        else:
            if type(response.get('Item'))==list:
                for i in range(len(response['Item'])):
                    items[_ + i]['QuantitySold'] = response['Item'][i].get('QuantitySold')
                    items[_ + i]['HitCount'] = response['Item'][i].get('HitCount')
            elif type(response.get('Item')) == dict:
                    print(items[_:j])
                    print(response['Item'])
                    items[_]['QuantitySold'] = response['Item'].get('QuantitySold')
                    items[_]['HitCount'] = response['Item'].get('HitCount')
            else:
                print("Din't get any response due to time out.")
                print(response.get('Errors'))
                break

        _ = j

        # print("remaining items to process ",len(items)-i)
    # correcting duration to start and end dates diff
        # print("duration is , ",item['DurationCalc'])
    toc = time.perf_counter()
    logger.debug(f"stopwatch: {toc-tic}")
    #logger.debug(f"lengthof input {len(inputObjects)}")
    return items


if __name__ == "__main__":
    main()