import praw, re, time, pytz, datetime, math, requests
from dateutil import parser
from datetime import timedelta
from nltk import word_tokenize, pos_tag

##pytz provides hundreds timezones, put don't provide some with the abbreviation like CST is CST6CDT, which is why I created
##  this list containing the most used timezones. Pytz also automatically detects daylight savings etc.
timezones = {"PST": "PST8PDT", "EST": "EST5EDT", "CEST": "CET",
             "CST": "CST6CDT", "CT": "CST6CDT", "CDT": "CST6CDT", "BST": "Europe/London", "ET": "EST5EDT",
             "EDT": "EST5EDT", "ET": "EST5EDT", "PT": "PST8PDT", "PDT": "PST8PDT", "MST": "MST7MDT", "MDT": "MST7MDT",
             "UTC": "UTC", "GMT": "Etc/GMT", "KST": "Japan", "GMT+0": "Etc/GMT+0", "GMT+1": "Etc/GMT+1",
             "GMT+10": "Etc/GMT+10", "GMT+11": "Etc/GMT+11", "GMT+12": "Etc/GMT+12", "GMT+2": "Etc/GMT+2",
             "GMT+3": "Etc/GMT+3","GMT+4": "Etc/GMT+4","GMT+5": "Etc/GMT+5","GMT+6": "Etc/GMT+6",
             "GMT+7": "Etc/GMT+7","GMT+8": "Etc/GMT+8","GMT+9": "Etc/GMT+9","GMT-0": "Etc/GMT-0",
             "GMT-1": "Etc/GMT-1","GMT-10": "Etc/GMT-10","GMT-11": "Etc/GMT-11","GMT-12": "Etc/GMT-12",
             "GMT-13": "Etc/GMT-13","GMT-14": "Etc/GMT-14","GMT-2": "Etc/GMT-2","GMT-3": "Etc/GMT-3",
             "GMT-4": "Etc/GMT-4","GMT-5": "Etc/GMT-5","GMT-6": "Etc/GMT-6","GMT-7": "Etc/GMT-7",
             "GMT-8": "Etc/GMT-8","GMT-9": "Etc/GMT-9","GMT+0": "Etc/GMT0", "EASTERN": "EST5EDT",
             "UK": "Europe/London", "CET": "CET", "EET": "EET", "MSK": "Europe/Moscow", "WET": "WET",
             "HST": "HST" }

##This is used for calculations as my computer clock is also based on this timezone
##It could be anything as long as you change the local time to the same timezone as well, with pytz.
suomi = pytz.timezone("UTC")

reddit = praw.Reddit(client_id="",
                     client_secret="",
                     password="",
                     user_agent="",
                     username="")

findTimeAndZonePMAM = r'(\d+:\d+|\d+)( |)(PM|AM|pm|am) \w+'
findTimeAndZone = r'\d+:\d+( |,|.)( |)\w+( |)( |\+| |\-)(\d+|)'

print(findTimeAndZone)

months = ["January","February","March","April","May","June","July","August","October","September","November","December"]

##These must be changed depending on the month, because searching for all months is too slow, and I haven't found a way to add raw strings together
##There must be a better way to do this one though.
findDate1 = r"(may|june|july)( |,|)\d+(th|st| |)"
findDate2 = r"\d+/\d+/\d+"
findDate3 = r"\d\d(th|st| |)( |,|)( |)(may|june)"

findDateRs = [findDate1, findDate2, findDate3]

##Some subreddits that wanted to "opt-out" or don't seem to benefit from the bot, many subreddits have also just banned the bot which is fine.
dontPostSubreddits = ["/r/MHOCMP/", "/r/buildapc", "/r/Brewers", "/r/Reds",
                      "/r/OaklandAthletics", "/r/Nationals", "/r/buccos",
                      "/r/azdiamondbacks", "/r/redsox", "/r/LaGalaxy",
                      "/r/orioles", "/r/CHICubs", "/r/aviationmaintenance/",
                      "/r/angelsbaseball"]

weekdays = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
weekdays = {0: "monday", 1: "tuesday", 2: "wednesday", 3: "thursday", 4: "friday", 5: "saturday", 6: "sunday", -1: "sunday"}
weekdaysArr = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "tomorrow"]

timeFormatted = ""

##Main search loop
def searchPostsAndComments():
    
    while True:
      ##Get all submissions from /r/all
        for post in reddit.subreddit("all").stream.submissions():##new(limit=100):
            
            ##Search title and body
            findTitle = re.search(findTimeAndZonePMAM, post.title)
            findBody = re.search(findTimeAndZonePMAM, post.selftext)

            if not findTitle:
                findTitle = re.search(findTimeAndZone, post.title)
            if not findBody:
                findBody = re.search(findTimeAndZone, post.selftext)
            
            if findTitle:

                found = findTitle.group();
                
                ##Just for debugging, and to see that the app is doing something
                try:
                    print("\nTIME: ", found)
                    print("TITLE: ", post.title)
                    print("URL: ", post.url)
                except UnicodeEncodeError:
                    continue

                if any(x in post.url for x in dontPostSubreddits): ##"buildapc" in post.url:
                    continue

                if not happensToday(post):
                    continue
                
                if not getTense(post.title):
                    continue
                
                if not checkForDates(post):
                    continue
                    
                difference = getTimeDifference(found)
                
                ##Make sure the time isn't "yesterday" or happening right now
                if difference and difference < 22 and difference > 0.12:

                    sendMessage(post, difference, found)
            elif findBody:
                
                found = findBody.group()
                
                try:
                    print("\nTIME: ", found)
                    print("TITLE: ", post.title)
                    print("URL: ", post.url)
                except UnicodeEncodeError:
                    continue
                
                difference = getTimeDifference(found)

                if not happensToday(post):
                    continue
                
                if not checkForDates(post):
                    continue
                
                if not getTense(post.body):
                    continue
                
                if difference and difference < 22 and difference > 0.12:

                    sendMessage(post, difference, found)
                
        time.sleep(0.5)

##Try to find dates that indicates that the time happens some other day than today.
def checkForDates(post):

    postTitle = post.title.lower()
    postBody = post.selftext.lower()
    
    ##foundDates = re.search(findDate1, postBody)
    
    for regex in findDateRs:

        foundDates = re.search(regex, postTitle)
        if foundDates:
            break
        else:
            foundDates = re.search(regex, postBody)
            if foundDates:
                break

    if foundDates:

        foundDate = foundDates.group()

        try:
            date = parser.parse(foundDate)
            print("FOUND DATE:",foundDate)
            print(date)
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

def happensToday(post):

    day = datetime.datetime.today().weekday()
    if day == 6:
        ar = [weekdays[day], weekdays[day-1], weekdays[0]]
    else:
        ar = [weekdays[day], weekdays[day-1], weekdays[day+1]]
    a = [x for x in weekdaysArr if x not in ar]

    ##print(a)
    
    if any(x in post.title.lower() for x in a):
        return False
    if any(x in post.selftext.lower() for x in a):
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

##By using nltk we can determine the tense of the text. If we found that the text is in past tense we don't post anything, as the event would have already ended
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
    
    ##These values require some experimenting, but should be okay
    if pastPer > 0.7:
        return False
    if presentPer > 0.7:
        return True
    if futurePer > 0.7:
        return True
    if pastPer == presentPer and pastPer > 0.4:
        return False
    
    return True
      
##Change the timezone to proper one, taking into account daylight savings      
def is_dst(timezone):
    tz = pytz.timezone(timezone)
    now = pytz.utc.localize(datetime.datetime.utcnow())
    return now.astimezone(tz).dst() != timedelta(0)

def sendMessage(post, difference, found):

    global timeFormatted
    
    endMessage = "\n\n---\n\nI'm a bot, if you want to send feedback, please comment below or send a PM."
    
    split = math.modf(difference)
    hours = int(split[1])
    
    minutes = math.floor(split[0] * 60)
    
    timeFormatted = timeFormatted.strftime('%Y-%m-%d %H:%M:%S%z')
    
    r = requests.post('http://countle.com/createnew/gQOCmuH7H3N_WVfvrjIB0nZULCH2rmr1dQEVYPkxAQg',
                      json={"date": timeFormatted, "foundtime": found, "eventname": post.title,
                            "redditlink": post.url})

    token = r.text

    cdUrl = "https://countle.com/" + token

    foundParts = found.split(" ")
    zone = foundParts[-1].upper()
    timezone = timezones[zone]

    if zone == "BST":
        timezone = zone  
    elif is_dst(timezone):
        timezone = zone.replace("S", "D")
    else:
        timezone = zone
        
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
            post.reply(found + " happens when this comment is " + str(minutes) + " minutes old.\n\nYou can find the live countdown here: " + cdUrl + endMessage)
        except Exception as e:
            print(e)
            pass
    else:
        if minutes != 0:
            try:
                post.reply(found + " happens when this comment is " + str(int(hours)) + hoursS + " and " + str(minutes) + " minutes old.\n\nYou can find the live countdown here: " + cdUrl + endMessage)
            except Exception as e:
                print(e)
                pass
        else:
            try:
                post.reply(found + " happens when this comment is " + str(int(hours)) + hoursS + " old.\n\nYou can find the live countdown here: " + cdUrl + endMessage)
            except Exception as e:
                print(e)
                pass

print(reddit.user.me())
##Start the application/main loop
searchPostsAndComments()
