from PyQt5 import QtCore, QtGui, QtWidgets

import re
import sys
import ctypes
import time
import shlex
import logging

from cUtils import *
#from cSender import *
#from cCodeEditor import *
#from cRunConsole import *
from cWindow import *       



def Main():    
    try:
        xArgs = sys.argv
        xLockfile = QtCore.QLockFile(QtCore.QDir.tempPath() + '/BaabnqIde.lock')
                    
        if xLockfile.tryLock(100):
            xApp = QtWidgets.QApplication(sys.argv)
            xApp.setStyle(QtWidgets.QStyleFactory.create('Fusion'))
            xWindow = cWindow()
                        
            if len(xArgs) > 1:
                xWindow.OpenCodeEditorTab(xArgs[1].replace("\\", "/"))
            
            logging.info("Window Opened")    
    
            xReturnCode = xApp.exec()
            xLockfile.unlock()

        elif len(xArgs) > 1:
            #send call path to main instance via shared memory
            xSharedMem = QtCore.QSharedMemory("BaabnqIdeShare")            

            if xSharedMem.attach(QtCore.QSharedMemory.ReadWrite):
                xRaw = QtCore.QByteArray(xArgs[1].replace("\\", "/").encode("ascii"))
                
                xSharedMem.lock()
                xSharedMem.data()[:xRaw.size()] = xRaw
                xSharedMem.unlock()            
            
            xReturnCode = 0
        else:
            xReturnCode = 0
        
    except Exception as E:
        print(E)
        logging.critical(logging.traceback.format_exc())
        QtWidgets.QMessageBox.about(logging.traceback.format_exc())

    sys.exit(xReturnCode)




if __name__ == '__main__':
    logging.basicConfig(filename = xThisPath + '\lastest.log', filemode = 'w', format = '%(asctime)-10s    %(levelname)-8s    %(message)s', level = logging.DEBUG)
    logging.info("BaabnqIde")
    logging.info("Hello, World")
    logging.info(f"Starting from directory: {xThisPath}".format())
    logging.debug(f"Styles dict loaded: {cUtils.xStyleHandle.xStyle}")

    Main()
        
