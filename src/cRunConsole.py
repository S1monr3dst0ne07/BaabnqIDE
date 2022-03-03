from PyQt5 import QtCore, QtGui, QtWidgets

import re
import sys
import ctypes
import time
import shlex


from cUtils import *



class cRunConsole(QtWidgets.QPlainTextEdit):
    def __init__(self, xParent):
        super().__init__()
        self.xParent = xParent

        self.xAutoScroll = False
        self.setFont(QtGui.QFont())
        self.setStyleSheet(cUtils.xStyleHandle["RunConsole"])
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

        #override the look of the scroll bar to match the overall theme (which btw is a pain in the ass)
        xHandleColor = cUtils.xStyleHandle["ScrollStyleHandelColor"]
        self.verticalScrollBar().setStyleSheet(  cUtils.xStyleHandle["ScrollStyle"].format(sizeMod = "width:20px;", handleColor = xHandleColor))
        self.horizontalScrollBar().setStyleSheet(cUtils.xStyleHandle["ScrollStyle"].format(sizeMod = "hight:20px;", handleColor = xHandleColor))
        
        self.textChanged.connect(self.Change)
    
    def SetAutoScroll(self, xNewState):
        self.xAutoScroll = xNewState

    def Write2Console(self, xNewText):
        self.insertPlainText(xNewText)
        
    def Byte2Console(self, xByteArray):
        #catch if screen is cleared by looking for escape code 0c
        if b'\x0c' in xByteArray:   self.clear()
        else:                       self.Write2Console(cUtils.Bytes2Str(xByteArray))
              
    def Change(self):
        if self.xAutoScroll:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def keyPressEvent(self, xEvent):
        xParentProcess = self.xParent.xRunner.xProcessTracker.xSourceProcess

        super().keyPressEvent(xEvent)
        xChar = xEvent.text()
        xBytes = xChar.encode("utf-8")
                
        try:
            if xBytes == b"\r":
                xParentProcess.write(b"\n")
                
            else:    
                xParentProcess.write(xBytes)
                sys.stdout.flush()
            
        except Exception as E:
            print(E)
        