import praw, re, time, pytz, datetime, math, requests
from dateutil import parser
from nltk import word_tokenize, pos_tag
from datetime import timedelta

##This is mostly same program as redditTimezoneBot.py, but this one searches comments instead of posts.

timezones = {"PST": "PST8PDT", "EST": "EST5EDT", "CEST": "CET",
             "CST": "CST6CDT", "CT": "CST6CDT", "CDT": "CST6CDT", "BST": "Europe/London", "ET": "EST5EDT",
             "EDT": "EST5EDT", "PT": "PST8PDT", "PDT": "PST8PDT", "MST": "MST7MDT", "MDT": "MST7MDT",
             "UTC": "UTC", "GMT": "Etc/GMT", "KST": "Japan", "GMT+0": "Etc/GMT+0", "GMT+1": "Etc/GMT+1",
             "GMT+10": "Etc/GMT+10", "GMT+11": "Etc/GMT+11", "GMT+12": "Etc/GMT+12", "GMT+2": "Etc/GMT+2",
             "GMT+3": "Etc/GMT+3","GMT+4": "Etc/GMT+4","GMT+5": "Etc/GMT+5","GMT+6": "Etc/GMT+6",
             "GMT+7": "Etc/GMT+7","GMT+8": "Etc/GMT+8","GMT+9": "Etc/GMT+9","GMT-0": "Etc/GMT-0",
             "GMT-1": "Etc/GMT-1","GMT-10": "Etc/GMT-10","GMT-11": "Etc/GMT-11","GMT-12": "Etc/GMT-12",
             "GMT-13": "Etc/GMT-13","GMT-14": "Etc/GMT-14","GMT-2": "Etc/GMT-2","GMT-3": "Etc/GMT-3",
             "GMT-4": "Etc/GMT-4","GMT-5": "Etc/GMT-5","GMT-6": "Etc/GMT-6","GMT-7": "Etc/GMT-7",
             "GMT-8": "Etc/GMT-8","GMT-9": "Etc/GMT-9","GMT+0": "Etc/GMT0", "EASTERN": "EST5EDT",
             "UK": "Europe/London", "CET": "CET"}

suomi = pytz.timezone("Europe/Helsinki")
##suomi = pytz.timezone("UTC")

reddit = praw.Reddit(client_id="",
                     client_secret="",
                     password="",
                     user_agent="",
                     username="")

findTimeAndZonePMAM = r'(\d+:\d+|\d+)( |)(PM|AM|pm|am) \w+'
findTimeAndZone = r'\d+:\d+( |,|.)( |)\w+( |)( |\+| |\-)(\d+|)'

findDate1 = r"(may|june|july)( |,|)\d+(th|st| |)"
findDate2 = r"\d+/\d+/\d+"
findDate3 = r"\d\d(th|st| |)( |,|)( |)(may|june)"

findDateRs = [findDate1, findDate2, findDate3]

dontPostSubreddits = ["/r/MHOCMP/", "/r/buildapc", "/r/Brewers", "/r/Reds",
                      "/r/OaklandAthletics", "/r/Nationals", "/r/buccos",
                      "/r/azdiamondbacks", "/r/redsox", "/r/LaGalaxy",
                      "/r/orioles", "/r/CHICubs", "/r/aviationmaintenance/",
                      "/r/angelsbaseball"]

weekdays = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
weekdays = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday", 5: "saturday", 6: "sunday", -1: "sunday"}
weekdaysArr = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "tomorrow"]

timeFormatted = ""

def searchComments():
    while True:

        for comment in reddit.subreddit("all").stream.comments():
            
            findBody = re.search(findTimeAndZonePMAM, comment.body)
            
            if not findBody:
                findBody = re.search(findTimeAndZone, comment.body)
            
            if findBody:
                
                found = findBody.group();

                if not userNotMe(comment):
                    continue

                if not getTense(comment.body):
                    continue
                
                try:
                    print("\nTIME: ", found)
                    print("TITLE: ", comment.submission.title)
                    print("URL: ", comment.permalink())
                except UnicodeEncodeError:
                    continue
                
                if any(x in comment.submission.url for x in dontPostSubreddits):
                    continue
                
                if "bot" in comment.author.name:
                    continue
                
                if len(comment.body) > 600:
                    continue
                
                if not happensToday(comment):
                    continue

                if not checkForDates(comment):
                    continue
                
                difference = getTimeDifference(found)

                if difference and difference < 22 and difference > 0.12:
                    print("sendMsg")
                    sendMessage(comment, difference, found)
                    
        time.sleep(0.5)

def checkForDates(comment):

    commBody = comment.body.lower()
    
    ##foundDates = re.search(findDate1, postBody)
    
    for regex in findDateRs:

        foundDates = re.search(regex, commBody)
        if foundDates:
            break

    if foundDates:

        foundDate = foundDates.group()

        try:
            date = parser.parse(foundDate)
            print("FOUND DATE:",foundDate)
        except Exception:
            print("checkDateFailed")
            return True
        
        today = datetime.datetime.now()##date.today()
        tomorrow = today + datetime.timedelta(days=1)
        yesterday = today - datetime.timedelta(days=1)

        hoursAtm = today.hour

        if today.hour > 12:
        
            if date > tomorrow or date <= yesterday:
                return False
            else:
                return True
        else:
            if date > tomorrow or date < yesterday:
                return False
            else:
                return True
            
    else:
        return True


def userNotMe(comment):

    if comment.author.name == "timezone_bot":
        return False
    else:
        return True

def happensToday(comment):

    day = datetime.datetime.today().weekday()
                
    if day == 6:
        ar = [weekdays[day], weekdays[day-1], weekdays[0]]
    else:
        ar = [weekdays[day], weekdays[day-1], weekdays[day+1]]
    a = [x for x in weekdaysArr if x not in ar]

    ##print(a)
    
    if any(x in comment.body.lower() for x in a):
        return False
    if any(x in comment.submission.selftext.lower() for x in a):
        return False
    if any(x in comment.submission.title.lower() for x in a):
        return False
    
    return True
    

def getTimeDifference(found):

    global timeFormatted

    timezone = found.split(" ")[-1]
    print(timezone)
    try:
        zone = pytz.timezone(timezones[timezone.upper()])
    except KeyError:
        return

    try:
        time = parser.parse(found.upper())
    except ValueError:
        return
    time = time.replace(tzinfo=None)
    time = zone.localize(time)
    
    utc = pytz.timezone("UTC")
    time = time.astimezone(utc)

    now = datetime.datetime.now()
    now = suomi.localize(now)
    now = now.astimezone(utc)
    
    diff = (time - now).seconds/3600
    
    print(time)
    print("HOURS: ", diff)
    print(now)

    timeFormatted = time
    
    if (time - now).days > 0:
        time = time - datetime.timedelta(days=1)
        timeFormatted = time
        return diff
    else:
        return diff

##Call with comment body
def getTense(comment):

    text = word_tokenize(comment)
    tagged = pos_tag(text)

    tense = {}
    tense["future"] = len([word for word in tagged if word[1] == "MD"])
    tense["present"] = len([word for word in tagged if word[1] in ["VBP", "VBZ","VBG"]])
    tense["past"] = len([word for word in tagged if word[1] in ["VBD", "VBN"]])

    past = tense["past"]
    present = tense["present"]
    future = tense["future"]

    allT = 0
    for i in tense:
	allT += tense[i]
	    
    if allT == 0:
        return True
    
    pastPer = past / allT
    presentPer = present / allT
    futurePer = future / allT

    if pastPer > 0.7:
        return False
    if presentPer > 0.7:
        return True
    if futurePer > 0.7:
        return True
    if pastPer == presentPer and pastPer > 0.4:
        return False
    
    return True##(tense)

def is_dst(timezone):
    tz = pytz.timezone(timezone)
    now = pytz.utc.localize(datetime.datetime.utcnow())
    return now.astimezone(tz).dst() != timedelta(0)

def sendMessage(comment, difference, found):

    global timeFormatted
    
    endMessage = "\n\n---\n\nI'm a bot, if you found my service helpful please consider upvoting. If you want to send feedback, please send a PM or reply below."
    
    split = math.modf(difference)
    hours = int(split[1])
    
    minutes = math.floor(split[0] * 60)
    timeFormatted = timeFormatted.strftime('%Y-%m-%d %H:%M:%S%z')
    r = requests.post('http://countle.com/createnew/gQOCmuH7H3N_WVfvrjIB0nZULCH2rmr1dQEVYPkxAQg',
                      json={"date": timeFormatted, "foundtime": found, "eventname": comment.submission.title,
                            "redditlink": comment.submission.url})

    token = r.text

    cdUrl = "https://countle.com/" + token

    foundParts = found.split(" ")
    zone = foundParts[-1].upper()
    timezone = timezones[zone]
    if is_dst(timezone):
            timezone = zone.replace("S", "D")

    found = ""
    for i in range(len(foundParts) - 1):
            found += (foundParts[i] + " ")

    found += timezone
    
    if hours == 1:
        hoursS = " hour"
    else:
        hoursS = " hours"

    if hours == 0:
        try:
            comment.reply(found + " happens when this comment is " + str(minutes) + " minutes old.\n\nYou can find the live countdown here: " + cdUrl + endMessage)
        except Exception as e:
            print(e)
            pass
    else:
        if minutes != 0:
            try:
                comment.reply(found + " happens when this comment is " + str(int(hours)) + hoursS + " and " + str(minutes) + " minutes old.\n\nYou can find the live countdown here: " + cdUrl + endMessage)
            except Exception as e:
                print(e)
                pass
        else:
            try:
                comment.reply(found + " happens when this comment is " + str(int(hours)) + hoursS + " old.\n\nYou can find the live countdown here: " + cdUrl + endMessage)
            except Exception as e:
                print(e)
                pass

print(reddit.user.me())
searchComments()
