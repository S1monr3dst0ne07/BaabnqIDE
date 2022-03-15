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
    xApp = QtWidgets.QApplication(sys.argv)
    xApp.setStyle(QtWidgets.QStyleFactory.create('Fusion'))
    xWindow = cWindow()

    logging.info("Window Opened")    
    sys.exit(xApp.exec())




if __name__ == '__main__':
    logging.basicConfig(filename = xThisPath + '\..\lastest.log', filemode = 'w', format = '%(asctime)-10s    %(levelname)-8s    %(message)s', level = logging.DEBUG)
    logging.info("BaabnqIde")
    logging.info("Hello, World")
    logging.info(f"Starting from directory: {xThisPath}".format())
    logging.debug(f"Styles dict loaded: {cUtils.xStyleHandle.xStyle}")



    try:
        Main()
        
    except Exception as E:
        logging.critical(str(E))
