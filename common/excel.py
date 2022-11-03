# ==================================================================================================================== #
# Script Name: excel_lib
#
# Description: common misc library for PRI
# ==================================================================================================================== #
import logging
import sys
import datetime
import re
import argparse
import os
import time

try:
    import win32com.client
except ImportError:
    logging.error("Please Install win32com")
    raise ImportError


# ==================================================================================================================== #
#  Class Name: ExcelApp
#
# Description: Creates an Excel Application process
# ==================================================================================================================== #
class ExcelApp(object):
    logger = logging.getLogger("ExcelApp")
    opened = None

    def __init__(self):
        try:
            self.excel = None
            self.excel = win32com.client.DispatchEx("Excel.Application")
        except Exception as e:
            self.logger.error(str(e))
            self.logger.error("Failed Excel.Application, retrying...")
            time.sleep(5)
            try:
                self.excel = None
                self.excel = win32com.client.DispatchEx("Excel.Application.15")
            except Exception as e:
                self.logger.error(str(e))
                self.logger.error("Failed Excel.Application.15, retrying...")
                time.sleep(5)
                try:
                    self.excel = None
                    self.excel = win32com.client.DispatchEx("{00024500-0000-0000-C000-000000000046}")
                except Exception as e:
                    self.logger.error(str(e))
                    self.logger.error("Unable to run Excel COM object, please re-run again!")
                    sys.exit(-1)
        self.excel.Visible = False
        self.excel.DisplayAlerts = False
        self.excel.EnableEvents = False
        self.book = None

    def open(self, file_path):
        try:
            self.book = self.excel.Workbooks.Open(file_path)
            self.opened = file_path
            bar = "-" * len(" %s " % self.opened)
            self.logger.info(bar)
            self.logger.info(" %s " % self.opened)
            self.logger.info(bar)
        except Exception as e:
            self.logger.error(str(e))
            sys.exit(-1)

    def add(self, file_path):
        self.book = self.excel.Workbooks.Add()
        self.opened = file_path

    def close(self):
        self.book.Saved = True
        self.book.Close()
        self.book = None

    def save(self):
        if not os.path.exists(self.opened):
            if self.opened.endswith(".xlsm"):
                file_format = 18
            else:
                file_format = None
            self.book.SaveAs(self.opened, FileFormat=file_format)
        else:
            self.book.Save()

    def quit(self):
        self.excel.DisplayAlerts = True
        self.excel.EnableEvents = True
        self.excel.Quit()
        self.excel = None
        del self.excel

    def add_sheet(self, name):
        count = self.book.Sheets.Count
        worksheet = self.book.Worksheets.Add(self.book.Sheets(count))
        worksheet.Name = name

    def remove_sheet(self, name):
        total_sheets = self.book.Sheets.Count
        for index in range(1, total_sheets + 1):
            if self.book.Sheets(index).Name == name:
                self.book.Sheets(index).Delete()

    def write(self, tab_name, row, column, value):
        worksheet = self.book.Worksheets(tab_name)
        worksheet.Cells(row, column).Value = value
        # self.logger.debug("Write (Row: %s, Column: %s): %s" % (row, column, value))

    def write_row(self, tab_name, row, values):
        worksheet = self.book.Worksheets(tab_name)
        for column_index in range(1, len(values) + 1):
            worksheet.Cells(row, column_index).Value = values[column_index - 1]
        # self.logger.debug("Write (Row: %s): %s" % (row, values))

    def read(self, tab_name, row, column):
        worksheet = self.book.Worksheets(tab_name)
        value = worksheet.Cells(row, column).Value
        # self.logger.debug("Read (Row: %s, Column: %s): %s" % (row, column, value))
        return value

    def read_row(self, tab_name, row):
        worksheet = self.book.Worksheets(tab_name)
        used = worksheet.UsedRange
        ncols = used.Column + used.Columns.Count
        row_value = []
        for column_index in range(1, ncols):
            value = worksheet.Cells(row, column_index).Value
            row_value.append(value)
        #self.logger.debug("Read (Row: %s): %s" % (row, row_value))
        return row_value

    def find(self, tab_name, value, exact=True):
        worksheet = self.book.Worksheets(tab_name)
        all_values = []
        current_value = worksheet.Cells.Find(value)
        if current_value is not None:
            first_address = current_value.Address
            all_values.append([current_value, current_value.Address])
            while True:
                current_value = worksheet.Cells.FindNext(current_value)
                if first_address == current_value.Address:
                    break
                else:
                    all_values.append([current_value, current_value.Address])
        for found_value in all_values:
            if exact:
                if value == str(found_value[0]):
                    # self.logger.debug("Found (%s): Row: %s, Column: %s" % (found_value[0], found_value[0].row, found_value[0].column))
                    return found_value[0].row, found_value[0].column
            else:
                if value in str(found_value[0]):
                    # self.logger.debug("Found (%s): Row: %s, Column: %s" % (found_value[0], found_value[0].row, found_value[0].column))
                    return found_value[0].row, found_value[0].column

    def find_last_row(self, tab_name):
        sheet = self.book.Worksheets(tab_name)
        used = sheet.UsedRange
        nrows = used.Row + used.Rows.Count - 1
        while self.read(tab_name, nrows, 1) is None:
            nrows -= 1
        # self.logger.debug("Last Row: %s" % nrows)
        return nrows

    def remove_row(self, tab_name, row):
        worksheet = self.book.Worksheets(tab_name)
        range = worksheet.Cells(row, 1).EntireRow
        range.Delete()
        # self.logger.debug("Row %s deleted" % row)

    def remove(self, tab_name, row, column):
        worksheet = self.book.Worksheets(tab_name)
        range = worksheet.Cells(row, column)
        range.Delete()
        # self.logger.debug("Row %s, Column %s deleted" % (row, column))

    def run_vb_code(self, function):
        self.excel.Application.Run(function)


# ==================================================================================================================== #
#  Class Name: Spreadsheet
#
# Description:
# ==================================================================================================================== #
class PRISheet(ExcelApp):
    logger = logging.getLogger("Spreadsheet")

    def __init__(self, file_path=None, visible=False):
        super(PRISheet, self).__init__()
        self.excel.Visible = visible
        self.type = None
        self.package = None
        self.sku = None
        self.part_number = None
        self.model = None
        self.firmware = None
        self.name = None
        self.pri_version = None
        self.message = None
        self.secure_boot = None
        if file_path is not None:
            self.open(file_path)

    def open(self, file_path):
        super(PRISheet, self).open(file_path)
        # find if PRI is Customer/Carrier
        self.type = self.get_type()
        # assign the rest
        self.package = self.read_package()
        self.model = self.get_model()
        self.sku = self.package.split("_")[0]
        self.part_number = self.package.split("_")[1]
        self.firmware = self.package.split("_")[3]
        self.name = self.package.split("_")[5]
        self.pri_version = "%s_%s" % (self.package.split("_")[6], self.package.split("_")[7])
        self.message = ""
        self.secure_boot = self.get_secure_boot()

    def get_type(self):
        search_part = self.find("Summary", "PRI Package Part Number")
        if search_part is not None:
            search_sku = self.find("Summary", "PRI Package SKU")
            if search_sku is not None:
                return "Customer"
            return "Carrier"

    def get_model(self):
        if self.type == "Customer":
            row, col = self.find("Summary", "Product")
            search_model = self.read("Summary", row, col+1)
        else:
            search_model = self.package.split("_")[2]
        return search_model

    # meant for 9x30, 9x06, 9x07, 9x50
    def get_template_revision(self):
        if self.type == "Customer":
            content = self.excel.Range("Table33").Value
        else:
            content = self.excel.Range("Table9").Value
        return content

    # meant for 9x30, 9x06, 9x07, 9x50
    def get_changes_revision(self):
        if self.type == "Customer":
            content = self.excel.Range("Table34").Value
        else:
            content = self.excel.Range("Table14").Value
        return content

    def find_previous_revision(self):
        try:
            content = self.get_changes_revision()
            length = len(content) - 1
            if length == 0:
                prev_rev = None
            else:
                prev_rev = content[length - 1][0]
        except Exception:
            last_row = self.find_last_row("Revisions")
            prev_rev = str(self.read("Revisions", last_row - 1, 1))

        # try to cast the string value (to determine if there is any char in front)
        try:
            int(prev_rev[0][:1])
            prev_version = prev_rev
        except ValueError:
            regex = re.compile("\d.\d")
            if regex.search(prev_rev[1:]):
                prev_version = prev_rev[1:]
            else:
                prev_version = None
        except TypeError:
            prev_version = None

        # check if there is _ in the string
        if prev_version is not None:
            if "_" not in prev_version:
                pri = prev_version.split(".")
                major = int(pri[0])
                minor = int(pri[1])
                pri_major = "{0:03}".format(major)
                pri_minor = "{0:03}".format(minor)
                pri_version = "%s.%s_000" % (pri_major, pri_minor)
            else:
                pri = prev_version.split("_")
                build = pri[1]
                pri_ver = pri[0].split(".")
                major = int(pri_ver[0])
                minor = int(pri_ver[1])
                pri_major = "{0:03}".format(major)
                pri_minor = "{0:03}".format(minor)
                pri_version = "%s.%s_%s" % (pri_major, pri_minor, build)
        else:
            pri_version = prev_version
        self.logger.debug("Read Previous Version (Revisions->Last Row-1): %s" % pri_version)
        return pri_version

    def read_package(self):
        nvup_row, nvup_col = self.find("Prefs", "NVUPVersion")
        folder = self.read("Prefs", nvup_row + 1, nvup_col)
        self.logger.debug("Read Package (Prefs->NVUPVersion): %s" % folder)
        return str(folder)

    def get_secure_boot(self):
        try:
            sb_row, sb_col = self.find("Summary", "SecureBoot")
            sb = self.read("Summary", sb_row, sb_col + 1)
        except Exception:
            sb = "Disabled"
        return str(sb)

    def read_fact(self):
        fact_list = []
        fact_row, fact_col = self.find("Package", "FACT")
        fact_value = self.read_row("Package", fact_row)
        for fact in fact_value:
            fact_list.append(str(fact))
        self.logger.debug("Read FACT (Package->FACT): %s" % fact_list)
        return fact_list

    def read_fdt(self):
        fdt_list = []
        fdt_row, fdt_col = self.find("Package", "FDT")
        fdt_value = self.read_row("Package", fdt_row)
        for fdt in fdt_value:
            fdt_list.append(str(fdt))
        self.logger.debug("Read FDT (Package->FDT): %s" % fdt_list)
        return fdt_list

    def read_cmu(self):
        cmu_list = []
        cmu_row, cmu_col = self.find("Package", "CMU")
        cmu_value = self.read_row("Package", cmu_row)
        for cmu in cmu_value:
            cmu_list.append(str(cmu))
        self.logger.debug("Read CMU (Package->CMU): %s" % cmu_list)
        return cmu_list

    def read_latest_changes(self):
        try:
            content = self.get_changes_revision()
            length = len(content) - 1
            changes = content[length]
        except Exception:
            last_row = self.find_last_row("Revisions")
            changes = self.read_row("Revisions", last_row)
        self.logger.debug("Read Latest Changes (Revisions->Last Row): %s" % str(changes))
        return changes

    def update_nvextra(self, version, file_name, location):
        nvextra_row, nvextra_col = self.find("Package", "NVExtra")

        prev_value = self.read_row("Package", nvextra_row)
        logging.info("Prev. NVExtra: %s" % str(prev_value))

        self.write_row("Package", nvextra_row, ["NVExtra", version, file_name, "No", location])

        curr_value = self.read_row("Package", nvextra_row)
        logging.info("Curr. NVExtra: %s" % str(curr_value))

        self.message += "Update NVExtra.xml to %s. " % version

    def update_parsertool(self, version, file_name, location):
        parsertool_row, parsertool_col = self.find("Package", "PRI_Parser")

        prev_value = self.read_row("Package", parsertool_row)
        logging.info("Prev. ParserTool: %s" % str(prev_value))

        self.write_row("Package", parsertool_row, ["PRI_Parser", version, file_name, "No", location])

        curr_value = self.read_row("Package", parsertool_row)
        logging.info("Curr. ParserTool: %s" % str(curr_value))

        self.message += "Update ParserTool to %s. " % version

    def update_fdt(self, version, file_name, location):
        fdt_row, fdt_col = self.find("Package", "FDT")

        prev_value = self.read_row("Package", fdt_row)
        logging.info("Prev. FDT: %s" % str(prev_value))

        self.write_row("Package", fdt_row, ["FDT", version, file_name, "Yes", location])

        curr_value = self.read_row("Package", fdt_row)
        logging.info("Curr. FDT: %s" % str(curr_value))

        self.message += "Update FDT to %s. " % version

    def update_fact(self, version, file_name, location):
        fact_row, fact_col = self.find("Package", "FACT")

        prev_value = self.read_row("Package", fact_row)
        logging.info("Prev. FACT: %s" % str(prev_value))

        self.write_row("Package", fact_row, ["FACT", version, file_name, "Yes", location])

        curr_value = self.read_row("Package", fact_row)
        logging.info("Curr. FACT: %s" % str(curr_value))

        self.message += "Update FACT to %s. " % version

    def update_cmu(self, version, file_name, location):
        cmu_row, cmu_col = self.find("Package", "CMU")

        prev_value = self.read_row("Package", cmu_row)
        logging.info("Prev. CMU: %s" % str(prev_value))

        self.write_row("Package", cmu_row, ["CMU", version, file_name, "Yes", location])

        curr_value = self.read_row("Package", cmu_row)
        logging.info("Curr. CMU: %s" % str(curr_value))

        self.message += "Update CMU to %s. " % version

    def update_carrier_firmware(self, version, location):
        # Appl Firmware
        applz = self.find("Package", "Appl Firmware")

        # Check for Appl Firmware (does not exist on WP)
        if applz is not None:
            applz_row, applz_col = applz
            prev_appl = self.read_row("Package", applz_row)
            logging.info("Prev. Appl FW: %s, %s" % (str(prev_appl[3]), str(prev_appl[2])))
            self.write("Package", applz_row, applz_col + 3, location)
            curr_appl = self.read_row("Package", applz_row)
            logging.info("Curr. Appl FW: %s, %s" % (str(curr_appl[3]), str(curr_appl[2])))
        
        # Taop Firmware
        taop = self.find("Package", "TAOP Firmware")

        # Check for Taop Firmware (exist of SDX55)
        if taop is not None:
            taop_row, taop_col = taop
            prev_taop = self.read_row("Package", taop_row)
            logging.info("Prev. Taop FW: %s, %s" % (str(prev_taop[3]), str(prev_taop[2])))
            self.write("Package", taop_row, taop_col + 3, location)
            curr_taop = self.read_row("Package", taop_row)
            logging.info("Curr. Taop FW: %s, %s" % (str(curr_taop[3]), str(curr_taop[2])))

        # Boot Firmware
        boot_row, boot_col = self.find("Package", "Boot Firmware")
        prev_boot = self.read_row("Package", boot_row)
        logging.info("Prev. Boot FW: %s, %s" % (str(prev_boot[3]), str(prev_boot[2])))
        self.write("Package", boot_row, boot_col + 3, location)
        curr_boot = self.read_row("Package", boot_row)
        logging.info("Curr. Boot FW: %s, %s" % (str(curr_boot[3]), str(curr_boot[2])))

        # Modem Firmware
        modem_row, modem_col = self.find("Package", "Modem Firmware")
        prev_modem = self.read_row("Package", modem_row)
        logging.info("Prev. Modem FW: %s, %s" % (str(prev_modem[3]), str(prev_modem[2])))
        self.write("Package", modem_row, modem_col + 3, location)
        curr_modem = self.read_row("Package", modem_row)
        logging.info("Curr. Modem FW: %s, %s" % (str(curr_modem[3]), str(curr_modem[2])))

        # Update Firmware
        fw_row, fw_col = self.find("Summary", "PRI FW version")
        prev_fw = self.read_row("Summary", fw_row)
        logging.info("Prev. FW: %s" % str(prev_fw[1]))
        self.write("Summary", fw_row, fw_col + 1, version)
        curr_fw = self.read_row("Summary", fw_row)
        logging.info("Curr. FW: %s" % str(curr_fw[1]))

        self.message += "Update Firmware to %s. " % version

    def update_customer_firmware(self, version, fw_location, pri_list):

        carrier_info = self.excel.Range("Table99").Value
        start_row = self.excel.Range("Table99").Row
        CARRIER = 1
        DEFAULT_CARRIER = 2
        EXCEL_NAME = 3
        EXCEL_LOCATION = 4
        CARRIER_LOCATION = 5
        FIRMWARE_NAME = 6
        NVUP_NAME = 7
        AUTO_PROVISION = 8

        default_carrier = None
        default_config = None
        row = int(start_row)

        for carrier in carrier_info:
            for pri in pri_list:
                if carrier[0] == pri.name:
                    # find the default value
                    if carrier[1] is not None:
                        default_carrier = carrier[0]
                        default_config = "%s_%s" % (carrier[0], pri.pri_version)

                    file_path, excel = os.path.split(pri.file_location)

                    # Excel_Name
                    self.write("Package", row, EXCEL_NAME, excel)

                    # Excel_Location
                    self.write("Package", row, EXCEL_LOCATION, file_path + "\\")

                    # Carrier_Location
                    driver_release = os.path.join(file_path, pri.package, "Driver-Release")
                    self.write("Package", row, CARRIER_LOCATION, driver_release)

                    # Firmware_Name and NVUP_Name
                    for content in os.listdir(driver_release):
                        if content.endswith(".cwe"):
                            self.write("Package", row, FIRMWARE_NAME, content)
                        elif content.endswith(".nvu"):
                            self.write("Package", row, NVUP_NAME, content)
            # increment counter of row
            row += 1

        # Update Firmware
        fw_row, fw_col = self.find("Summary", "PRI FW version")
        prev_fw = self.read_row("Summary", fw_row)
        logging.info("Prev. FW: %s" % str(prev_fw[1]))
        self.write("Summary", fw_row, fw_col + 1, version)
        curr_fw = self.read_row("Summary", fw_row)
        logging.info("Curr. FW: %s" % str(curr_fw[1]))

        yocto = self.find("Package", "Yocto Firmware")

        if yocto is not None:
            yocto_row, yocto_col = yocto
            prev_yocto = self.read("Package", yocto_row, yocto_col + 3)
            logging.info("Prev. Yocto: %s" % prev_yocto)
            self.write("Package", yocto_row, yocto_col + 3, fw_location)
            curr_yocto = self.read("Package", yocto_row, yocto_col + 3)
            logging.info("Curr. Yocto: %s" % curr_yocto)

        pref_fw = "preferredfwversion:%s" % version
        pref_name = "preferredcarriername:%s" % default_carrier
        pref_pri = "preferredconfigname:%s" % default_config
        cal_fw = "calculatedfwversion:%s" % version
        cal_name = "calculatedcarriername:%s" % default_carrier
        cal_pri = "calculatedconfigname:%s" % default_config
        curr_fw = "currentfwversion:%s" % version
        curr_name = "currentcarriername:%s" % default_carrier
        curr_pri = "currentconfigname:%s" % default_config

        impref = "AT!IMPREF?=!IMPREF:%s%s%s%s%s%s%s%s%s" % (pref_fw, pref_name, pref_pri, cal_fw, cal_name, cal_pri, curr_fw, curr_name, curr_pri)

        impref_row, impref_col = self.find("Factory", "Checks image preference")
        prev_impref = self.read_row("Factory", impref_row)
        logging.info("Prev. Impref: %s" % str(prev_impref[1]))

        self.write("Factory", impref_row, impref_col + 1, impref)

        curr_impref = self.read_row("Factory", impref_row)
        logging.info("Curr. Impref: %s" % str(curr_impref[1]))

    def update_pri_version(self, external, build=None):
        pri_row, pri_col = self.find("Summary", "PRI Version")
        prev_pri_version = str(self.read("Summary", pri_row, pri_col + 1))
        build_row, build_col = self.find("Summary", "PRI Build version")
        prev_pri_build = str(self.read("Summary", build_row, build_col + 1))
        logging.info("Prev. PRI Version: %s, Build: %s" % (str(prev_pri_version), str(prev_pri_build)))

        # PRI version
        pri_major, pri_minor = prev_pri_version.split(".")

        if len(pri_minor) == 2:
            pri_minor += "0"
        if len(pri_minor) == 1:
            pri_minor += "00"
        temp_major = int(pri_major)
        temp_minor = int(pri_minor)

        if external:
            temp_minor += 1

        # PRI Build
        if build is None:
            temp_build = int(prev_pri_build)
        else:
            temp_build = int(build)

        # create new PRI version
        new_pri_version = "%03d.%03d" % (temp_major, temp_minor)
        self.write("Summary", pri_row, pri_col + 1, new_pri_version)
        curr_pri_version = self.read("Summary", pri_row, pri_col + 1)

        # create new PRI Build version
        new_build_version = "%03d" % temp_build
        self.write("Summary", build_row, build_col + 1, new_build_version)
        curr_pri_build = self.read("Summary", build_row, build_col + 1)

        logging.info("Curr. PRI Version: %s, Build: %s" % (str(curr_pri_version), str(curr_pri_build)))

        # for specifically Carriers, update the Carrier tab
        if self.type == "Carrier":
            carrier_row, carrier_col = self.find("Carrier", "Carrier PRI Version")
            prev_carrier = self.read("Carrier", carrier_row, carrier_col + 1)
            logging.info("Prev. Carrier PRI Version: %s" % prev_carrier)

            new_carrier_version = "%02d%02d" % (temp_major, temp_minor)
            self.write("Carrier", carrier_row, carrier_col + 1, new_carrier_version)
            curr_carrier = self.read("Carrier", carrier_row, carrier_col + 1)
            logging.info("Curr. Carrier PRI Version: %s" % curr_carrier)

        # new PRI version
        new_pri = "%s" % new_pri_version
        if new_build_version != "000":
            new_pri += "_%s" % new_build_version

        return new_pri

    def update_latest_revision(self, external, build, message):
        today_date = datetime.datetime.now()
        last_row = self.find_last_row("Revisions")
        revision = self.update_pri_version(external, build)
        self.write("Revisions", last_row + 1, 1, "v%s" % revision)
        self.write("Revisions", last_row + 1, 2, "Jenkins")
        self.write("Revisions", last_row + 1, 3, "%s/%s/%s" % (today_date.month, today_date.day, today_date.year))
        self.write("Revisions", last_row + 1, 4, message)
        self.read_row("Revisions", last_row + 1)

    def update_pri(self, nvextra, parsertool, fdt, fact, cmu, firmware, external, build, ticket):

        # Update the Tools section
        if nvextra is not None:
            self.update_nvextra(nvextra[0], nvextra[1], nvextra[2])
        if parsertool is not None:
            self.update_parsertool(parsertool[0], parsertool[1], parsertool[2])
        if cmu is not None:
            self.update_cmu(cmu[0], cmu[1], cmu[2])
        if fdt is not None:
            self.update_fdt(fdt[0], fdt[1], fdt[2])
        if fact is not None:
            self.update_fact(fact[0], fact[1], fact[2])

        # Update the FW section
        if self.type == "Carrier":
            if firmware is not None:
                if len(firmware) == 2:
                    self.update_carrier_firmware(firmware[0], firmware[1])
                else:
                    raise Exception

        # Update the PRI version
        if ticket is not None:
            self.update_latest_revision(external, build, ticket + "\n" + self.message)
        else:
            self.update_latest_revision(external, build, self.message)

    def update_customer_default_carrier(self, update_carrier_info):
        carrier_info = self.excel.Range("Table99").Value
        start_row = self.excel.Range("Table99").Row
        CARRIER = 1
        DEFAULT_CARRIER = 2
        EXCEL_NAME = 3
        EXCEL_LOCATION = 4
        CARRIER_LOCATION = 5
        FIRMWARE_NAME = 6
        NVUP_NAME = 7
        AUTO_PROVISION = 8

        default_carrier = None
        default_config = None
        row = int(start_row)

        for carrier in carrier_info:
            if carrier[1] is not None:
                # Excel File Name #
                self.write("Package", row, EXCEL_NAME, update_carrier_info["Excel File Name"])
                # Excel Location #
                self.write("Package", row, EXCEL_LOCATION, update_carrier_info["Excel File Location"])
                # Carrier Location #
                self.write("Package", row, CARRIER_LOCATION, update_carrier_info["Driver Release Link"])
                # Firmware Name # 
                self.write("Package", row, FIRMWARE_NAME, update_carrier_info["Carrier Firmware"])
                # NVUP Name #
                self.write("Package", row, NVUP_NAME, update_carrier_info["Carrier NVU"])
        self.run_vb_code("getCarrier")
                
    


# ==================================================================================================================== #
#
# Excel properties
#
# ==================================================================================================================== #
########################################################################################################################
#   Function Name: pri_information                                                                                     #
#                                                                                                                      #
#     Description:                                                                                                     #
#                                                                                                                      #
#    Parameter(s): file_path                                                                                           #
#                                                                                                                      #
# Return Value(s):                                                                                                     #
########################################################################################################################
def pri_information(file_path):
    pri_list = []

    excel = PRISheet()
    for pri_file in file_path:
        if os.path.isfile(pri_file):
            excel.open(pri_file)
            prev_pri = excel.find_previous_revision()
            fdt_row = excel.read_fdt()
            latest_changes = excel.read_latest_changes()
            excel.close()

            pri = argparse.Namespace()
            pri.sku = excel.sku
            logging.info("SKU: %s" % pri.sku)
            pri.part_number = excel.part_number
            logging.info("Part Number: %s" % pri.part_number)
            pri.pri_version = excel.pri_version
            logging.info("PRI Version: %s" % pri.pri_version)
            pri.model = excel.model
            logging.info("Model: %s" % pri.model)
            pri.name = excel.name
            logging.info("Name: %s" % pri.name)
            pri.firmware = excel.firmware
            logging.info("Firmware: %s" % pri.firmware)
            pri.type = excel.type
            logging.info("Type: %s" % pri.type)
            pri.package = excel.package
            logging.info("Package: %s" % pri.package)
            pri.secure_boot = excel.secure_boot
            logging.info("SecureBoot: %s" % pri.secure_boot)
            pri.fdt_row = fdt_row
            pri.prev_pri = prev_pri
            pri.latest_changes = latest_changes[3]
            pri.file_location = pri_file

            pri_list.append(pri)
    excel.quit()

    return pri_list


########################################################################################################################
#   Function Name: modify_pri                                                                                          #
#                                                                                                                      #
#     Description:                                                                                                     #
#                                                                                                                      #
#    Parameter(s): file_path                                                                                           #
#                                                                                                                      #
# Return Value(s):                                                                                                     #
########################################################################################################################
def modify_carrier_pri(file_path, nvextra, parsertool, fdt, firmware, external, build, jira_summary=None):
    logging.info("======================")
    logging.info("| Modify Carrier PRI |")
    logging.info("======================")

    if nvextra is None and parsertool is None and fdt is None and firmware is None:
        logging.info("No need to modify spreadsheet")
    else:
        # display to screen what was in text file
        logging.info("NVExtra: %s" % str(nvextra))
        logging.info("ParserTool: %s" % str(parsertool))
        logging.info("FDT: %s" % str(fdt))
        logging.info("Firmware: %s" % str(firmware))

        # create excel object, and update the information
        excel = PRISheet()
        for xlsm in file_path:
            if os.path.isfile(xlsm):
                excel.open(xlsm)
                excel.update_pri(nvextra, parsertool, fdt, None, None, firmware, external, build, jira_summary)
                excel.save()
                excel.close()
        excel.quit()


########################################################################################################################
#   Function Name: modify_pri                                                                                          #
#                                                                                                                      #
#     Description:                                                                                                     #
#                                                                                                                      #
#    Parameter(s): file_path                                                                                           #
#                                                                                                                      #
# Return Value(s):                                                                                                     #
########################################################################################################################
def modify_customer_pri(file_path, firmware, carrier_path, external, build, jira_summary=None):
    logging.info("=======================")
    logging.info("| Modify Customer PRI |")
    logging.info("=======================")

    logging.info("Firmware: %s" % str(firmware))

    version, location = firmware

    pri_list = pri_information(carrier_path)

    logging.info("============")
    logging.info("| Customer |")
    logging.info("============")
    # create excel object, and update the information
    excel = PRISheet()
    for xlsm in file_path:
        excel.open(xlsm)
        excel.update_customer_firmware(version, location, pri_list)
        excel.update_latest_revision(external, build, jira_summary)
        excel.save()
        excel.close()
    excel.quit()


def modify_customer_default_pri(file_path, carrier_info):
    """ Modify Customer Default PRI """
    logging.info("===============================")
    logging.info("| Modify Customer Default PRI |")
    logging.info("===============================")

    logging.info("Input: %s" % str(file_path))
    logging.info("Carrier Info: %s" % carrier_info)
    excel = PRISheet()
    for xlsm in file_path:
        excel.open(xlsm)
        excel.update_customer_default_carrier(carrier_info)     
        excel.update_latest_revision(False, "999", "Test Package Generated.")
        excel.save()
        excel.close()
    excel.quit()    