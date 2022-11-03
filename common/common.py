# ==================================================================================================================== #
# Script Name: common
#
# Description: common misc library for PRI
# ==================================================================================================================== #
import logging
import os
import re
import datetime
import platform
from distutils.dir_util import mkpath, remove_tree
import subprocess
import requests 
from bs4 import BeautifulSoup
import fnmatch

import urllib.request # python310
import winreg # python310
# import urllib2 # python 2.7.18 original
# import _winreg # python 2.7.18 original

try:
    import wmi  # depends on WMI Module
except ImportError:
    raise ImportError("Please Install WMI")

# Variables #

SCRIPT_REAL_PATH = os.path.dirname(os.path.realpath(__file__))
CURRENT_TIMESTAMP = datetime.datetime.now().strftime('%Y%m%d-%I%M%S%p')
UNC_REGEX = re.compile(r"^\\\\([A-z0-9_.$-]+)")
HTTP_REGEX = re.compile('^http.*/([^/]+)(\.*)')
FILE_REGEX = re.compile("[-\w,\s]+\.[A-Za-z]{3,4}$")
PRODUCT_REGEX = re.compile("SWI9X\d\d\w_\d\d\.\d\d\.\d\d\.\d\d|SWIX55C_\d\d.\d\d.\d\d.\d\d-\d\d\d|SWIX55C_\d\d.\d\d.\d\d.\d\d")

# Logger #
LOGGER = logging.root
LOGGER.setLevel(logging.DEBUG)
LOG_FORMAT = logging.Formatter('%(asctime)s %(levelname)-5s: %(message)s', '%Y-%m-%d,%H:%M:%S')


class CopyError(Exception):
    def __init__(self, rc):
        self.rc = rc
        self.message = "Failed to copy: %s" % self.rc

# ==================================================================================================================== #
# Functions
# ==================================================================================================================== #
# ==================================================================================================================== #
#   Function Name: heading
#
#     Description: Creates two parallel bar to surround the message using "=" char
#
#    Parameter(s): message - string value
#
# Return Value(s): None
# ==================================================================================================================== #
def heading(message):
    bar = "=" * len(message)
    # log bar
    logging.info(bar)
    logging.info(message)
    logging.info(bar)


# ==================================================================================================================== #
#   Function Name: main_heading
#
#     Description: Creates a main heading for each major function
#
#    Parameter(s): value - function name
#
# Return Value(s): None
# ==================================================================================================================== #
def main_heading(value):
    message = "========== %s ==========" % value
    heading(message)


# ==================================================================================================================== #
#   Function Name: sub_heading
#
#     Description: Creates a sub heading for each minor function
#
#    Parameter(s): value - function name
#
# Return Value(s): None
# ==================================================================================================================== #
def sub_heading(value):
    message = "< %s >" % value
    heading(message)


# ==================================================================================================================== #
#   Function Name: log_cpu_info
#
#     Description: logs the cpu information from each machine used (building/testing)
#
#    Parameter(s): None
#
# Return Value(s): None
# ==================================================================================================================== #
def log_cpu_info():
    main_heading("Build Information")
    wmi_object = wmi.WMI()
    comp_name = platform.uname()
    logging.info("Computer Name: %s" % comp_name[1])
    logging.info("Platform: %s %s (%s)" % (comp_name[0], comp_name[2], comp_name[3]))
    logging.info("CPU: %s" % comp_name[4])
    for csproduct in wmi_object.Win32_ComputerSystemProduct():
        logging.info("Brand (model): %s - %s" % (csproduct.Vendor, csproduct.Version))
        logging.info("Name: %s, Identifying Number: %s" % (csproduct.Name, csproduct.IdentifyingNumber))


# ==================================================================================================================== #
#   Function Name: log_argv_info
#
#     Description: logs the cpu information from each machine used (building/testing)
#
#    Parameter(s): None
#
# Return Value(s): None
# ==================================================================================================================== #
def log_argv_info(args):
    sub_heading("Command Line (argv)")
    for item in sorted(args.__dict__):
        if str(item) == "pwd":
            if args.pwd is not None:
                logging.info("%s = []" % item.ljust(16))
        else:
            logging.info("%s = %s" % (item.ljust(16), args.__dict__[item]))

# ==================================================================================================================== #
#   Function Name: parse_text_file
#
#     Description: Takes user input from text file and creates a list of input/value pairing.
#
#    Parameter(s): input_file - path of the input file given by user
#
# Return Value(s): presets
# ==================================================================================================================== #
def parse_text_file(input_file):
    presets = []
    try:
        file_handler = open(input_file, 'r')  # read only
        for line in file_handler:
            if line != "\n" and not line.startswith('#'):
                if not line.startswith("-"):
                    raise ValueError

                function = line.strip("\r\n").split("=")
                presets.append(function[0])
                if len(function) > 1:
                    args = re.split(', ', function[1])  # split the input based on ', ' between the variables
                    for item in args:
                        presets.append(item.strip("\"").rstrip(" "))  # remove quotes and spaces
        return presets
    except ValueError:
        raise ValueError("Incorrect Text Content")


# ==================================================================================================================== #
#   Function Name: create_log_handler
#
#     Description: creates a file handler that will log debug messages and below
#
#    Parameter(s): output - the path to the specified output directory
#                    name - script name
#
# Return Value(s): log_file
# ==================================================================================================================== #
def create_file_handler(output_location):
    log_file = os.path.join(output_location, "%s.log" % CURRENT_TIMESTAMP)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(LOG_FORMAT)
    file_handler.setLevel(logging.DEBUG)
    LOGGER.addHandler(file_handler)

    return log_file


# ==================================================================================================================== #
#   Function Name: create_stream
#
#     Description: creates a stream handler that will log INFO messages and ERROR messages to screen
#
#    Parameter(s): None
#
# Return Value(s): None
# ==================================================================================================================== #
def create_stream():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(LOG_FORMAT)
    stream_handler.setLevel(logging.INFO)
    LOGGER.addHandler(stream_handler)


# ==================================================================================================================== #
#   Function Name: create_log_file
#
#     Description: creates a log file that will log all the logging information
#
#    Parameter(s): None
#
# Return Value(s): None
# ==================================================================================================================== #
def create_log_file(argv, log_name):
    log_folder = os.path.join(argv.output, "Logs", "%s" % log_name)

    # create log folder
    create_folder(log_folder)

    # create log file
    log_file = create_file_handler(log_folder)
    log_cpu_info()
    log_argv_info(argv)

    return log_file


# ==================================================================================================================== #
#   Function Name: get_html_files_list
#
#     Description: Gets tht HTML files from http site and store into a list (copy from FWpackagecreator and edited to
#                  fit into module_setup)
#
#    Parameter(s): Link     - the http link
#                  ext      - search by .extension (if set to None, it will find all files with an extension)
#                  fileList - list to append "found" files
#
# Return Value(s): None
# ==================================================================================================================== #
def get_html_files_list(link, ext, filelist):
    page = requests.get(link).text
    soup = BeautifulSoup(page, 'html.parser')
    if ext is not None:
        files = [node.get('href') for node in soup.find_all('a') if node.get('href').endswith(ext)]
    else:
        files = [node.get('href') for node in soup.find_all('a') if (fnmatch.fnmatch(node.get('href'), "*.*") and str(node.get('href')) != "../")]
    for file in files:
        filePath = link + file[(file.rfind('/'))+1:]
        fileName = os.path.split(filePath)[1]
        if fnmatch.fnmatch(fileName, "*.*"):
            filelist.append(filePath)


# ==================================================================================================================== #
#   Function Name: download_file
#
#     Description: Download from http site to the specified destination (copy from FWpackagecreator and edited to fit
#                  into module_setup)
#
#    Parameter(s): source      - location of the file to download
#                  destination - where to copy the file
#
# Return Value(s): None
# ==================================================================================================================== #
def download_file(source, destination):
    file_name = os.path.split(source)[1]
    try:
        u = urllib2.urlopen(source)
    except urllib2.URLError as e:
        logging.error(e)
        raise urllib2.URLError

    meta = u.info()
    logging.info("Downloading... (%s)" % file_name)
    file_size = int(meta.getheaders("Content-Length")[0])
    with open(destination + "\\" + file_name, 'wb') as local_file:
        local_file.write(u.read())
    u.close()
    logging.info("Downloaded %s Bytes (%s)" % (file_size, file_name))


# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #
def robocopy(cmd):
    robocopy_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = robocopy_process.communicate()[0]
    logging.debug(output)
    rc = robocopy_process.returncode
    return rc


# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #
def copy_files(source, destination, mirror=False):
    if HTTP_REGEX.search(str(source)):
        if FILE_REGEX.search(str(source)):
            download_folder = os.path.join(SCRIPT_REAL_PATH, "download-file")
            create_folder(download_folder)
            download_file(source, download_folder)
            robocopy_files(os.path.join(download_folder, os.path.split(source)[1]), destination)
        else:
            folder_list = []
            get_html_files_list(source, None, folder_list)
            if len(folder_list) == 0:
                logging.debug("empty list")
                raise LookupError
            else:
                download_folder = os.path.join(SCRIPT_REAL_PATH, "download")
                create_folder(download_folder)
                for item in folder_list:
                    download_file(item, download_folder)
                robocopy_files(download_folder, destination)
    else:
        robocopy_files(source, destination, mirror=mirror)


# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #
def robocopy_files(source, destination, mirror=False):
    if os.path.exists(source) and os.path.exists(destination) and source != destination:
        if os.path.isfile(source):
            cmd = ["robocopy", os.path.dirname(source), destination, os.path.split(source)[1], "/is", "/it", "/bytes",
                   "/np", "/ndl"]
        else:
            if mirror:
                cmd = ["robocopy", source, destination, "/e", "/is", "/it", "/bytes", "/np", "/ndl", "/MT", "/purge"]
            elif os.path.basename(source)== "EFS":
                cmd = ["robocopy", source, os.path.join(destination, "EFS"), "/e", "/is", "/it", "/bytes", "/np", "/ndl", "/MT"]
            else:
                cmd = ["robocopy", source, destination, "/e", "/is", "/it", "/bytes", "/np", "/ndl", "/MT"]
        logging.debug(cmd)
        rc = robocopy(cmd)
        if rc > 5:
            raise CopyError(rc)
    else:
        logging.debug("skip copying...")


# ==================================================================================================================== #
#   Function Name: create_folder
#
#     Description: Copy files from given source to given destination.
#
#    Parameter(s): source      - location of the file/folder to copy
#                  destination - where to copy the content
#
# Return Value(s): None
# ==================================================================================================================== #
def create_folder(path):
    mkpath(path)


# ==================================================================================================================== #
#   Function Name: remove_folder
#
#     Description: Copy files from given source to given destination.
#
#    Parameter(s): source      - location of the file/folder to copy
#                  destination - where to copy the content
#
# Return Value(s): None
# ==================================================================================================================== #
def remove_folder(path):
    remove_tree(path)


# ==================================================================================================================== #
#   Function Name: get_reg_credentials
#
#     Description: Copy files from given source to given destination.
#
#    Parameter(s): source      - location of the file/folder to copy
#                  destination - where to copy the content
#
# Return Value(s): None
# ==================================================================================================================== #
def get_reg_credentials():
    registry = _winreg.ConnectRegistry(None, _winreg.HKEY_LOCAL_MACHINE)
    raw_key = _winreg.OpenKey(registry, "SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon")
    data = {}

    try:
        index = 0
        while 1:
            name, value, type = _winreg.EnumValue(raw_key, index)
            data[name] = value
            index += 1
    except WindowsError:
        pass

    _winreg.CloseKey(registry)

    try:
        user = data["DefaultUserName"]
        pwd = data["DefaultPassword"]
    except KeyError:
        user = None
        pwd = None

    return user, pwd
