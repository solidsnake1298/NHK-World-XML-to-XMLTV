""" Python application to convert NHK EPG in JSON into XMLTV standard"""
__author__ = "Squizzy"
__copyright__ = "Copyright 2019-now, Squizzy"
__credits__ = "The respective websites, and whoever took time to share information\
                 on how to use Python and modules"
__license__ = "GPLv2"
__version__ = "1.6" # Python-3 only
__maintainer__ = "Squizzy"
__contributors__ = "TheDreadPirate"

import json
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as xml
import requests
import sys
import calendar
import pytz


# Location of the NHK EPG JSON to be downloaded.
# This might need occastional updating
URL_OF_NHK_JSON_ROOT: str = "https://masterpl.hls.nhkworld.jp/epg/w"

# Location of the NHK streams for use in the XMLTV
URL_OF_NHK_ROOT: str = "https://www3.nhk.or.jp"

# Location of the NHK channel icon
URL_OF_NHK_CHANNEL_ICON: str = URL_OF_NHK_ROOT + "nhkworld/assets/images/icon_nhkworld_tv.png"

# Name of the file that is created by this application 
# which contains the XMLTV XML of the NHK EPG
XMLTV_XML_FILE: str = 'ConvertedNHK.xml'

# Downloaded JSON file for tests, or created when DEBUG is on
DEBUG: bool = False
TEST_NHK_JSON: str = 'DownloadedJSON.json'

# Local time zone that will be used for the timestamps in the XMLTV file
# Currently set for UTC as for Continental European use
TIMEZONE: timezone = timezone.utc

# In case the time offset is incorrect in the XMLTV file, the value below 
# can be modified to adjust it: For example -0100 would change to -1 UTC
TIME_OFFSET: str = ' +0000'

# Import the .json from the URL
def Import_nhk_epg_json(JsonIn: str) -> dict:
    """Downloads the NHK EPG JSON data from the specified URL and loads it into a variable.
    Args:
        JsonInURL (str): URL to download the NHK EPG JSON data.
    """
    response: requests.Response = requests.get(url = JsonIn)

    if response.status_code == 200:
        try:
            data: dict = response.json()
        except requests.exceptions.JSONDecodeError:
            print("problem with the parsing of the JSON file downloaded from NHK")
            sys.exit(1)

    elif response.status_code == 404:
        print(f"Network error {response.status_code}: The NHK file containing the EPG JSON does not exist at the URL provided")
        sys.exit(1)

    elif response.status_code == 403:
        print(f"Network error {response.status_code}: The NHK EPG JSON file exists but NHK rejects the request - try again later")
        sys.exit(1)

    else:
        print(f"Network error {response.status_code}: Problem with the URL to the NHK JSON file provided")
        sys.exit(1)

    return data


def Convert_tokyo_to_utc(dateTime: str) -> str:
    """ Converts the date-time from Tokyo's time zone to UTC.  Formats to XMLTV time format
    Args:
        u (str): Human readable date-time with time zone offset.  Will be parsed and converted to UTC.
    Returns:
        str: Returns the date in XMLTV format required for applications like Kodi.
    """    
    return datetime.strptime(dateTime, '%Y-%m-%dT%H:%M:%S%z').astimezone(pytz.utc).strftime('%Y%m%d%H%M%S')


def Add_xml_element(parent: xml.Element, tag: str, attributes:dict[str,str]|None=None, text:str|None=None) -> xml.Element:
    """ Add an XML element to a tree
    Args:
        parent (xml.Element): The parent node in the XML tree
        tag (str): The name of the XML tag to be added.
        attributes (dict, optional): Dictionary of attributes for the XML tag. Defaults to None.
        text (str, optional): The text content for the XML element. Defaults to None.
    Returns:
        xml.Element: the XML node created
    """
    element: xml.Element = xml.SubElement(parent, tag)
    if attributes:
        for key, value in attributes.items():
            element.set(key, value)
    if text:
        element.text = text
    return element


def Xml_beautify(elem:xml.Element, level:int=0) -> bool:
    """ indent: beautify the xml to be output, rather than having it stay on one line
        Origin: http://effbot.org/zone/element-lib.htm#prettyprint """
    i:str = "\n" + level * "\t"
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "\t"
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            Xml_beautify(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
    return True


def Generate_xmltv_xml()  -> xml.Element:
    """Generates the XMLTV XML tree from the NHK JSON EPG data        
    Returns:
        root (xml.tree): the XML tree created
    """
    # Start filling in the table XML tree with content that is useless and might not change
    root: xml.Element = xml.Element(
                            'tv', 
                            attrib={
                                'source-data-url': URL_OF_NHK_JSON_ROOT, 
                                'source-info-name': 'NHK World EPG Json', 
                                'source-info-url': 'https://www3.nhk.or.jp/nhkworld/'})

    channel = Add_xml_element(root, 'channel', attributes={'id': 'nhk.world'})
    Add_xml_element(channel, 'display-name', text='NHK World')
    Add_xml_element(channel, 'icon', attributes={'src': URL_OF_NHK_CHANNEL_ICON})

    # Gets today's date.  Applies timedelta to generate date format need to get each day's JSON.
    # Range starts at 0 to get today's JSON.
    today = datetime.today()
    for delta in range(14):
        date = today + timedelta(days=delta)
        formatedDate = date.strftime("%Y%m%d")
        URL_OF_NHK_JSON = URL_OF_NHK_JSON_ROOT + "/" + formatedDate + ".json"
        nhkimported: dict = Import_nhk_epg_json(URL_OF_NHK_JSON)

        print("NHK World EPG JSON file for " + formatedDate + " downloaded successfully")

        # Go through all items, though only interested in the Programmes information here
        for item in nhkimported["data"]:

            # construct the program info xml tree
            programme: xml.Element = Add_xml_element(
                                        root, 
                                        'programme', 
                                        attributes={'start': Convert_tokyo_to_utc(item["startTime"]) + TIME_OFFSET,
                                                    'stop': Convert_tokyo_to_utc(item["endTime"]) + TIME_OFFSET,
                                                    'channel':'nhk.world'})

            Add_xml_element(programme, 'title', attributes={'lang': 'en'}, text=item["title"])
            Add_xml_element(programme, 'sub-title', attributes={'lang': 'en'}, text=item["episodeTitle"] if item["episodeTitle"] else item["airingId"])
            Add_xml_element(programme, 'desc', attributes={'lang': 'en'}, text=item["description"])
            Add_xml_element(programme, 'episode-num', text=item["airingId"])
            Add_xml_element(programme, 'icon', attributes={'src': item["episodeThumbnailURL"]})

    if not Xml_beautify(root):
        print("Problem beautifying the XML")
        sys.exit(1)
    
    print("NHK WORLD EPG data converted to XMLTV standard")
    
    return root


def Save_xmltv_xml_to_file(root: xml.Element) -> bool:
    """Store the XML tree to a file

    Args:
        root (_type_): The XMLTV XML tree to store to file
    """
    # Export the xml to a local file
    tree:xml.ElementTree = xml.ElementTree(root)
    with open(XMLTV_XML_FILE, 'w+b') as outFile:
        tree.write(outFile)
    
    print(f"{XMLTV_XML_FILE} created successfully")
    return True


def main() -> int:
    """Main application
    Returns:
        0: Successful execution
    """
    XmltvXml: xml.Element = Generate_xmltv_xml()
    
    Save_xmltv_xml_to_file(XmltvXml)
    
    return 0



if __name__ == "__main__":
    main()
