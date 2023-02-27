from PyQt5 import QtCore, QtGui, QtWidgets
import time

#used to open new tab from other process, when old instance of process is still running
class cAltInstanceRecvChecker(QtCore.QThread):
    def __init__(self, xParent, xSharedMem):
        super().__init__()
        self.xSharedMem = xSharedMem
        self.xIsRunning = True
        self.xParent = xParent
    
    def run(self):
        while self.xIsRunning:
            self.xSharedMem.lock()
            xData = self.xSharedMem.data()
            xPath = str(xData, encoding = 'ascii').strip("\x00")

            if len(xPath) > 0:
                #reset shared memory
                xZs = "\x00" * len(xData)
                xData[:] = QtCore.QByteArray(xZs.encode("ascii"))

                #open new tab with path
                self.xParent.xSender.OpenCodeEditorTab.emit(xPath)

                #raise window
                self.xParent.xSender.RaiseMainWindow.emit()
            
            self.xSharedMem.unlock()
            time.sleep(0.5)
            
        
    def Kill(self):
        self.xIsRunning = False
    


