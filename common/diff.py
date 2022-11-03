# ==================================================================================================================== #
# Script Name: diff
#
# Description: diff library to compare PRI packages
# ==================================================================================================================== #
import logging
import os
import sys
import re
import subprocess

import common


def get_file_category(file_path):
    """http://timgolden.me.uk/python/win32_how_do_i/get-document-summary-info.html"""
    import pythoncom
    from win32com.shell import shell
    from win32com import storagecon

    FORMATS = {
      pythoncom.FMTID_SummaryInformation: "SummaryInformation",
      pythoncom.FMTID_DocSummaryInformation: "DocSummaryInformation",
      pythoncom.FMTID_UserDefinedProperties: "UserDefinedProperties"
    }

    PROPERTIES = {
        pythoncom.FMTID_SummaryInformation: dict((getattr(storagecon, d), d) for d in dir(storagecon) if d.startswith("PIDSI_")),
        pythoncom.FMTID_DocSummaryInformation: dict((getattr (storagecon, d), d) for d in dir(storagecon) if d.startswith("PIDDSI_"))
    }

    def property_dict(property_set_storage, fmtid):
        STORAGE_READ = storagecon.STGM_READ | storagecon.STGM_SHARE_EXCLUSIVE
        properties = {}
        try:
            property_storage = property_set_storage.Open (fmtid, STORAGE_READ)
        except pythoncom.com_error as error: # except pythoncom.com_error, error:
            if error.strerror == 'STG_E_FILENOTFOUND':
                return {}
            else:
                raise ValueError

        for name, property_id, vartype in property_storage:
            if name is None:
                name = PROPERTIES.get(fmtid, {}).get(property_id, None)
            if name is None:
                name = hex(property_id)
            try:
                for value in property_storage.ReadMultiple([property_id]):
                    properties[name] = value
            #
            # There are certain values we can't read; they
            # raise type errors from within the pythoncom
            # implementation, thumbnail
            #
            except TypeError:
                properties[name] = None
        return properties

    def property_sets(file_path):
        pidl, flags = shell.SHILCreateFromPath(os.path.abspath (file_path), 0)
        property_set_storage = shell.SHGetDesktopFolder().BindToStorage(pidl, None, pythoncom.IID_IPropertySetStorage)
        for fmtid, clsid, flags, ctime, mtime, atime in property_set_storage:
            yield FORMATS.get(fmtid, str (fmtid)), property_dict(property_set_storage, fmtid)

            if fmtid == pythoncom.FMTID_DocSummaryInformation:
                fmtid = pythoncom.FMTID_UserDefinedProperties
                user_defined_properties = property_dict(property_set_storage, fmtid)

                if user_defined_properties:
                    yield FORMATS.get(fmtid, str(fmtid)), user_defined_properties

    for name, properties in property_sets(file_path):
        for piddsi_name, value in properties.items():
            if "PIDDSI_CATEGORY" in str(piddsi_name):
                return value


def generic_diff(new_file, old_file, output_path):

    filename = os.path.split(new_file)[1]
    diff_file = "Differences-%s.diff" % filename

    cmd = ["svn", "diff", "--old=%s" % old_file, "--new=%s" % new_file]
    logging.debug("Command: %s" % str(cmd))
    logging.info("Old: %s" % old_file)
    logging.info("New: %s" % new_file)

    svn_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = svn_process.communicate()[0]

    # create new file
    file_path = open(os.path.join(output_path, diff_file), "w", 0)

    for line in output:
        file_path.write(line.strip("\n"))

    file_path.close()
    logging.info("Return Code: %s" % svn_process.returncode)
    return svn_process.returncode


def xlsm_diff(new_file, old_file, output_path, tool_path=None, timeout=300):

    cmd = ['cscript', 'diff_plus.js', 'Diff', old_file, new_file, output_path, '//T:' + str(timeout), '//B']  # Timeout after 5 minutes if not done
    logging.debug("Command: " + str(cmd))
    logging.info("Old: %s" % old_file)
    logging.info("New: %s" % new_file)

    xlsm_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=tool_path)
    xlsm_process.communicate()
    logging.info("Return Code: %s" % xlsm_process.returncode)
    return xlsm_process.returncode


def find_xml_export(source, expected_type):
    xml_export = os.path.join(source, "XML-Export")
    found_xlsm = None
    xml_files = []

    customer_regex = re.compile("110\d\d\d\d_")
    devkit_regex = re.compile("910\d\d\d\d_")
    carrier_regex = re.compile("99\d\d\d\d\d_")
    ptcrb_regex = re.compile("550\d\d\d\d_")

    # check if xml_export folder exists
    if os.path.exists(xml_export):
        for content in os.listdir(xml_export):
            if content.endswith(".xlsm") and not content.startswith("~"):
                category = get_file_category(os.path.join(xml_export, content))

                # find the category string
                if category is not None:
                    if expected_type in str(category):
                        found_xlsm = os.path.join(xml_export, content)

                # fallback
                else:
                    if expected_type == "Customer":
                        if customer_regex.search(content) or devkit_regex.search(content):
                            found_xlsm = os.path.join(xml_export, content)
                    else:
                        if carrier_regex.search(content) or ptcrb_regex.search(content):
                            found_xlsm = os.path.join(xml_export, content)

        # find the xml that is associated to the found xlsm
        if found_xlsm is not None:
            logging.debug("File: %s" % found_xlsm)
            xml_files.append(found_xlsm)
            filename = os.path.split(found_xlsm)[1].split(".")[0]

            for content in os.listdir(xml_export):
                if content.endswith(".xml") and filename in content:
                    logging.debug("File: %s" % content)
                    xml_files.append(os.path.join(xml_export, content))

    return xml_files


def find_efs_nvup(source, expected_type):
    efs_nvup = os.path.join(source, "EFS-NVUP-Files")
    efs_files = []

    if os.path.exists(efs_nvup):
        nvup_efs = os.listdir(efs_nvup)
        for content in nvup_efs:
            if content.endswith(".txt") and not "-field" in content:
                if expected_type == "Carrier":
                    if "NVUP-9999999" in content:
                        logging.debug("File: %s" % content)
                        efs_files.append(os.path.join(efs_nvup, content))
                else:
                    if "NVUP-9999999" not in content:
                        logging.debug("File: %s" % content)
                        efs_files.append(os.path.join(efs_nvup, content))

    return efs_files
