# ==================================================================================================================== #
# Script Name: svn
#
# Description: script to execute SVN commands from command line
# ==================================================================================================================== #
import subprocess
import os
import logging
import sys
import distutils.dir_util as dir_util

def call_cmd(cmd, cwd=None):
    """
    Function Name: Call_cmd
    Input:
        cmd - command to be executed
    Output: none
    Description: Creates subprocess to execute shell command. Exits if process fails
    """
    logging.info(cmd)
    # start subprocess to launch command line svn
    svn_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
    output, error = svn_proc.communicate()
    logging.debug(output)

    # check if it failed
    if svn_proc.returncode > 0:
        logging.error("%s" % error)
        sys.exit(1)

    return svn_proc.returncode


def checkout(svn_remote_path, output, revision=None):
    """
    Function Name: checkout
    Input:
        svn_remote_path - path in SVN to checkout
        output - output path to checkout to from SVN
    Output: none
    Description: Creates subprocess to execute shell command. Exits if process fails
    """
    cmd = "svn checkout %s %s" % (svn_remote_path, output)
    if revision is not None:
        cmd += " -r %s" % revision
    call_cmd(cmd)


def export(svn_local_file, output):
    """
    Function Name: export
    Input:
        svn_local_file - path to excel spreadsheet to export
        output - output path to export from svn
    Output: none
    Description: Creates subprocess to execute shell command. Exits if process fails
    """
    cmd = "svn export --force %s %s" % (svn_local_file, output)
    call_cmd(cmd)


def add(svn_local_file):
    """
    Function Name: add
    Input:
        svn_local_file - path to excel spreadsheet in local svn directory to be checked in
    Output: none
    Description: Adds file to remote repository
    """
    cmd = "svn add %s --parents" % svn_local_file
    call_cmd(cmd)


def add_to_changelist(svn_local_file, ticket):
    """
    Function Name: add_to_changelist
    Input:
        svn_local_file - path to excel spreadsheet in local svn directory to be checked in
        commit_msg - commit message
    Output: none
    Description: Adds file to a changelist to commit multiple files in one commit
    """
    cmd = "svn changelist %s %s" % (ticket, svn_local_file)
    call_cmd(cmd)


def commit(svn_local_file, changes):
    """
    Function Name: commit
    Input:
        svn_local_file - path to excel spreadsheet in local svn directory to be checked in
    Output: none
    Description: Commits file to remote repository
    """
    cmd = "svn commit %s -m \"%s\"" % (svn_local_file, changes)
    call_cmd(cmd)


def commit_changelist(root_path, ticket, summary):
    """
    Function Name: commit_changelist
    Input:
        commit_msg - commit message
    Output: none
    Description: Commits changelist
    """
    cmd = "svn commit --changelist %s -m \"%s\"" % (ticket, "[%s] - %s" % (ticket, summary))
    call_cmd(cmd, root_path)


def update(svn_local_file):
    """
    Function Name: update
    Input:
        svn_local_file - path to folder in local svn directory that contains the file to be checked in
    Output: none
    Description: Updates local svn working directory
    """
    if os.path.isdir(svn_local_file):
        cmd = "svn update %s" % svn_local_file
    else:
        cmd = "svn update %s" % os.path.dirname(svn_local_file)
    call_cmd(cmd)


def create_new_svn_dir(svn_remote_dir, svn_local_dir, commit_msg):
    """
    Function Name: create_new_svn_dir
    Input:
        svn_remote_dir - path to remote folder to be created
        svn_local_dir - path to local svn directory to be created
        commit_msg - commit message
    Output: none
    Description: Creates new directory in remote svn repository and checks out the directory to local workspace
    """
    if not os.path.exists(svn_local_dir):
        dir_util.mkpath(svn_local_dir)
        cmd = "svn mkdir %s -m \"%s\"" % (svn_remote_dir, commit_msg)
        call_cmd(cmd)
        checkout(svn_remote_dir, svn_local_dir)


def update_author(file_path, email):
    """
    Function Name: upate_auhor
    Input:
        filepath - path to checked-in file in remote repository
        email - email address of commit author
    Output: none
    Description: Updates the author of the specified commit
    """
    cmd = "svn log %s --limit 1" % file_path
    logging.info(cmd)
    svn_info = subprocess.check_output(cmd, shell=True)
    svn_info_list = svn_info.split('\n')
    revision = svn_info_list[1].split(' ')[0]
    revision = revision[1:]
    author = email.split('@')[0]
    cmd = "svn propset --revprop -r %s svn:author %s" % (revision, author)
    if os.path.isdir(file_path):
        call_cmd(cmd, file_path)
    else:
        call_cmd(cmd, os.path.dirname(file_path))


def tag(svn_local_file, svn_remote_dir, pri_type, version, ticket, email, commit_msg):
    """
    Function Name: TAG
    Input:
        svn_remote_dir - path to remote folder to be created
        svn_local_file - path to excel spreadsheet in local svn directory to be checked in
        commit_msg - commit message
        version - pri revision
    Output: none
    Description: Tags the specified commit
    """
    if 'BRANCHES' in svn_local_file:
        local_TAG_path = os.path.join(svn_local_file.split("BRANCHES")[0], "TAGS")
        remote_TAG_path = svn_remote_dir.replace('BRANCHES', 'TAGS')
        if pri_type == 'Customer':
            svn_local_file_base = '_'.join(os.path.basename(svn_local_file).split('_', 3)[:3]) + '.xlsm'  # SKU_DEVICE_CUSTOMER
        else:
            if "SDX55" in os.path.basename(svn_local_file):
                svn_local_file_base = '_'.join(os.path.basename(svn_local_file).split('_', 3)[:3]) + '.xlsm'  # SDX55_PARTNUM_CARRIER
            else:
                svn_local_file_base = '_'.join(os.path.basename(svn_local_file).split('_', 2)[:2]) + '.xlsm'  # PARTNUM_CARRIER
    else:
        local_TAG_path = "%s" % os.path.join(os.path.dirname(svn_local_file), 'TAGS')
        remote_TAG_path = "%s" % svn_remote_dir + "TAGS" + "/"
        svn_local_file_base = os.path.basename(svn_local_file)

    logging.info("SVN: %s" % remote_TAG_path)
    logging.info("Local: %s" % local_TAG_path)
    logging.debug("Base: %s" % svn_local_file_base)

    # if there is no TAG folder, create TAG folder
    if not os.path.exists(local_TAG_path):
        create_new_svn_dir(remote_TAG_path, local_TAG_path, commit_msg)

    # recreate TAG + VERSION
    filename, ext = os.path.splitext(svn_local_file_base)
    TAG_filename = "%s_%s" % (filename, version) + ext
    remote_TAG_file = "%s" % remote_TAG_path + TAG_filename

    cmd = "svn copy %s %s -m \"%s\"" % (svn_remote_dir + os.path.basename(svn_local_file), remote_TAG_file, "[%s] - Create TAG %s" % (ticket, version))
    call_cmd(cmd)
    update(local_TAG_path)
    if email is not None:
        update_author(local_TAG_path, email)


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

if __name__ == "__main__":
    logging.basicConfig(format='[ %(asctime)s ] %(levelname)-5s: %(message)s', datefmt='%Y-%m-%d_%H:%M:%S', level=logging.DEBUG)