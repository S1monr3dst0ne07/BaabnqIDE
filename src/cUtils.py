import json
import os
import re

xThisPath = os.path.dirname(os.path.abspath(__file__))

#loaing css style from file
class cStyleHandle:
    def __init__(self, xPath):
        with open(xPath, "r") as xFileHandle:
            xFileContent = xFileHandle.read()
            self.xStyle = json.loads(xFileContent.replace("\n", ""))
    
    def __getitem__(self, xKey):
        return self.xStyle[xKey]

class cUtils:
        
    xStyleHandle = cStyleHandle(xThisPath + "/../assets/styles.json")

    @staticmethod    
    def ChopChopSplit(xStr, xDelimiters):
        xList = [xStr]
        
        
        for xDelimIter in xDelimiters:
            xNewList = []
            
            for x in xList: xNewList += x.split(xDelimIter)
            xList = xNewList

        return xList

    
    
    @staticmethod
    def RemoveDups(x):
        return list(set(x))

    @staticmethod
    def SaveDialog(xPopupHostWidgetInstance):
        xSaveDialog = QtWidgets.QMessageBox(xPopupHostWidgetInstance)
        xSaveDialog.setWindowTitle("Save?")
        xSaveDialog.setText("Save changes before closing?")
        xSaveDialog.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
        xSaveDialog.setDefaultButton(QtWidgets.QMessageBox.Save)

        return xSaveDialog.exec_()

    @staticmethod
    def Noop():
        pass
    @staticmethod
    def FindQActionInList(xQActionList, xName):
        for xQActionIter in xQActionList:
            if xQActionIter.text() == xName:
                return xQActionIter
            
        return None
    
    @staticmethod
    def Path2Name(xPath):
        xMatch = re.search("[^\/]+\.[^\/]+$", xPath)
        return xMatch[0]

    @staticmethod
    def Path2BasePath(xPath):
        print(xPath)
        xMatch = re.search("(.*[\\\/]).*", xPath)
        print(xMatch)
        return xMatch[0]
    
    
    @staticmethod
    def Quotes(xRaw):
        return '"' + xRaw + '"'