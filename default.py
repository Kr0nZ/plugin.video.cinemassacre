import xbmcplugin
import xbmcgui
import xbmcaddon
import sys
import urllib, urllib2
import re
import showEpisode, CommonFunctions, os#, random
try:
  import StorageServer
except:
  import storageserverdummy as StorageServer
cache = StorageServer.StorageServer("cinemassacre", 24)
common = CommonFunctions
#cache.dbg = True
#common.dbg = True
addon = xbmcaddon.Addon(id='plugin.video.cinemassacre')

thisPlugin = int(sys.argv[1])

baseLink = "http://cinemassacre.com/"

hideMenuItem = []
hideMenuItem.append("412") # Gallery
hideMenuItem.append("486") # Fan Stuff
hideMenuItem.append("402") # Full list of AVGN Videos
hideMenuItem.append("225") # Game Collection

_regex_extractMenuItems = re.compile("<li(?:.+?)class=(?:[\'|\"]*)(?:.+?)cat-item-([\d]{1,4})(?:[^\'|\"]*)(?:[\'|\"]*)><a(?:.+?)href=(?:[\'|\"]*)([^\'|\"]*)(?:[\'|\"]*)(?:[^\>]*)>([^\<]*)</a>", re.DOTALL);

defaultsXML = os.path.join(addon.getAddonInfo('path'), 'resources',"defaults.xml")
dontShowTheseUrls = []
defaultFolderIcons = {"default":os.path.join(addon.getAddonInfo('path'), "icon.png"),"list":[]}

def retFileAsString(fileName):
    file = common.openFile(fileName, "r")
    tmpContents = file.read()
    file.close()
    return tmpContents
    
def getDefaultIcons():
    xmlContents = retFileAsString(defaultsXML)
    iconList =  common.parseDOM(xmlContents, "icons")
    iconUrlList =  common.parseDOM(iconList, "icon", ret="url")
    iconImgList =  common.parseDOM(iconList, "icon", ret="image")
    
    retList = []
    for i in range(0,len(iconUrlList)):
        retList.append({"url": iconUrlList[i], "image": os.path.join(addon.getAddonInfo('path'), 'resources', 'images', iconImgList[i])})
    return retList

def getNotShownUrls():
    xmlContents = retFileAsString(defaultsXML)
    exclList =  common.parseDOM(xmlContents, "excludeUrls")
    urlList =  common.parseDOM(exclList, "url")
    
    retList = []
    for url in urlList:
        retList.append(url)
    return retList

def excludeUrl(url):
    for notUrl in dontShowTheseUrls:
      if notUrl in url:
        return True
    return False

def checkDefaultIcon(url):
    possibleIcon = ""
    for defaultIcon in defaultFolderIcons["list"]:
        if (defaultIcon["url"] in url) and (len(defaultIcon["image"]) > len(possibleIcon)):
            possibleIcon = defaultIcon["image"]
    if len(possibleIcon) == 0:
        possibleIcon = defaultFolderIcons["default"]
    return possibleIcon
    
def addEpisodeListToDirectory(epList):
    for episode in epList:
        if not excludeUrl(episode['url']):
            addDirectoryItem(episode['title'], {"action" : "episode", "link": episode['url']}, episode['thumb'], False)
    xbmcplugin.endOfDirectory(thisPlugin)        
    
def extractEpisodeLink(episode_h3):
    linkUrl = common.parseDOM(episode_h3, "a", ret="href")[0]
    if excludeUrl(linkUrl):
        return None
    return linkUrl

def extractEpisodeTitle(episode, episode_h3):
    linkTitle = common.parseDOM(episode_h3, "a")[0]
    linkDate = common.parseDOM(episode, "div", attrs={"class": "video-date"})
    if len(linkDate)>0:
        linkDate = linkDate[0]
        linkDate = re.compile('(.+?)<span>|</span>', re.DOTALL).findall(linkDate)[0]
        linkTitle = linkTitle+" ("+linkDate.strip()+")"
    linkTitle = remove_html_special_chars(linkTitle)
    return linkTitle
    
def extractEpisodeImg(episode):
    linkImage = common.parseDOM(episode, "div", attrs={"class": "video-tnail"})
    linkImage = common.parseDOM(linkImage, "img", ret="src")
    linkImageTmp = re.compile('src=([^&]*)', re.DOTALL).findall(linkImage[0])
    if len(linkImageTmp)>0:
        if linkImageTmp[0][:1] != "/":
            linkImageTmp[0] = "/" + linkImageTmp[0]
        linkImage = baseLink+linkImageTmp[0]
    else:
        if (len(linkImage[0]) > 0) and (baseLink in linkImage[0]):
            linkImage = linkImage[0]
        else:
            linkImage = ""
    return linkImage

def nextShowPage(page):
    wpPageNav = common.parseDOM(page, "div", attrs={"class": "wp-pagenavi"})
    nextPageUrl = common.parseDOM(wpPageNav, "a", attrs={"class": "nextpostslink"}, ret="href")
    if len(nextPageUrl)>0:
        page = load_page(nextPageUrl[0])
        show = common.parseDOM(page, "div", attrs={"id": "content"})
        return show
    else:
        return None
        
def pageInCache(episodeList,link):
    storedList = cache.get(link)
    print "pageInCache:"
    if (len(storedList) >= len(episodeList)):
        storedList = eval(storedList)
        for i in range(0,len(episodeList)):
            if episodeList[i] != storedList[i]:
                return []
        print "Using Stored Cache Page"
        return storedList
    return []
    
def mainPage():
    global thisPlugin

    addDirectoryItem(addon.getLocalizedString(30000), {"action" : "recent", "link": ""}, defaultFolderIcons["default"])  
    subMenu(baseLink)

def subMenu(link):
    global thisPlugin
    link = urllib.unquote(link)
    page = load_page(link)
    mainMenu = extractMenu(page,link)
    
    if not len(mainMenu):
        return showPage(link) # If link has no sub categories then display video list
    
    if len(link) != len(baseLink):
      addDirectoryItem(addon.getLocalizedString(30001), {"action" : "show", "link": link}, defaultFolderIcons["default"]) # All Videos Link
    
    for menuItem in mainMenu:
        menu_name = remove_html_special_chars(menuItem['name']);
        menu_link = menuItem['link'];
        menu_icon = checkDefaultIcon(menu_link)
        addDirectoryItem(menu_name, {"action" : "submenu", "link": menu_link}, menu_icon)
        
    xbmcplugin.endOfDirectory(thisPlugin)

def recentPage():
    global thisPlugin
    page = load_page(baseLink)
    show = common.parseDOM(page, "div", attrs={"id": "sidebar-right"})
    linkList = extractEpisodes(show)
    addEpisodeListToDirectory(linkList)
    
def extractMenu(page,link=baseLink):
    navList = common.parseDOM(page, "ul", attrs={"id": "navlist"})
    navUrls = _regex_extractMenuItems.findall(navList[0])
    
    menuList = []
    lastUrl = ""
    for item in navUrls:
      if (link == item[1]): # Dont show parent category
        continue
      if link not in item[1]: # Only show child categories
        continue
      if (lastUrl in item[1]) and (len(lastUrl)>0): # Dont show children with parents
        continue
      lastUrl = item[1]
      if item[0] in hideMenuItem: # Dont show hidden Menu items
        continue
      menuList.append({"name" : item[2], "link" : item[1]})
      
    return menuList

def showPage(link):
    global thisPlugin
    link = urllib.unquote(link)
    page = load_page(link)
    show = common.parseDOM(page, "div", attrs={"id": "content"})
    episodeList = extractEpisodes(show)
    
    ##Check first page against cache
    cachedPage = pageInCache(episodeList,link) # Returns empty list if cache differs
    if (len(cachedPage)>0):
        episodeList = cachedPage
        show = None
    else:
        show = nextShowPage(show)
    
    while (show != None):
        linkList = extractEpisodes(show)
        episodeList = episodeList + linkList
        show = nextShowPage(show)

    cache.set(link, repr(episodeList)) #update cache
    addEpisodeListToDirectory(episodeList)

def extractEpisodes(show):
    episodes = common.parseDOM(show, "div", attrs={"class": "video archive"})
    linkList = []
    for episode in episodes:
        episode = episode.encode('ascii', 'ignore')
        episode_h3 = common.parseDOM(episode, "h3")
        episode_link = extractEpisodeLink(episode_h3)
        if episode_link is None:
            continue;
        episod_title = extractEpisodeTitle(episode, episode_h3)
        episod_title = remove_html_special_chars(episod_title)
        episode_img = extractEpisodeImg(episode)
        linkList.append({"title":episod_title, "url":episode_link, "thumb":episode_img})
    return linkList

def playEpisode(link):
    link = urllib.unquote(link)
    page = load_page(link)
    showEpisode.showEpisode(page)

def load_page(url):
    print "Getting page: " + url
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:14.0) Gecko/20100101 Firefox/14.0.1')
    response = urllib2.urlopen(req)
    link = response.read()
    response.close()
    return link

def addDirectoryItem(name, parameters={}, pic="", folder=True):
    li = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=pic)
    if not folder:
        li.setProperty('IsPlayable', 'true')
    url = sys.argv[0] + '?' + urllib.urlencode(parameters)# + "&randTok=" + str(random.randint(1000, 10000))
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=folder)

def remove_html_special_chars(inputStr):
    inputStr = inputStr.replace("&#8211;", "-")
    inputStr = inputStr.replace("&#8217;", "'")#\x92
    inputStr = inputStr.replace("&#039;", chr(39))# '
    inputStr = inputStr.replace("&#038;", chr(38))# &
    inputStr=inputStr.replace("&lt;","<").replace("&gt;",">").replace("&amp;","&").replace("&#039;","'")
    inputStr=inputStr.replace("&quot;","\"").replace("&ndash;","-").replace("&#8220;", "\"")
    inputStr=inputStr.replace("&#8221;", "\"")
    inputStr=inputStr.strip()
    return inputStr
    
def get_params():
    param = []
    paramstring = sys.argv[2]
    print paramstring
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    
    return param

dontShowTheseUrls = getNotShownUrls()
defaultFolderIcons["list"] = getDefaultIcons()

if not sys.argv[2]:
    mainPage()
else:
    params = get_params()
    if params['action'] == "show":
        print "Video List"
        showPage(params['link'])
    elif params['action'] == "submenu":
        print "Menu"
        subMenu(params['link'])
    elif params['action'] == "recent":
        print "Recent list"
        recentPage()
    elif params['action'] == "episode":
        print "Episode"
        playEpisode(params['link'])
    else:
        mainPage()
