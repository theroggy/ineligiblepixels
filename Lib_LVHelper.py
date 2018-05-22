##[LV] Lib=group

#-------------------------------------
# Import/init needed modules
#-------------------------------------
import os
import datetime
import errno
import subprocess
import _winreg as winreg
from qgis.core import QgsMessageLog

#-------------------------------------
# Helper functions
#-------------------------------------
log_filepath=''
log_qgisprogress = ''

def init_log(filepath, qgisprogress):
    """"Functie om logging dir te initialiseren"""
    global log_filepath
    log_filepath = filepath
    global log_qgisprogress
    log_qgisprogress = qgisprogress

def log(message):
    """"Functie om logging wat handiger te maken"""
    # Put the current time before the message...
    now_str = datetime.datetime.now().strftime("%Y-%m-%d|%H:%M:%S")
    message = '%s|%s' %(now_str,message)
    
    # Log the message to the QGIS log...
    QgsMessageLog.logMessage(message, "Processing") 
    
    # Log the message to the QGIS progress window... but in pieces of max maxlen characters, otherwise the output window becomes very wide...
    maxlen = 200
    numberwritten = 0
    while numberwritten < len(message):
        log_qgisprogress.setText(message[numberwritten:numberwritten+maxlen])
        numberwritten += maxlen
    
    # Write to log file...
    if not os.path.exists(os.path.dirname(log_filepath)):
        try:
            os.makedirs(os.path.dirname(log_filepath))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    if os.path.exists(log_filepath):
        with open(log_filepath, 'a') as logfile:
            logfile.write(message + '\n')
    else:
        with open(log_filepath, 'w') as logfile:
            logfile.write(message + '\n')

def run_command(command, ignorecrash=False):
    """"Run a command"""
    # Run the command
    log('    -> Command to execute: %s' %(command))
    log('----------------------------------------------------')

    # Some command line tools tend to crash after they actualy dit all the work. 
    # For these cases it is practical to keep the script from showing a crash-popup so the script can continue successfully.
    if ignorecrash:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Software\Microsoft\Windows\Windows Error Reporting', 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key,"DontShowUI",0, winreg.REG_DWORD, 1)

    command_process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=open(os.devnull), stderr=subprocess.STDOUT, universal_newlines=True)
    for line in iter(command_process.stdout.readline, ""):
        log(line.rstrip())
    log('----------------------------------------------------')
    command_process.wait()

    # Disable suppressing the crash dialog again...
    if ignorecrash:
        winreg.SetValueEx(key,"DontShowUI",0, winreg.REG_DWORD, 0)

    if command_process.returncode != 0:
        message = 'Returncode=%s executing command %s' %(command_process.returncode, command)
        log(message)

        # Raise an exception if ignorecrash isn't used
        if not ignorecrash:
            raise Exception(message)