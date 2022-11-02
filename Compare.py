# ==================================================================================================================== #
# Script Name: compare diff and xml
# Usage: -i <input|xlsm> -o <output|xml> -l </dir/log_file>
# Example: -i </dir|xlsm> -o <output|xml> -l </dir> 
# Description: automation script to compare diff and xml
# ==================================================================================================================== #
import argparse
import logging
import xml.etree.ElementTree as ET # read xml
import os
import re
from unidiff import PatchSet # module for getting diff file information
# win32com --> open excel
try:
    import win32com.client
except ImportError:
    logging.error("Please Install win32com")
    raise ImportError

# custom libraries #
from common import excel
from common import oempri
from common import common

SCRIPT_REAL_PATH = os.path.dirname(os.path.realpath(__file__))
# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #
def excel_info(excel_path, output_path):
    xls = excel.ExcelApp() # Read excel file
    xls.open(excel_path) # Open excel file to get the input data
    
    search_Field = [] # This is Field. example PRI package customer
    search_value = [] # This is the value of Field
    Carriers_PRI_Files_value = [] # Carriers PRI Files have a lot of value which are needed to be compared to output file

    i = 2 # first row is Field and value
    while i <= xls.find_last_row('sheet1'): # sheet1 is table name, append Field and value to list
        if xls.read_row('sheet1', i)[0] == 'Carriers PRI Files': # First deal with Carriers PRI Files value. Index 0 is Field, 1 is the value of Field
            search_Field.append(xls.read_row('sheet1', i)[0])
            for j in range(xls.find_last_row('sheet1') - i): # xls.find_last_row('sheet1') - i is for checking number of Carriers PRI Files value number
                if xls.read_row('sheet1', i+j)[1] is None:
                    pass
                else:
                    Carriers_PRI_Files_value.append(xls.read_row('sheet1', i+j)[1])
            search_value.append(Carriers_PRI_Files_value)
            i += j + 1
        elif xls.read_row('sheet1', i)[0] is None and xls.read_row('sheet1', i)[1] is None: # If Field and value is None --> pass append to list
            i += 1
        else: # Other Field and value append to list
            search_Field.append(xls.read_row('sheet1', i)[0])
            if type(xls.read_row('sheet1', i)[1]) == float:
                temp = str(int(xls.read_row('sheet1', i)[1]))
                search_value.append(temp)
            else:
                search_value.append(xls.read_row('sheet1', i)[1])
            i += 1

    if '.diff' in output_path: # diff file compare
        print("This is diff compare")
        compare_to_diff_file_info(output_path, search_Field, search_value)
    else:
        print("This is XML compare") # xml file compare
        compare_to_xml_info(output_path, search_Field, search_value)
    xls.quit() # close excel file

# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #
# Read xml for checking the value existing
def compare_to_xml_info(xml_path, s_key, s_val):
    # xml file parser function --> ET.parse(xml_path), tree.getroot()  --> get the xml info
    tree = ET.parse(xml_path)
    root = tree.getroot() 
    
    Pass = [] # If value can be found in xml file --> append to this list
    result = True # This is for checking the process passed or not
    
    # while loop initial value --> the times of loop
    i = 0
    j = 0 # Carrier PRI files --> using list to compare

    # Checking times --> each value comparing whole xml once
    while i < len(s_val):
        if type(s_val[i]) == list:
            if not s_val[i]:
                logging.info("Filed: "+ s_key[i])
                logging.info("Target: "+str(None))
            else:
                logging.info("Filed: "+ s_key[i])
                logging.info("Target: "+ str(s_val[i][j]))
        else:
            logging.info("Filed: "+ s_key[i])
            logging.info("Target: "+ str(s_val[i]))
        if s_val[i] is None:
            logging.info("PASSED")
            Pass.append("Value is None == passed")
        else:
            for find in root.iter(): # search all xml info
                # xml info is empty, so we pass comparing
                if str(find.text) == 'None' or find.text.isspace() == True:
                    pass
                # If we compare Carriers PRI Files, comparing the list with xml info
                elif s_key[i] == 'Carriers PRI Files':
                    if not s_val[i]:
                        logging.info("PASSED")
                        break
                    elif s_val[i][j] in find.text:
                        logging.debug("Data in xml file: <tag> : <content> " + find.tag + " : " + find.text)
                        Pass.append(s_val[i][j])
                elif str(s_val[i]) in find.text:
                    logging.debug("Data in xml file: <tag> : <content> " + find.tag + " : " + find.text)
                    Pass.append(s_val[i])
        # Checking value existing in xml info or not
        if s_key[i] == 'Carriers PRI Files':
            # print(Pass, len(Pass))
            if len(Pass) == 0:
                i+=1
                pass
            elif j == (len(s_val[i]) - 1):
                i+=1
            else:
                j+=1
            Pass.clear()
            logging.info("---------------NEXT TARGET---------------")
        else:
            if len(Pass) == 0:
                logging.info("FAILED")
                i+=1
                result = False
                pass
            else:
                Pass.clear()
                i+=1
            logging.info("---------------NEXT TARGET---------------")
    # Result of this process
    if result == False:
        logging.info("========================================")
        logging.info('XML file comparing result' + " : " + "< FAILED >")
        logging.info("========================================\n\n")
    else:
        logging.info("========================================")
        logging.info('XML file comparing result' + " : " + "< PASSED >")
        logging.info("========================================\n\n")

# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #

def compare_to_diff_file_info(diff_path, s_key, s_val):
    # parameter, sample file: Differences-1105080_RC7620-1_TeleAlarm.xml.diff
    added = [] # list to check which lines in diff file are added
    warning = [] # list to check which lines in diff file comparing to excel are not exsiting. Then, add the lines to this list
    add_line_number = 0 # This means which lines in diff file are added. Example: This is first line: @@ -125,7 +125,7 @@ This line nubmer is 0. Detail is seen in following.
    warning_line_number = [] # This means child that include added line. Example is following
                             #     @@ -125,7 +125,7 @@ 
                             #  			<Name/>    
                             #  		</TabPreferences> 
                             #  		<NVUPPreferences> 
                             # -			<NVUPVersion>1105080_9911208_RC7620-1_00.08.07.00_00_TeleAlarm_001.000_000</NVUPVersion> 
                             # +			<NVUPVersion>1105080_9911208_RC7620-1_00.08.07.00_00_TeleAlarm_001.001_000</NVUPVersion> # add_line_number 1
                             #  			<NVUPLink/>   
                             #  		</NVUPPreferences> 
                             #  	</Prefs>
    warning_pass_index = [] # In warning list, which are matching added.
    added_index = [] # In diff file, which lines are matching excel

    patches = PatchSet.from_filename(diff_path) 
    # Getting the added line in diff file, then add to added list
    for p in patches:
        if p.added > 0:
            for h in p:
                for i, line in enumerate(h):
                    if line.is_added:
                        tem = re.sub("\+\s+", "", str(line))
                        added_line = tem.strip('\n')
                        # Example: + <NVUPVersion>1105080_9911208_RC7620-1_00.08.07.00_00_TeleAlarm_001.001_000</NVUPVersion> The line number is 5 and in the list index is 0
                        added.append(added_line)
                        add_line_number += 1
                
                warning_line_number.append(add_line_number) # First add line in diff file is line number 1
                warning.append(str(h)) # This line is + <NVUPVersion>1105080_9911208_RC7620-1_00.08.07.00_00_TeleAlarm_001.001_000</NVUPVersion> and the index is 0 in warning list.
                             # Ths is warning example.
                             #     @@ -125,7 +125,7 @@ 
                             #  			<Name/>    
                             #  		</TabPreferences> 
                             #  		<NVUPPreferences> 
                             # -			<NVUPVersion>1105080_9911208_RC7620-1_00.08.07.00_00_TeleAlarm_001.000_000</NVUPVersion> 
                             # +			<NVUPVersion>1105080_9911208_RC7620-1_00.08.07.00_00_TeleAlarm_001.001_000</NVUPVersion> # add_line_number 1
                             #  			<NVUPLink/>   
                             #  		</NVUPPreferences> 
                             #  	</Prefs>
                
    
    
    for i in range(len(s_key)):
        result = False # This is for checking the result, PASSED or FAILED
        if s_val[i] is None:
            logging.info("Field: "+ s_key[i])
            logging.info("Target: "+ str(s_val[i]))
            logging.info("PASSED")
            logging.info("---------------NEXT TARGET---------------")
        elif type(s_val[i]) == list: # This is checking PRI Carrier File
            CarrierPRIFiles_index = 0
            if not s_val[i]:
                logging.info("Field: " + s_key[i])
                logging.info("Target: "+ str(None))
                logging.info("PASSED")
                logging.info("---------------NEXT TARGET---------------")
                pass
            else:
                for CarrierPRIFiles_index in range(len(s_val[i])):
                    logging.info("Field: " + s_key[i])
                    logging.info("Target: " + s_val[i][CarrierPRIFiles_index])
                    for j in range(len(added)):
                        if s_val[i][CarrierPRIFiles_index] in added[j]:
                            logging.debug("Target in diff file: " + added[j])
                            if j not in added_index:
                                added_index.append(j)
                            result = True
                    if result == True:
                        logging.info("PASSED")
                    else:
                        logging.info("Target in diff file is not found")
                        logging.info("FAILED")
                    logging.info("---------------NEXT TARGET---------------")
        else: # If Field is not PRI Carrier File.
            logging.info("Field: "+ s_key[i])
            logging.info("Target: "+ s_val[i])
            for k in range(len(added)):
                start = added[k].find('>')
                end = added[k].find('<',start)
                if s_val[i] in added[k][start+1:end]:
                    logging.debug("Target in diff file: " + added[k])
                    if k not in added_index:
                        added_index.append(k)
                    result = True
            if result == True:
                logging.info("PASSED")
            else:
                logging.info("Target in diff file is not found")
                logging.info("FAILED")
            logging.info("---------------NEXT TARGET---------------")
    
    # Comparing which lines are
    # m is added_index that means added line can match excel.
    for m in added_index:
        for n in warning_line_number: # n is warning_line_number that means warning line is if added_index < warning_line_number. warning will show.
            if m < n:
                if warning_line_number.index(n) not in warning_pass_index: # checking which lines are passed and then print not passed line child.
                    warning_pass_index.append(warning_line_number.index(n))
                break

    
    
    if len(warning) != len(warning_pass_index):
        logging.info("========================================")
        logging.info('Diff file comparing result' + " : " + "< FAILED >")
        logging.info("========================================\n\n")
    else:
        logging.info("========================================")
        logging.info('Diff file comparing result' + " : " + "< PASSED >")
        logging.info("========================================\n\n")
    logging.info("========================================")
    logging.info("\t\t  WARNING")
    logging.info("========================================")
    for l in range(len(warning)):
        if l not in warning_pass_index:
            logging.warning("\n"+warning[l])

# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #

def jira_ticket(username, passwd, ticket):

    issue = oempri.OEMPRI('jahuang', 'EhhBNR$&33', 'OEMPRI-25143') # username, password, jira ticket
    issue = oempri.OEMPRI(username, passwd, ticket) # username, password, jira ticket
    
    # -----Getting output file folder from JIRA ticket----- #
    for i in issue.fields['Review-Notes'].split('\n'):
        if 'Package' in i:
            package = i # Diff: \\\\jasmine2\\Projects-1\\Engineering\\Firmware\\Work\\jerliao\\WP76_Customer\\WP7611-1\\1105082_Qualified_OEMPRI-25143\\Diffs\r
            print(repr(package)) # Package: \\\\jasmine2\\Projects-1\\Engineering\\Firmware\\Work\\jerliao\\WP76_Customer\\WP7611-1\\1105082_Qualified_OEMPRI-25143\\1105082_9911219_WP7611-1_02.37.03.00_00_Qualified_001.000_000\r
        if 'Diff' in i:
            diff = i
            print(repr(diff))
        if 'Spreadsheet' in i:
            spreadsheet = i
            print(repr(spreadsheet)) # Spreadsheet: \\\\jasmine2\\Projects-1\\Engineering\\Firmware\\Work\\jerliao\\WP76_Customer\\WP7611-1\\1105082_Qualified_OEMPRI-25143\\1105082_WP7611-1_Qualified.xlsm\r
    
    # output file folder
    folder_xml_all = package.strip("Package: ").replace('\r','') # 
    folder_diff = diff.strip("Diff: ").replace('\r','') # 
    spreadsheet = spreadsheet.strip("Spreadsheet: ").replace('\r','') #
    
    tem = spreadsheet.split('\\')[-1] # tem example: 1105082_WP7611-1_Qualified.xlsm
    before_file_type = tem.find('.') # How many character in tem example before file type(xlsm)
    target_file_name = tem[:before_file_type] # So, the target is 1105082_WP7611-1_Qualified
    
    # output file path
    xml_file_path = folder_xml_all + "\\" + target_file_name + ".xml" # file folder + file name + file type
    diff_file_path = folder_diff + "\\" + "Differences-" + target_file_name + ".xml.diff"
    
    # -----Getting input file from JIRA ticket---- #
    for j in issue.list_attachment():
        if ".xls" in j:
            input_file = j
            issue.get_attachment(j, SCRIPT_REAL_PATH)
    input_file_path = SCRIPT_REAL_PATH + '\\' + input_file
    excel_info(input_file_path, xml_file_path)
    excel_info(input_file_path, diff_file_path)
    os.remove(SCRIPT_REAL_PATH + '\\' + input_file)
    logging.shutdown() # close logging
    
    issue.add_attachment(SCRIPT_REAL_PATH + '\\' + 'test.log') # upload to JIRA log file
    with open(SCRIPT_REAL_PATH + '\\' + 'test.log') as f: # open log file for uploading log to JIRA comment
        content = f.read()
    f.close() # close log file

    issue.add_comment("{noformat}\n" + content + "\n{noformat}") # upload to JIRA log file

# -------------------------------------------------------------------------------------------------------------------- #
# Read excel file for getting value through pandas because win32com module can not use in linux
# -------------------------------------------------------------------------------------------------------------------- #

def pandas_parser_excel_info(xlsm_path, xml_path):
    
    df = pandas.read_excel(xlsm_path, usecols=[0,1], keep_default_na=False) # keep_default_na=False
    search_key = []
    search_value = []
    Carriers_PRI_Files_value = []
    
    # Get Filed and value from excel
    i = 0
    while(i < int(df.shape[0])):
        if df[df.columns[0]][i] == 'Carriers PRI Files':
            j = i
            search_key.append(df[df.columns[0]][i])
            while (j < int(df.shape[0]) - 1):
                if df[df.columns[1]][j] != '':
                    Carriers_PRI_Files_value.append(df[df.columns[1]][j])
                j += 1
            search_value.append(Carriers_PRI_Files_value)
            i = j
        elif (df[df.columns[0]][i] == '' and df[df.columns[1]][i] == ''):
            i += 1
        else:
            search_key.append(df[df.columns[0]][i])
            search_value.append(df[df.columns[1]][i])
            i += 1
    
    # Compare xml
    result = parse_xml_info(xml_path, search_key, search_value)
    logging.info("==========")
    logging.info("< "+result+" >")
    logging.info("==========")
    print(result)
    print("End find excel")

# -------------------------------------------------------------------------------------------------------------------- #

# -------------------------------------------------------------------------------------------------------------------- #
def main():
    logging.basicConfig(filename=SCRIPT_REAL_PATH + '\\' + 'test.log', filemode="w",format='%(asctime)s %(levelname)-5s: %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=logging.DEBUG)
    # Parser Function # This needed to modify based on the requirement
    parser = argparse.ArgumentParser(description='pri_compare', formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-j', '--jira', metavar="<OEMPRI-XXX>", help="JIRA ticket", required=True)
    parser.add_argument('-u', '--user', metavar="<username>", help="JIRA account")
    parser.add_argument('-p', '--pwd', metavar="<password>", help="JIRA account")
    args = parser.parse_args()

    # check for jira
    if args.jira is not None:
        number = re.compile("^\d+$")
        if re.search(number, str(args.jira)):
            args.jira = "OEMPRI-%s" % args.jira
        else:
            if not re.search("OEMPRI-", str(args.jira)):
                logging.error("JIRA ticket is not correct (expected: OEMPRI-XXX): %s" % args.jira)
                raise ValueError
    
    # check username and password if not passed into script
    if args.user is None or args.pwd is None:
        args.user, args.pwd = common.get_reg_credentials()
        if args.user is None or args.pwd is None:
            logging.error("Registry key not set for user/pwd")
            raise ValueError
    # Start to get input and output file
    jira_ticket(args.user, args.pwd, args.jira)

if __name__ == "__main__":
    main()