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
    #hands running of program
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
            
            def HandleLaunch():
                self.Launch(xBuildPath, self.xParent.xConsole.Byte2Console, self.StartNextProcess)
            
            def Test(xText):
                print(xText)
                pass
            
            def HandleCompile():
                self.Compile(xPath, xBuildPath, Test, self.StartNextProcess)
            
            self.xProcessQueue = [HandleCompile, HandleLaunch]
            self.StartNextProcess()
            
                
        def Kill(self):
            
            #clear queue to prevent bullshit
            self.xProcessQueue = []
    
            #terminate processes
            self.xProcessTracker.stop()
            self.xCompilerProcess.kill()
            self.xVirtMachProcess.kill()        
    
            self.xProcessTracker = self.cAsyncProcessTracker(None, None, None)
            self.xCompilerProcess = QtCore.QProcess()
            self.xVirtMachProcess = QtCore.QProcess()
















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
        self.xSender.GetLaunchConfig = GetLaunchConfig
        
        self.setAcceptDrops(True)
        self.xFontFamily = cUtils.xStyleHandle["FontFamily"]
        self.xDialogInstance = None
        
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
                
        self.xMenuOptions.addAction(self.NewMenuSubOption("Corrector Enabled", self.ToggleCorrector, "Ctrl+Space", True))
        self.xMenuOptions.addAction(self.NewMenuSubOption("Run Config", self.RunConfigGui, ""))

        self.xMenuRun.addAction(self.NewMenuSubOption("Run", self.RunCurrentProgram, "F1"))
        self.xMenuRun.addAction(self.NewMenuSubOption("Terminate", self.xRunner.Kill, "Shift+F1"))



        self.setWindowTitle("Baabnq IDE")
        self.LoadSetttings(self.xSettingsHandle)
        self.show()        
    
    def FindGui(self):
        pass
    
    
    def RunCurrentProgram(self):
        xPath = self.xTabHost.currentWidget().xFilePath
        self.xRunner.SetRunConfig(self.xCompilerCall, self.xVirtMachCall) #update call paths
        self.xRunner.Run(xPath)
      
                
    def ToggleCorrector(self):
        xMenuQAction = cUtils.FindQActionInList(self.xMenuOptions.actions(), "Corrector Enabled")
        if xMenuQAction:
            xCheckedState = xMenuQAction.isChecked()
            self.xSender.UpdateCorrectorState.emit(xCheckedState)
            self.xSender.UpdateCompleter.emit()

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
        if xConsoleAutoScroll: self.xConsoleSubmenu.actions()[1].setChecked(xConsoleAutoScroll)
        
        xTabDataList = eval(self.xSettingsHandle.value("tabInstanceList"))
        for xTabDataIter in xTabDataList:
            xSuccess = self.OpenCodeEditorTab(xTabDataIter["filePath"])
            if xSuccess:
                self.xTabContent[-1][0].setFont(QtGui.QFont(self.xFontFamily, xTabDataIter["zoom"]))
            
            
        
        self.xTabHost.setCurrentIndex(xSettingsHandle.value("selectedTabIndex"))
        self.HandleClickAutoScroll()
        
        
    def SaveSettings(self, xSettingsHandle):
        xSettingsHandle.setValue("windowPos", self.pos())
        xSettingsHandle.setValue("windowSize", self.size())
        xSettingsHandle.setValue("compilerCall", self.xCompilerCall)
        xSettingsHandle.setValue("virtMachCall", self.xVirtMachCall)

        xSettingsHandle.setValue("splitterState", self.xSplitterContainer.saveState())

        xSettingsHandle.setValue("consoleZoom", self.xConsole.font().pointSize())
        xBoolAutoScrollState = self.xConsoleSubmenu.actions()[1].isChecked()
        xSettingsHandle.setValue("consoleAutoScroll", 1 if xBoolAutoScrollState else 0)

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
