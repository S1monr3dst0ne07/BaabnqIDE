from PyQt5 import QtCore, QtGui, QtWidgets

import re
import sys
import ctypes
import time
import shlex


from cUtils import *
from cSender import *
from cCodeEditor import *
from cRunConsole import *


class cWindow(QtWidgets.QMainWindow):
    #handles running of program
    class cRunner:
        class cAsyncProcessTracker(QtCore.QThread):
            #true finish is only emitted when the process finished on it's own, and not when kill with the stop method
            TrueFinish = QtCore.pyqtSignal()
            
            def __init__(self, xDisplayWidget, xSourceProcess, xDisplayName):
                super().__init__()
                self.xDisplayWidget = xDisplayWidget    #object the progress will be displayed in
                self.xDisplayName   = xDisplayName      #name the object on display will have
                self.xSourceProcess = xSourceProcess
                self.xStopFlag = False
    
            def __del__(self):
                self.quit()
                self.wait()
                    
            def stop(self):
                self.xStopFlag = True
                self.wait()        
    
            def run(self):                
                xPointAnimation = 1
                while self.xSourceProcess.state() != QtCore.QProcess.NotRunning and not self.xStopFlag:
                    time.sleep(0.1)
                    self.xDisplayWidget.setText(self.xDisplayName + xPointAnimation * ".")
    
                    if xPointAnimation < 3: xPointAnimation += 1
                    else                  : xPointAnimation = 0
    
                if not self.xStopFlag:
                    self.TrueFinish.emit()
    
                self.xStopFlag = False
                self.xDisplayWidget.setText("")
                        
        def __init__(self, xParent):
            self.xParent = xParent
            self.xStatusDisplay = xParent.xProcessStatusDisplay
            
            self.xCompilerOutputPuffer = []
            
            self.xProcessTracker = self.cAsyncProcessTracker(None, None, None)
            self.xCompilerProcess = QtCore.QProcess()
            self.xVirtMachProcess = QtCore.QProcess()
            self.xProcessQueue = []

        def __del__(self):
            self.Kill()

        def Compile(self, xSourcePath = "", xDestPath = "", StdoutHandleFunc = None, xFinishInvoke = cUtils.Noop):
            def HandleOutput():
                StdoutHandleFunc(self.xCompilerProcess.readAllStandardOutput())
                
            #kill tracker first then the process, otherwise the tracker will think the process is done and will call xFinishInvoke
            self.xProcessTracker.stop()
            self.xCompilerProcess.kill()
    
            #setup and start the process
            self.xCompilerProcess = QtCore.QProcess()
            self.xCompilerProcess.setWorkingDirectory(cUtils.Path2BasePath(xThisPath))
            self.xCompilerProcess.readyReadStandardOutput.connect(HandleOutput)
            xCallArgs = shlex.split(self.xCompilerCall.replace("<input>", cUtils.Quotes(xSourcePath)).replace("<output>", cUtils.Quotes(xDestPath)))
            self.xCompilerProcess.start(xCallArgs[0], xCallArgs[1:])
            
            #and it's tracker
            self.xProcessTracker = self.cAsyncProcessTracker(self.xStatusDisplay, self.xCompilerProcess, "Compiling")
            self.xProcessTracker.TrueFinish.connect(xFinishInvoke)
            self.xProcessTracker.start()
            
        def Launch(self, xSourcePath = "", StdoutHandleFunc = None, xFinishInvoke = cUtils.Noop):
            def HandleOutput():
                StdoutHandleFunc(self.xVirtMachProcess.readAllStandardOutput())
                StdoutHandleFunc(self.xVirtMachProcess.readAllStandardError())
            
            self.xProcessTracker.stop()
            self.xVirtMachProcess.kill()
            
            self.xVirtMachProcess = QtCore.QProcess()        
            self.xVirtMachProcess.readyReadStandardOutput.connect(HandleOutput)
            xCallArgs = shlex.split(self.xVirtMachCall.replace("<file>", cUtils.Quotes(xSourcePath)))
            self.xVirtMachProcess.start(xCallArgs[0], xCallArgs[1:])
            
            #and it's tracker
            self.xProcessTracker = self.cAsyncProcessTracker(self.xStatusDisplay, self.xVirtMachProcess, "Running")
            self.xProcessTracker.TrueFinish.connect(xFinishInvoke)
            self.xProcessTracker.start()
    
        def StartNextProcess(self):
            if len(self.xProcessQueue) > 0:
                xNextProcess = self.xProcessQueue.pop(0)
                xNextProcess()
    
        def SetRunConfig(self, xCompilerCall, xVirtMachCall):
            self.xCompilerCall = xCompilerCall
            self.xVirtMachCall = xVirtMachCall
    
        def Run(self, xPath):
            self.Kill()
            xBuildPath = xThisPath + "/../build.s1"
            self.xCompilerOutputPuffer = []
            
            def HandleLaunch():
                self.Launch(xBuildPath, self.xParent.xConsole.Byte2Console, self.StartNextProcess)

            def HandleParseCompilerOutput():
                self.ParseCompilerOutput(self.xCompilerOutputPuffer)                
                self.StartNextProcess()


            def HandleCompile():
                self.Compile(xPath, xBuildPath, self.xCompilerOutputPuffer.append, self.StartNextProcess)
            
            self.xProcessQueue = [HandleCompile, HandleParseCompilerOutput, HandleLaunch]
            self.StartNextProcess()
        
        
        
        def ParseCompilerOutput(self, xBytesArrayList):
            xBytes = QtCore.QByteArray()
            for xBytesArrayIter in xBytesArrayList:
                xBytes += xBytesArrayIter
            
            
            xText = str(xBytes, "utf-8")
            #remove all empty line and then take the last to get the status
            xCompilerExitStatus = [x for x in xText.split("\r\n") if x != ""][-1] 
            
            #compiler fail            
            if xCompilerExitStatus != "Compilation was successful":
                self.xParent.xConsole.Write2Console(xCompilerExitStatus + "\r\n")
            
                #only further do something if error checking is enabled
                if self.xParent.xCompilerErrorCheck:
                    self.Kill() #stop the execution of the old build.s1 by kill the processes when the compiler crashes
                    
                    if self.xParent.xJump2ErrorLine:
                        #try to get the line number at which the error is thrown at to jump there
                        xMatch = re.search("\s(\d+):", xCompilerExitStatus)
                        if xMatch:
                            xErrorLineNumber = int(xMatch.group(1))
                            self.xParent.MoveCurrentEditor(xErrorLineNumber - 1)
                        
                    
            
            print(xCompilerExitStatus)
         
        #kills the current process and stops any further ones form running
        def Kill(self):
            
            #clear queue to prevent bullshit
            self.xProcessQueue = []
    
            #kill processes
            self.xProcessTracker.stop()
            self.xCompilerProcess.kill()
            self.xVirtMachProcess.kill()        
    
            self.xProcessTracker = self.cAsyncProcessTracker(None, None, None)
            self.xCompilerProcess = QtCore.QProcess()
            self.xVirtMachProcess = QtCore.QProcess()










    class cFindDialog(QtWidgets.QWidget):
        class cResultList(QtWidgets.QListWidget):
            def __init__(self, xParent):
                super().__init__()
                self.itemClicked.connect(self.clicked)
                self.xParent = xParent
            
            def clicked(self, xItem):
                xText = xItem.text()
                xLineIndex = int(xText.split(":")[1]) - 1
                self.xParent.xParent.xSender.MoveCurrentEditor.emit(xLineIndex)
        
        def __init__(self, xParent):
            super().__init__()
            self.xParent = xParent

            self.setStyleSheet(cUtils.xStyleHandle["FindDialog"])
            self.setWindowTitle("Find")


            self.xLayout = QtWidgets.QGridLayout()
            self.setLayout(self.xLayout)

            self.xResultList = self.cResultList(self)
            self.xLayout.addWidget(self.xResultList, 1, 0)
            
            self.xSearchPrompt = QtWidgets.QLineEdit()
            self.xLayout.addWidget(self.xSearchPrompt, 0, 0)
            
            #update button
            xUpdateButton = QtWidgets.QPushButton("Update")
            xUpdateButton.setStyleSheet(cUtils.xStyleHandle["QPushButtonCss"])
            xUpdateButton.clicked.connect(self.RunSearch)
            self.xLayout.addWidget(xUpdateButton, 0, 1)
            
            #close button
            xCloseButton = QtWidgets.QPushButton("Close")
            xCloseButton.setStyleSheet(cUtils.xStyleHandle["QPushButtonCss"])
            xCloseButton.clicked.connect(self.close)
            self.xLayout.addWidget(xCloseButton, 0, 2)

            
            self.show()
            
            self.xSearchPrompt.setFocus()

        def keyPressEvent(self, xEvent):            
            xKey = xEvent.key()
            
            if xKey == QtCore.Qt.Key_Escape:
                self.close()

            elif xKey == QtCore.Qt.Key_Return:
                self.RunSearch()

            else:
                super().keyPressEvent(xEvent)

        def focusInEvent(self, xEvent):
            self.xSearchPrompt.grabKeyboard()

        def focusOutEvent(self, xEvent):
            self.xSearchPrompt.releaseKeyboard()


        def RunSearch(self):
            xSearchText = self.xSearchPrompt.text()
            xSourceText = self.xParent.xTabHost.currentWidget().toPlainText()

            self.xResultList.clear()

            xFindList = list(re.finditer(xSearchText, xSourceText))
            for xFindIter in xFindList:
                xStartIndex = xFindIter.span()[0]
                xLineIndex = xSourceText[:xStartIndex].count("\n")

                self.xResultList.addItem(f"Line: {xLineIndex + 1}".format())
                
                
                
                
    class cRunConfigDialog(QtWidgets.QWidget):
        def __init__(self, xSender):
            super().__init__()
            self.xSender = xSender

            xPointSize = 10

            self.setStyleSheet(cUtils.xStyleHandle["RunConfig"])
            self.setWindowTitle("Run Config")
            
            self.xLayout = QtWidgets.QGridLayout(self)
                        
                        
            xHelperLabel = QtWidgets.QLabel("""
This is the config for compiling/running a program.
Both the Compiler and the Virtual Machine need to be provided with a call
Source and Destination for the compiler are: <input> and <ouput>. 
So a Compiler call would look like this: python "SomePath2Compiler/Compiler vX.X.py" --input <input> --output <output>
Same for the Virtual Machine, but here only the assembler file needs to be provided, using <file>
            
            """)
            self.xLayout.addWidget(xHelperLabel, 0, 1)          
            
            self.xCompilerCall = QtWidgets.QLineEdit()
            self.xVirtMachCall = QtWidgets.QLineEdit()           
            self.xCompilerCall.setFont(QtGui.QFont(cUtils.xStyleHandle["FontFamily"], xPointSize))
            self.xVirtMachCall.setFont(QtGui.QFont(cUtils.xStyleHandle["FontFamily"], xPointSize))
            self.xCompilerCall.setStyleSheet(cUtils.xStyleHandle["RunConfigLineEditors"])
            self.xVirtMachCall.setStyleSheet(cUtils.xStyleHandle["RunConfigLineEditors"])
            self.xCompilerCall.setFixedHeight(self.xCompilerCall.font().pointSize() * 2)
            self.xVirtMachCall.setFixedHeight(self.xVirtMachCall.font().pointSize() * 2)

            self.xLayout.addWidget(self.xCompilerCall, 1, 1)
            self.xLayout.addWidget(self.xVirtMachCall, 2, 1)



            xCompilerText = QtWidgets.QLabel("Compiler: ")
            xVirtMachText = QtWidgets.QLabel("VirtMach: ")
            xCompilerText.setFont(QtGui.QFont(cUtils.xStyleHandle["FontFamily"], xPointSize))
            xVirtMachText.setFont(QtGui.QFont(cUtils.xStyleHandle["FontFamily"], xPointSize))
            xCompilerText.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            xVirtMachText.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            
            self.xLayout.addWidget(xCompilerText, 1, 0)
            self.xLayout.addWidget(xVirtMachText, 2, 0)
            
            xApplyButton = QtWidgets.QPushButton("Apply")
            xApplyButton.setStyleSheet(cUtils.xStyleHandle["QPushButtonCss"])
            xApplyButton.clicked.connect(self.ApplyChangedFromDialog)
            
            self.xLayout.addWidget(xApplyButton, 3, 0)
            
                    
            self.UpdateDisplays()
            self.show()
            #fix size after all the components have been edited
            self.setFixedHeight(self.height())
            
        def UpdateDisplays(self):
            xCurrectLaunchConfig = self.xSender.GetLaunchConfig()
            self.xCompilerCall.setText(xCurrectLaunchConfig[0])
            self.xVirtMachCall.setText(xCurrectLaunchConfig[1])
            
        def ApplyChangedFromDialog(self):
            self.xSender.SetCompilerCall.emit(self.xCompilerCall.text())
            self.xSender.SetVirtMachCall.emit(self.xVirtMachCall.text())
    
    def __init__(self):
        super().__init__()
        
        self.xProcessStatusDisplay = QtWidgets.QLabel()
        self.xRunner = self.cRunner(self)
        
        self.xTabContent = []
        self.xSender = cSender()
        self.xSender.CloseTab4QWidget.connect(self.CloseTab4QWidget)
        self.xSender.RemoteDragEnterEvent.connect(self.dragEnterEvent)
        self.xSender.RemoteDropEvent.connect(self.dropEvent)
        self.xSender.UpdateTabSaveColor.connect(self.UpdateTabSaveColor)
        
        self.xCompilerCall = ""
        self.xVirtMachCall = ""
        
        #assignment methods
        def SetCompilerCall(x): self.xCompilerCall = x
        def SetVirtMachCall(x): self.xVirtMachCall = x
        def GetLaunchConfig():  return (self.xCompilerCall, self.xVirtMachCall)
        
        self.xRunConfigDialogInstance = None
        self.xSender.SetCompilerCall.connect(SetCompilerCall)
        self.xSender.SetVirtMachCall.connect(SetVirtMachCall)
        self.xSender.MoveCurrentEditor.connect(self.MoveCurrentEditor)
        self.xSender.GetLaunchConfig = GetLaunchConfig
        
        self.setAcceptDrops(True)
        self.xFontFamily = cUtils.xStyleHandle["FontFamily"]
        self.xDialogInstance = None
        
        #compiler check settings
        self.xCompilerErrorCheck = False
        self.xJump2ErrorLine = False
        
        self.InitUI()

    def InitUI(self):

        self.setStyleSheet(cUtils.xStyleHandle["Main"])




        xCentralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(xCentralWidget)
        self.xMainLayout = QtWidgets.QGridLayout(xCentralWidget)
        self.xSplitterContainer = QtWidgets.QSplitter()
        self.xMainLayout.addWidget(self.xSplitterContainer, 0, 0)
        
        #process status
        self.xProcessStatusDisplay.setFixedHeight(15)
        self.xProcessStatusDisplay.setFont(QtGui.QFont(self.xFontFamily, 10))
        self.xProcessStatusDisplay.setStyleSheet(cUtils.xStyleHandle["ProcessDisplay"])
        self.xMainLayout.addWidget(self.xProcessStatusDisplay, 1, 0)



        #main tab host
        self.xTabHost = QtWidgets.QTabWidget()
        self.xSettingsHandle = QtCore.QSettings("BaabnqIde", "MainSettings")
        self.xTabHost.setStyleSheet(cUtils.xStyleHandle["TabHost"])
        self.xTabHost.setTabsClosable(False)
        self.xTabHost.currentChanged.connect(self.UpdateEditorFocus)
        self.xSplitterContainer.addWidget(self.xTabHost)




        #integrated console
        self.xConsoleLayout = QtWidgets.QGridLayout()
        self.xConsole = cRunConsole(self)
        self.xSplitterContainer.addWidget(self.xConsole)

        #menu management
        self.xMenu = self.menuBar()
        self.xMenuFile = self.xMenu.addMenu("&File")
        self.xMenuView = self.xMenu.addMenu("&View")
        self.xMenuOptions = self.xMenu.addMenu("&Options")
        self.xMenuRun = self.xMenu.addMenu("&Run")

        self.xMenuFile.addAction(self.NewMenuSubOption("Open File", self.OpenFileGui, "Ctrl+O"))
        self.xMenuFile.addAction(self.NewMenuSubOption("Close File", self.CloseTabGui, "Ctrl+W"))
        self.xMenuFile.addAction(self.NewMenuSubOption("Save File", self.SaveFileGui, "Ctrl+S"))
        self.xMenuFile.addAction(self.NewMenuSubOption("Refresh Editors", self.RefreshGui, ""))
        self.xMenuFile.addAction(self.NewMenuSubOption("Exit", self.ExitGui, "Esc"))
        
        def GlobalZoom(xDelta):
            if any([x[0].hasFocus() for x in self.xTabContent]):
                self.xTabHost.currentWidget().zoomIn(xDelta)
                
            elif self.xConsole.hasFocus():
                self.xConsole.zoomIn(xDelta)
                
                
        self.xMenuView.addAction(self.NewMenuSubOption("Zoom in",  lambda: GlobalZoom(+1), "Ctrl++"))
        self.xMenuView.addAction(self.NewMenuSubOption("Zoom out", lambda: GlobalZoom(-1), "Ctrl+-"))
        self.xMenuView.addAction(self.NewMenuSubOption("Find", self.FindGui, "Ctrl+F"))

        self.xConsoleSubmenu = self.xMenuOptions.addMenu("Console")        
        def HandleClickAutoScroll(): return self.xConsole.SetAutoScroll(self.xConsoleSubmenu.actions()[1].isChecked())
        self.HandleClickAutoScroll = HandleClickAutoScroll
        self.xConsoleSubmenu.addAction(self.NewMenuSubOption("Clear", self.xConsole.clear, "Ctrl+1"))
        self.xConsoleSubmenu.addAction(self.NewMenuSubOption("Autoscroll  Enabled", HandleClickAutoScroll, "", True))
                
        self.xMenuOptions.addAction(self.NewMenuSubOption("Corrector Enabled", self.UpdateCorrector, "Ctrl+Space", True))
        self.xMenuOptions.addAction(self.NewMenuSubOption("Run Config", self.RunConfigGui, ""))
        self.xMenuOptions.addAction(self.NewMenuSubOption("Compiler Error Check", self.UpdateCompilerErrorCheck, "", True))
        self.xMenuOptions.addAction(self.NewMenuSubOption("Jump To Error Line"  , self.UpdateJump2ErrorLine    , "", True))
        

        self.xMenuRun.addAction(self.NewMenuSubOption("Run", self.RunCurrentProgram, "F1"))
        self.xMenuRun.addAction(self.NewMenuSubOption("Terminate", self.xRunner.Kill, "Shift+F1"))



        self.setWindowTitle("Baabnq IDE")
        self.LoadSetttings(self.xSettingsHandle)
        self.show()        
    
    def FindGui(self):
        self.xFindDialogInstance = self.cFindDialog(self)
    
    
    def MoveCurrentEditor(self, xLine):
        xEditor = self.xTabHost.currentWidget()
        xCursor = QtGui.QTextCursor(xEditor.document().findBlockByLineNumber(xLine))
        xEditor.setTextCursor(xCursor)
    
    def RunCurrentProgram(self):
        xPath = self.xTabHost.currentWidget().xFilePath
        self.xRunner.SetRunConfig(self.xCompilerCall, self.xVirtMachCall) #update call paths
        self.xRunner.Run(xPath)
      
                
    def UpdateCorrector(self):
        xMenuQAction = cUtils.FindQActionInList(self.xMenuOptions.actions(), "Corrector Enabled")
        if xMenuQAction:
            xCheckedState = xMenuQAction.isChecked()
            self.xSender.UpdateCompleterGlobal.emit(xCheckedState)
            self.xSender.UpdateCompleter.emit()

    def UpdateCompilerErrorCheck(self):
        xMenuQAction = cUtils.FindQActionInList(self.xMenuOptions.actions(), "Compiler Error Check")
        if xMenuQAction: self.xCompilerErrorCheck = xMenuQAction.isChecked()
            
    def UpdateJump2ErrorLine(self):
        xMenuQAction = cUtils.FindQActionInList(self.xMenuOptions.actions(), "Jump To Error Line")
        if xMenuQAction: self.xJump2ErrorLine = xMenuQAction.isChecked()
    

    #helper method used for constructing the menu bar
    def NewMenuSubOption(self, xName = "", xActionFunc = None, xShort = "", xCheckable = False):
        xNewAction = QtWidgets.QAction(xName, self, checkable = xCheckable)
        xNewAction.triggered.connect(xActionFunc)
        xNewAction.setShortcut(QtGui.QKeySequence(xShort))
        xNewAction.setText(xName)
        return xNewAction

    #user refresh
    def RefreshGui(self):
        xExitSaveDialog = QtWidgets.QMessageBox(self)
        xExitSaveDialog.setWindowTitle("Confirm?")
        xExitSaveDialog.setText("Refreshing will loose all done progress if not saved, do you wish to continue?")
        xExitSaveDialog.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        xExitSaveDialog.setDefaultButton(QtWidgets.QMessageBox.Cancel)
        
        xReturnCode = xExitSaveDialog.exec()
        if xReturnCode == QtWidgets.QMessageBox.Ok: self.xSender.UpdateEditors.emit()
        
    #user file open request
    def OpenFileGui(self):
        xPath, _ = QtWidgets.QFileDialog.getOpenFileName(None, 'Open File', '', 'Baabnq File (*.baabnq);;Text File (*.txt)')
        if xPath != "": 
            self.OpenCodeEditorTab(xPath)

    #if reference to a file is lost the editor will kill itself and call this to close the tab
    def CloseTab4QWidget(self, QWidget):
        self.CloseTab(self.xTabHost.indexOf(QWidget))

    def CloseTabGui(self):
        #check if tab to be closed is saved
        if not self.xTabContent[self.xTabHost.currentIndex()][0].xIsSaved:
            xSaveDecision = cUtils.SaveDialog(self)
            if xSaveDecision == QtWidgets.QMessageBox.Save: 
                self.SaveFileGui()
                
            elif xSaveDecision == QtWidgets.QMessageBox.Discard:
                pass
            
            elif xSaveDecision == QtWidgets.QMessageBox.Cancel:
                return
             
        self.CloseTab(self.xTabHost.currentIndex())

    def CloseTab(self, xTabIndex):
        if xTabIndex < 0: return
        
        self.xTabHost.removeTab(xTabIndex)
        self.xTabContent[xTabIndex][0].close()
        self.xTabContent.pop(xTabIndex)

    #user file save
    def SaveFileGui(self):
        self.xTabHost.currentWidget().Save()
        self.xSender.UpdateTabSaveColor.emit()
    
    def RunConfigGui(self):
        self.xRunConfigDialogInstance = self.cRunConfigDialog(self.xSender)
        
        
    def SaveAll(self):
        for xTabIter in self.xTabContent:
            xTabIter[0].Save()
    
    
    def OpenCodeEditorTab(self, xPath):
        xCodeEditor = cCodeEditor(self.xSender, self.xFontFamily)
        
        self.xTabHost.addTab(xCodeEditor, cUtils.Path2Name(xPath))
        self.xTabContent.append((xCodeEditor, ))
        
        xCodeEditor.xFilePath = xPath
        xUpdateSuccess = xCodeEditor.UpdateFromPath()
        
        xCodeEditor.xIsSaved = True
        self.UpdateTabSaveColor()
        
        return xUpdateSuccess
        
    #tab changes color based on if saved or not
    def UpdateTabSaveColor(self):
        for xTabbarIndex in range(len(self.xTabHost)):
            xCurrentWidget = self.xTabContent[xTabbarIndex][0]
            if xCurrentWidget.xIsSaved: xColor = QtGui.QColor(cUtils.xStyleHandle["TabSaved"])
            else:                       xColor = QtGui.QColor(cUtils.xStyleHandle["TabChanged"])
            self.xTabHost.tabBar().setTabTextColor(xTabbarIndex, xColor)

    def UpdateEditorFocus(self):
        #disable all editor, except the one in focus
        for xTabIndex, xTabIter in enumerate(self.xTabContent):
            xDisabled = xTabIndex != self.xTabHost.currentIndex()
            xTabIter[0].SetCompleterStatus(not xDisabled)
            xTabIter[0].setDisabled(xDisabled)

    def ExitGui(self):
        
        self.close()

    def LoadSetttings(self, xSettingsHandle):
        self.resize(self.xSettingsHandle.value("windowSize"))
        self.move(self.xSettingsHandle.value("windowPos"))
        self.xCompilerCall = self.xSettingsHandle.value("compilerCall")
        self.xVirtMachCall = self.xSettingsHandle.value("virtMachCall")
        
        xSettingsState = self.xSettingsHandle.value("splitterState")
        if xSettingsState: self.xSplitterContainer.restoreState(xSettingsState)
        
        xConsoleZoom = self.xSettingsHandle.value("consoleZoom")
        if xConsoleZoom: self.xConsole.setFont(QtGui.QFont(self.xFontFamily, xConsoleZoom))
        
        xConsoleAutoScroll = self.xSettingsHandle.value("consoleAutoScroll")
        if xConsoleAutoScroll: cUtils.FindQActionInList(self.xConsoleSubmenu.actions(), "Autoscroll  Enabled").setChecked(xConsoleAutoScroll)
        
        xCompilerErrorCheck = self.xSettingsHandle.value("compilerErrorCheck")
        if xCompilerErrorCheck: cUtils.FindQActionInList(self.xMenuOptions.actions(), "Compiler Error Check").setChecked(xCompilerErrorCheck)

        xJump2ErrorLine = self.xSettingsHandle.value("jump2ErrorLine")
        if xJump2ErrorLine: cUtils.FindQActionInList(self.xMenuOptions.actions(), "Jump To Error Line").setChecked(xJump2ErrorLine)

        
        xTabDataList = eval(self.xSettingsHandle.value("tabInstanceList"))
        for xTabDataIter in xTabDataList:
            xSuccess = self.OpenCodeEditorTab(xTabDataIter["filePath"])
            if xSuccess:
                self.xTabContent[-1][0].setFont(QtGui.QFont(self.xFontFamily, xTabDataIter["zoom"]))
            
            
        
        self.xTabHost.setCurrentIndex(xSettingsHandle.value("selectedTabIndex"))
        self.HandleClickAutoScroll()
        self.UpdateCompilerErrorCheck()
        self.UpdateJump2ErrorLine()
        
    def SaveSettings(self, xSettingsHandle):
        xSettingsHandle.setValue("windowPos", self.pos())
        xSettingsHandle.setValue("windowSize", self.size())
        xSettingsHandle.setValue("compilerCall", self.xCompilerCall)
        xSettingsHandle.setValue("virtMachCall", self.xVirtMachCall)

        xSettingsHandle.setValue("splitterState", self.xSplitterContainer.saveState())

        xSettingsHandle.setValue("consoleZoom", self.xConsole.font().pointSize())
        xBoolAutoScrollState = cUtils.FindQActionInList(self.xConsoleSubmenu.actions(), "Autoscroll  Enabled").isChecked()
        xSettingsHandle.setValue("consoleAutoScroll", 1 if xBoolAutoScrollState else 0)

        xSettingsHandle.setValue("compilerErrorCheck", 1 if self.xCompilerErrorCheck else 0)
        xSettingsHandle.setValue("jump2ErrorLine",     1 if self.xJump2ErrorLine     else 0)
        

        xTabDataList = []
        
        #get data from tab content
        for xTabIter in self.xTabContent:
            xTabDataList.append({
                "filePath" : xTabIter[0].xFilePath,
                "zoom"     : xTabIter[0].font().pointSize(),
                
                })
        
        xSettingsHandle.setValue("tabInstanceList",  str(xTabDataList))
        xSettingsHandle.setValue("selectedTabIndex", self.xTabHost.currentIndex())            
        


    def dragEnterEvent(self, xEvent):
        if xEvent.mimeData().hasText():
            xEvent.accept()
        else:
            xEvent.ignore()

    def dropEvent(self, xEvent):
        xRawPath = xEvent.mimeData().text()
        xPath = re.search("file:\/\/\/(.+)", xRawPath).group(1)
        self.OpenCodeEditorTab(xPath)

    def closeEvent(self, xEvent):
        #check for unsaved editor instances
        xIsUnsaved = False
        for xTabIter in self.xTabContent:
            if not xTabIter[0].xIsSaved:
                xIsUnsaved = True
        
        if xIsUnsaved:
            #ask if the user wants to save progress
            
            xSaveDecision = cUtils.SaveDialog(self)
            if xSaveDecision == QtWidgets.QMessageBox.Save:
                self.SaveAll()
                
            elif xSaveDecision == QtWidgets.QMessageBox.Discard:
                pass
            
            elif xSaveDecision == QtWidgets.QMessageBox.Cancel:
                xEvent.ignore()
                return
            
        self.SaveSettings(self.xSettingsHandle)
        if self.xRunConfigDialogInstance:
            self.xRunConfigDialogInstance.close()
