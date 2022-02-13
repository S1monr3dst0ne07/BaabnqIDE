from PyQt5 import QtCore, QtGui, QtWidgets

import re
import sys
import ctypes
import time
import shlex


#from cUtils import *
#from cSender import *
#from cCodeEditor import *
#from cRunConsole import *
from cWindow import *       

        

if __name__ == '__main__':
    xApp = QtWidgets.QApplication(sys.argv)
    xWindow = cWindow()
    
    sys.exit(xApp.exec())
