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

                logging.info("New cAsyncProcessTracker")
                self.LogReference()
    
            def __del__(self):
                self.quit()
                self.wait()
                    
            def stop(self):
                self.xStopFlag = True
                self.wait()        
    
            def run(self):             
                logging.info("Starting cAsyncProcessTracker, target locked")
                self.LogReference()
                
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

            def LogReference(self):
                logging.debug(f"==={self}=== (WARNING: THIS PROCESS MAY BE DEAD)".format())
                logging.debug(f"xDisplayName: {self.xDisplayName}".format())
                logging.debug(f"xSourceProcess: {self.xSourceProcess}".format())
                
                
        class cDebug(QtWidgets.QWidget):
            def __init__(self, xParent):
                super().__init__()
                self.xParent = xParent

                xIconPath = xThisPath.replace("\\", "/") + "/assets/Icon.png"
                self.setWindowIcon(QtGui.QIcon(xIconPath))


                self.xPluginDisplayList = []
                self.xStackDisplayList  = []
                self.xMaxCommandListSize = 5


                self.setStyleSheet(cUtils.xStyleHandle["DebugDialog"])
                self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
                self.setWindowTitle("Debug")
                
                self.xLayout = QtWidgets.QGridLayout()
                self.setLayout(self.xLayout)
                
                self.xLayout.addWidget(QtWidgets.QLabel("Plugin Calls: "), 0, 0)
                self.xLayout.addWidget(QtWidgets.QLabel("Variables: "), 2, 0)
                self.xLayout.addWidget(QtWidgets.QLabel("Heap Usage: "), 0, 1)
                self.xLayout.addWidget(QtWidgets.QLabel("Stack: "), 2, 1)
                self.xLayout.addWidget(QtWidgets.QLabel("Mode: "), 4, 0)
                
                
                #buttons
                self.xButtonLayout = QtWidgets.QHBoxLayout(self)
                
                self.xContinueButton = QtWidgets.QPushButton("Continue Execution")
                self.xCloseButton = QtWidgets.QPushButton("Close")
                cUtils.FixWidgetWidth(self.xContinueButton)
                cUtils.FixWidgetWidth(self.xCloseButton)
                self.SetDebuggerButtonsEnabled(False)
                self.xContinueButton.pressed.connect(lambda: self.SendBreakpointOption("Continue\n"))
                self.xCloseButton.setStyleSheet(cUtils.xStyleHandle["QPushButtonCss"])
                self.xCloseButton.pressed.connect(self.close)
                
                self.xButtonLayout.addWidget(self.xContinueButton, 0)
                self.xButtonLayout.addWidget(self.xCloseButton, 1)

                self.xLayout.addLayout(self.xButtonLayout, 5, 1)


                
                self.xModeDisplay = QtWidgets.QLabel("<No Updates yet>")
                self.xModeDisplay.setStyleSheet(cUtils.xStyleHandle["Label"])
                self.xLayout.addWidget(self.xModeDisplay, 5, 0)
                
                self.xPluginDisplay = QtWidgets.QListWidget()
                self.xLayout.addWidget(self.xPluginDisplay, 1, 0)

                self.xStackDisplay = QtWidgets.QListWidget()
                self.xLayout.addWidget(self.xStackDisplay, 3, 1)


                self.xVarDisplay = QtWidgets.QTableWidget(0, 0, self)
                self.xVarDisplay.setColumnCount(2)
                self.xVarDisplay.setRowCount(1)
                self.xVarDisplay.verticalHeader().hide()
                self.xVarDisplay.horizontalHeader().hide()
                self.xVarDisplay.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
                self.xVarDisplay.setFocusPolicy(QtCore.Qt.NoFocus)
                self.xVarDisplay.setSelectionMode(QtWidgets.QTableWidget.NoSelection)
                self.xVarDisplay.setItem(0, 0, QtWidgets.QTableWidgetItem("Name"))
                self.xVarDisplay.setItem(0, 1, QtWidgets.QTableWidgetItem("Value"))
                                
                self.xLayout.addWidget(self.xVarDisplay, 3, 0)
                
                
                self.xHeapUsageDisplay = QtWidgets.QProgressBar(self)
                self.xHeapUsageDisplay.setFormat("%v / %m")
                self.xLayout.addWidget(self.xHeapUsageDisplay, 1, 1)

                xPluginDisplayFont = self.xPluginDisplay.font()
                xPluginDisplayMetric = QtGui.QFontMetrics(xPluginDisplayFont)
                
                xPluginDisplayHeight = xPluginDisplayMetric.height() * (self.xMaxCommandListSize + 1)
                self.xPluginDisplay.setFixedHeight(xPluginDisplayHeight)

                #fix alignments
                self.xLayout.setAlignment(self.xHeapUsageDisplay, QtCore.Qt.AlignTop)
                self.xLayout.setAlignment(self.xModeDisplay, QtCore.Qt.AlignTop)

                
                self.show()
            
            
            def SendBreakpointOption(self, xOptionType):
                if self.xParent.xVirtMachMode == 1:
                    self.xParent.xProcessTracker.xSourceProcess.write(xOptionType.encode("utf-8"))
            
            def SetDebuggerButtonsEnabled(self, xEnabled):
                self.xContinueButton.setEnabled(xEnabled)
                
                if xEnabled:
                    self.xContinueButton.setStyleSheet(cUtils.xStyleHandle["QPushButtonCss"])

                else:
                    self.xContinueButton.setStyleSheet(cUtils.xStyleHandle["QPushButtonCssDisabled"])

            
            def UpdateVarDisplay(self, xVarDict):
                self.xVarDisplay.setRowCount(1 + len(xVarDict))
                
                for xIndex, xName in enumerate(xVarDict.keys()):
                    self.xVarDisplay.setItem(xIndex + 1, 0, QtWidgets.QTableWidgetItem(xName))
                    self.xVarDisplay.setItem(xIndex + 1, 1, QtWidgets.QTableWidgetItem(str(xVarDict[xName])))

            def UpdateHeapUsage(self, xNewVal, xNewMax):
                self.xHeapUsageDisplay.setMaximum(int(xNewMax))
                self.xHeapUsageDisplay.setValue(int(xNewVal))
                
                
            def UpdatePluginDisplay(self, xNewCommand):
                self.xPluginDisplayList.append(xNewCommand.replace(" ", "\t"))
                
                while len(self.xPluginDisplayList) > self.xMaxCommandListSize:
                    self.xPluginDisplayList.pop(0)
                    
                #update the commanddisplay widget
                self.xPluginDisplay.clear()
                self.xPluginDisplay.addItems(self.xPluginDisplayList)
                
            def UpdateStackDisplay(self, xStackInteractionType, xValue):
                if xStackInteractionType == "push":
                    self.xStackDisplayList.append(xValue)
                    
                elif xStackInteractionType == "pull" and len(self.xStackDisplayList) > 0:
                    self.xStackDisplayList.pop(-1)

                
                self.xStackDisplay.clear()
                self.xStackDisplay.addItems(self.xStackDisplayList)
                

         
        def __init__(self, xParent):
            self.xParent = xParent
            self.xStatusDisplay = xParent.xProcessStatusDisplay
            self.xDebugWindow = None
            
            self.xCompilerOutputPuffer = []
            self.xVarValues = {}
            
            self.xVirtMachMode = 0
            
            self.xProcessTracker = self.cAsyncProcessTracker(None, None, None)
            self.xCompilerProcess = QtCore.QProcess()
            self.xVirtMachProcess = QtCore.QProcess()
            self.xProcessQueue = []

        def __del__(self):
            self.Kill()

        def Compile(self, xSourcePath = "", xDestPath = "", StdoutHandleFunc = None, xFinishInvoke = cUtils.Noop, xAddArgs = [], xDisplayName = "Compiling"):
            logging.info("Core Compiling")
            logging.debug(f"xSourcePath: {xSourcePath}".format())
            logging.debug(f"xDestPath  : {xDestPath}".format())
            logging.debug(f"xAddArgs   : {xAddArgs}".format())
            
            
            def HandleOutput():
                StdoutHandleFunc(self.xCompilerProcess.readAllStandardOutput())
                xError = self.xCompilerProcess.readAllStandardError()
                
                if xError:
                    logging.error(xError)

                
            #kill tracker first then the process, otherwise the tracker will think the process is done and will call xFinishInvoke
            self.xProcessTracker.stop()
            self.xCompilerProcess.kill()
    
            #setup and start the process
            self.xCompilerProcess = QtCore.QProcess()
            self.xCompilerProcess.setWorkingDirectory(cUtils.Path2BasePath(xThisPath))
            self.xCompilerProcess.readyReadStandardOutput.connect(HandleOutput)
            
            try: 
                if any(x not in self.xCompilerCall for x in ["{input}", "{output}"]): raise Exception
                xCallArgs = shlex.split(self.xCompilerCall.format(input = cUtils.Quotes(xSourcePath), output = cUtils.Quotes(xDestPath)))

                self.xCompilerProcess.start(xCallArgs[0], xCallArgs[1:] + xAddArgs)
            
                #and it's tracker
                self.xProcessTracker = self.cAsyncProcessTracker(self.xStatusDisplay, self.xCompilerProcess, xDisplayName)
                self.xProcessTracker.TrueFinish.connect(xFinishInvoke)
                self.xProcessTracker.start()


            except Exception:
                xWarnMsg = "Invalid Run Config: {}".format(self.xCompilerCall)
                logging.warn(xWarnMsg)
                self.xParent.xConsole.Write2Console(xWarnMsg)


            
        def Launch(self, xSourcePath = "", StdoutHandleFunc = None, xFinishInvoke = cUtils.Noop, xAddArgs = [], xDisplayName = "Running"):
            logging.info("Core Launching")
            logging.debug(f"xSourcePath: {xSourcePath}".format())
            logging.debug(f"xAddArgs   : {xAddArgs}".format())

            def HandleOutput():
                StdoutHandleFunc(self.xVirtMachProcess.readAllStandardOutput())
                xError = self.xCompilerProcess.readAllStandardError()
                
                if xError:
                    logging.error(xError)
            
            self.xProcessTracker.stop()
            self.xVirtMachProcess.kill()
            
            self.xVirtMachProcess = QtCore.QProcess()
            self.xVirtMachProcess.readyReadStandardOutput.connect(HandleOutput)
            
            try:
                if "{file}" not in self.xVirtMachCall: raise Exception                
                xCallArgs = shlex.split(self.xVirtMachCall.format(file = cUtils.Quotes(xSourcePath)))

                self.xVirtMachProcess.start(xCallArgs[0], xCallArgs[1:] + xAddArgs)
                
                #and it's tracker
                self.xProcessTracker = self.cAsyncProcessTracker(self.xStatusDisplay, self.xVirtMachProcess, xDisplayName)
                self.xProcessTracker.TrueFinish.connect(xFinishInvoke)
                self.xProcessTracker.start()

            except Exception:
                xWarnMsg = "Invalid Run Config: {}".format(self.xVirtMachCall)
                logging.warn(xWarnMsg)
                self.xParent.xConsole.Write2Console(xWarnMsg)

    
        def StartNextProcess(self):
            if len(self.xProcessQueue) > 0:
                xNextProcess = self.xProcessQueue.pop(0)
                
                logging.info("Starting new Handler Subprocess: " + str(xNextProcess))
                xNextProcess()
    
        def SetRunConfig(self, xCompilerCall, xVirtMachCall):
            self.xCompilerCall = xCompilerCall
            self.xVirtMachCall = xVirtMachCall

        def Run(self, xPath):
            logging.info("RunningProcess")

            self.Kill()
            xBuildPath = xThisPath + "/build.s1"
            self.xCompilerOutputPuffer = []

            logging.debug(f"xBuildPath: {xBuildPath}".format())
            
            def HandleLaunch():
                self.Launch(xBuildPath, self.xParent.xConsole.Byte2Console, self.StartNextProcess)

            def HandleParseCompilerOutput():
                self.ParseCompilerOutput(self.xCompilerOutputPuffer)                
                self.StartNextProcess()


            def HandleCompile():
                self.Compile(xPath, xBuildPath, self.xCompilerOutputPuffer.append, self.StartNextProcess)
            
            self.xProcessQueue = [HandleCompile, HandleParseCompilerOutput, HandleLaunch]
            logging.debug(f"Launching with xProcessQueue: {self.xProcessQueue}".format())

            self.StartNextProcess()
        
        def Debug(self, xPath, xBreakpoints):
            logging.info("DebugingProcess")

            self.Kill()
            self.xVarValues = {} #for new run reset variable buffer
            xBuildPath = xThisPath + "/build.s1"
            xTempPath  = xThisPath + "/temp.baabnq"
            self.xCompilerOutputPuffer = []
            
            logging.debug(f"xBuildPath: {xBuildPath}".format())
            logging.debug(f"xTempPath : {xTempPath}".format())
            
            
            #check if debugger is not opened
            if self.xDebugWindow is None or not self.xDebugWindow.isVisible():
                self.xDebugWindow = self.cDebug(self)
                self.xParent.xSender.GlobalClose.connect(self.xDebugWindow.close)

            self.xDebugWindow.xStackDisplayList = []
            
            def HandleDebugProtocol(xBytes):
                #split line by line
                xLines = cUtils.Bytes2Str(xBytes).split("\r\n")
                for xLineIter in xLines:
                    #pull category and data from line
                    xLineMatch = re.match("(.+)\((.+)\)", xLineIter)
                    if xLineMatch is None:
                        continue
                    
                    xCategory, xData = xLineMatch.group(1, 2)
                    
                    if xCategory == "Print":
                        self.xParent.xConsole.Write2Console(xData)
                        
                    elif xCategory == "Chr":
                        xRawInt = int(xData)
                        self.xParent.xConsole.Write2Console(chr(xRawInt))
                        
                    elif xCategory == "Plugin":
                        self.xDebugWindow.UpdatePluginDisplay(xData)
                        
                    elif xCategory == "Var":
                        self.xVarValues.update(eval(xData))
                        self.xDebugWindow.UpdateVarDisplay(self.xVarValues)
                        
                    elif xCategory == "HeapUsage":
                        self.xDebugWindow.UpdateHeapUsage(*xData.split(":"))
                    
                    elif xCategory == "Stack":
                        self.xDebugWindow.UpdateStackDisplay(*xData.split(":", 1))

                    elif xCategory == "Mode":
                        self.xVirtMachMode = int(xData)
                        
                        logging.debug(f"Mode Change: {self.xVirtMachMode}".format())
                        
                        xModeText = {
                            0 : "Running",
                            1 : "Breakpoint",
                            }[self.xVirtMachMode]
                        self.xDebugWindow.xModeDisplay.setText(xModeText)
                        self.xDebugWindow.SetDebuggerButtonsEnabled(self.xVirtMachMode == 1)
                    
                    else:
                        self.xParent.xConsole.Write2Console(f"UNRECOGNIZED RAW: {xData}\n".format())
                        
                                
                
            def HandleTempCopy():
                xInputFileHandle =  open(xPath, "r")
                xOutputFileHandle = open(xTempPath, "w")

                xCurrentWidget = self.xParent.xTabHost.currentWidget()
                xBreakpoints = xCurrentWidget.xBreakpoints

                xFileContent = xInputFileHandle.read()
                xFileInterlaced = [
                    ("asm 'breakpoint 0'; {}".format(xData) if xIndex in xBreakpoints else xData) for xIndex, xData in enumerate(xFileContent.split("\n"))
                ]
                
                xOutputFileHandle.write("\n".join(xFileInterlaced))
                                
                xInputFileHandle.close()
                xOutputFileHandle.close()
                
                self.StartNextProcess()
                            
            def HandleLaunch():
                self.Launch(xBuildPath, HandleDebugProtocol, self.StartNextProcess, xAddArgs = ["--debug"], xDisplayName = "Debugging")

            def HandleParseCompilerOutput():
                self.ParseCompilerOutput(self.xCompilerOutputPuffer)                
                self.StartNextProcess()


            def HandleCompile():
                self.Compile(xTempPath, xBuildPath, self.xCompilerOutputPuffer.append, self.StartNextProcess, xAddArgs = ["--MoreInfo"])
            
            self.xProcessQueue = [HandleTempCopy, HandleCompile, HandleParseCompilerOutput, HandleLaunch]
            logging.debug(f"Launching with xProcessQueue: {self.xProcessQueue}".format())
            
            self.StartNextProcess()

        
        def ParseCompilerOutput(self, xBytesArrayList):
            try:
                logging.debug(f"Compiler returned bytes: {xBytesArrayList}".format())
    
                xBytes = QtCore.QByteArray()
                for xBytesArrayIter in xBytesArrayList:
                    xBytes += xBytesArrayIter
                
                
                #xText = str(xBytes, "utf-8")
                xText = cUtils.Bytes2Str(xBytes)
                #remove all empty line and then take the last to get the status
                xCompilerExitStatus = [x for x in xText.split("\r\n") if x != ""][-1] 
                
                logging.debug(f"Compiler Exit Status: {xCompilerExitStatus}".format())
                
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

            except Exception as E:
                self.Kill()
                logging.warn(str(E))
                    
                     
        #kills the current process and stops any further ones form running
        def Kill(self):
            logging.info("KillingProcess")
            self.xProcessTracker.LogReference()
            
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
                xLineIndex = int(xText.split(":")[0]) - 1
                self.xParent.xParent.xSender.MoveCurrentEditor.emit(xLineIndex)
        
        def __init__(self, xParent):
            super().__init__()
            self.xParent = xParent

            xIconPath = xThisPath.replace("\\", "/") + "/assets/Icon.png"
            self.setWindowIcon(QtGui.QIcon(xIconPath))


            self.setStyleSheet(cUtils.xStyleHandle["FindDialog"])
            self.setWindowTitle("Find")


            self.xLayout = QtWidgets.QGridLayout()
            self.setLayout(self.xLayout)

            self.xResultList = self.cResultList(self)
            self.xLayout.addWidget(self.xResultList, 2, 0)
            
            self.xSearchPrompt = QtWidgets.QLineEdit()
            self.xLayout.addWidget(self.xSearchPrompt, 1, 0)
            
            xTempFont = QtGui.QFont("Consolas", 10)
            xHelpLabel = QtWidgets.QLabel("Find:")
            xHelpLabel.setFont(xTempFont)
            self.xLayout.addWidget(xHelpLabel, 0, 0)
            
            
            #update button
            xUpdateButton = QtWidgets.QPushButton(" Update ")
            xUpdateButton.setStyleSheet(cUtils.xStyleHandle["QPushButtonCss"])
            xUpdateButton.clicked.connect(self.RunSearch)
            self.xLayout.addWidget(xUpdateButton, 1, 2)
            
            #close button
            xCloseButton = QtWidgets.QPushButton(" Close ")
            xCloseButton.setStyleSheet(cUtils.xStyleHandle["QPushButtonCss"])
            xCloseButton.clicked.connect(self.close)
            self.xLayout.addWidget(xCloseButton, 1, 3)

            
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

            xFindList  = list(re.finditer(xSearchText, xSourceText))
            xFindCount = len(xFindList)
            
            #this is used to format the list of found items correctly
            #so that it looks like this:
            #1  : <lineContent>
            #10 : <lineContent>
            
            #and not like this:
            #1 : <lineContent>
            #10 : <lineContent>
            
            for xFindIter in xFindList:
                xStartIndex = xFindIter.span()[0]
                xLineIndex = xSourceText[:xStartIndex].count("\n")

                xLineContent = xSourceText.split("\n")[xLineIndex]
                
                self.xResultList.addItem(f"{xLineIndex + 1}:\t {xLineContent.strip()}".format())    
     
                
                
    class cRunConfigDialog(QtWidgets.QWidget):
        def __init__(self, xSender):
            super().__init__()
            self.xSender = xSender

            xIconPath = xThisPath.replace("\\", "/") + "/assets/Icon.png"
            self.setWindowIcon(QtGui.QIcon(xIconPath))


            xPointSize = 10

            self.setStyleSheet(cUtils.xStyleHandle["RunConfig"])
            self.setWindowTitle("Run Config")
            
            self.xLayout = QtWidgets.QGridLayout(self)
                        
                        
            xHelperLabel = QtWidgets.QLabel("""
This is the config for compiling/running a program.
Both the Compiler and the Virtual Machine need to be provided with a call
Source and Destination for the compiler are: {input} and {ouput}. 
So a Compiler call would look like this: python "SomePath2Compiler/Compiler vX.X.py" --input "{input}" --output "{output}"
Same for the Virtual Machine, but here only the assembler file needs to be provided, using {file}
            
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
        logging.info("Main Window Init")        
        super().__init__()
        
        self.xProcessStatusDisplay = QtWidgets.QLabel()
        self.xRunner = self.cRunner(self)
        
        self.xTabContent = []
        self.xSender = cSender()
        self.xSender.CloseTab4QWidget.connect(self.CloseTab4QWidget)
        self.xSender.RemoteDragEnterEvent.connect(self.dragEnterEvent)
        self.xSender.RemoteDropEvent.connect(self.dropEvent)
        self.xSender.UpdateTabSaveColor.connect(self.UpdateTabSaveColor)

        self.ConnectLog2Sender(self.xSender)
        
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
        
        self.xBreakpoints = []
        
        self.InitUI()


    def ConnectLog2Sender(self, xSender):
            
        
        for xMember in dir(xSender):
            xSenderObject = getattr(xSender, xMember)
            
            if type(xSenderObject) is QtCore.pyqtBoundSignal and not hasattr(QtCore.QObject, xMember):
                exec("xSenderObject.connect(lambda: logging.debug('Signal: {}'))".format(xMember))


    def InitUI(self):
        xIconPath = xThisPath.replace("\\", "/") + "/assets/Icon.png"
        self.setWindowIcon(QtGui.QIcon(xIconPath))

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
        self.xMenuFile.addAction(self.NewMenuSubOption("Exit", self.ExitGui))
        
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
        

        self.xMenuRun.addAction(self.NewMenuSubOption("Run", self.RunCurrentProgram, "Ctrl+F1"))
        self.xMenuRun.addAction(self.NewMenuSubOption("Terminate", self.xRunner.Kill, "Shift+F1"))
        self.xMenuRun.addAction(self.NewMenuSubOption("Debug", self.DebugCurrentProgram, "F1"))        

        def AddBreakpoint():
            xCurrentWidget = self.xTabHost.currentWidget()
            xIndex = cUtils.GetCursorLineIndex(xCurrentWidget)

            #toggle
            if xIndex in xCurrentWidget.xBreakpoints: xCurrentWidget.xBreakpoints.remove(xIndex)
            else:                                     xCurrentWidget.xBreakpoints.append(xIndex)
            xCurrentWidget.xLineNumberArea.update()

        def ClearBreakpoint():
            xCurrentWidget = self.xTabHost.currentWidget()
            xCurrentWidget.xBreakpoints = []
            xCurrentWidget.xLineNumberArea.update()

        self.xMenuRun.addAction(self.NewMenuSubOption("Add Breakpoint here",   AddBreakpoint  , "F2"))
        self.xMenuRun.addAction(self.NewMenuSubOption("Clear all Breakpoints", ClearBreakpoint, "Shift+F2"))

        self.setWindowTitle("Baabnq IDE")
        self.LoadSetttings(self.xSettingsHandle)
        self.UpdateEditorFocus()
        self.show()        
    
    def FindGui(self):
        try:                self.xFindDialogInstance.close()
        except Exception:   pass
        
        self.xFindDialogInstance = self.cFindDialog(self)
        self.xSender.GlobalClose.connect(self.xFindDialogInstance.close)
    
    def MoveCurrentEditor(self, xLine):
        xEditor = self.xTabHost.currentWidget()
        xCursor = QtGui.QTextCursor(xEditor.document().findBlockByLineNumber(xLine))
        xEditor.setTextCursor(xCursor)
    
    def RunCurrentProgram(self):
        xCurrentTab = self.xTabHost.currentWidget()
        if xCurrentTab is not None:
            xPath = xCurrentTab.xFilePath
            self.xRunner.SetRunConfig(self.xCompilerCall, self.xVirtMachCall) #update call paths
            
            logging.info("Run Current Program")
            logging.debug(f"Path       : {xPath}".format())
            logging.debug( "Run Config: [{}, {}]".format(self.xCompilerCall, self.xVirtMachCall))
    
            self.xRunner.Run(xPath)
      
    def DebugCurrentProgram(self):
        xCurrentTab = self.xTabHost.currentWidget()
        if xCurrentTab is not None:
            xPath = xCurrentTab.xFilePath
            self.xRunner.SetRunConfig(self.xCompilerCall, self.xVirtMachCall) #update call paths
    
            logging.info("Debug Current Program")
            logging.debug(f"Path      : {xPath}".format())
            logging.debug( "Run Config: [{}, {}]".format(self.xCompilerCall, self.xVirtMachCall))
            logging.debug(f"Breakpoints: {self.xBreakpoints}".format())
    
            
            self.xRunner.Debug(xPath, self.xBreakpoints)
        
        
      
    #methods handle user setting
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
        logging.info("CloseTab")
        logging.debug(f"TabIndex: {xTabIndex}".format())
        
        if xTabIndex < 0: return
        
        self.xTabHost.removeTab(xTabIndex)
        self.xTabContent[xTabIndex][0].close()
        self.xTabContent.pop(xTabIndex)

        logging.debug(f"New TabContent List: {self.xTabContent}".format())

    #user file save
    def SaveFileGui(self):
        self.xTabHost.currentWidget().Save()
        self.xSender.UpdateTabSaveColor.emit()
    
    def RunConfigGui(self):
        self.xRunConfigDialogInstance = self.cRunConfigDialog(self.xSender)
        self.xSender.GlobalClose.connect(self.xRunConfigDialogInstance.close)
        
        
    def SaveAll(self):
        for xTabIter in self.xTabContent:
            xTabIter[0].Save()
    
    
    def OpenCodeEditorTab(self, xPath):
        logging.info("OpenCodeEditorTab")
        logging.debug(f"Path for new editor: {xPath}".format())        
        
        xCodeEditor = cCodeEditor(self)
        
        self.xTabHost.addTab(xCodeEditor, cUtils.Path2Name(xPath))
        self.xTabContent.append((xCodeEditor, ))
        
        xCodeEditor.xFilePath = xPath
        xUpdateSuccess = xCodeEditor.UpdateFromPath()
        
        xCodeEditor.xIsSaved = True
        self.UpdateTabSaveColor()
        
        logging.debug(f"New TabContent List: {self.xTabContent}".format())
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
        xLogDict = {xKey : xSettingsHandle.value(xKey) for xKey in xSettingsHandle.allKeys()}
        logging.info("Loading Settings")
        logging.debug("LogDict: " + str(xLogDict))
        
        try:
            self.resize(self.xSettingsHandle.value("windowSize"))
            self.move(self.xSettingsHandle.value("windowPos"))
        except Exception as E:
            logging.warn(str(E))
        
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


        try:
            xTabDataList = eval(self.xSettingsHandle.value("tabInstanceList"))
            for xTabDataIter in xTabDataList:
                xSuccess = self.OpenCodeEditorTab(xTabDataIter["filePath"])
                if xSuccess:
                    try:
                        self.xTabContent[-1][0].setFont(QtGui.QFont(self.xFontFamily, xTabDataIter["zoom"]))
                        self.xTabContent[-1][0].xBreakpoints = xTabDataIter["breakpoints"] 
                
                    except KeyError:
                        pass

        
            self.xTabHost.setCurrentIndex(xSettingsHandle.value("selectedTabIndex"))
            self.HandleClickAutoScroll()
            self.UpdateCompilerErrorCheck()
            self.UpdateJump2ErrorLine()

        except Exception as E:
            logging.warn(str(E))
        
    def SaveSettings(self, xSettingsHandle):
        logging.info("Saving Settings")

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
                "breakpoints" : xTabIter[0].xBreakpoints,
                
                })
        
        xSettingsHandle.setValue("tabInstanceList",  str(xTabDataList))
        xSettingsHandle.setValue("selectedTabIndex", self.xTabHost.currentIndex())            
        
        xLogDict = {xKey : xSettingsHandle.value(xKey) for xKey in xSettingsHandle.allKeys()}
        logging.debug("LogDict: " + str(xLogDict))


    def dragEnterEvent(self, xEvent):
        if xEvent.mimeData().hasText():
            xEvent.accept()
            
        else:
            xEvent.ignore()

    def dropEvent(self, xEvent):
        xRawPath = xEvent.mimeData().text()
        xPath = re.search("file:\/\/\/(.+)", xRawPath).group(1)
        self.OpenCodeEditorTab(xPath)
        
        super().dropEvent(xEvent)

    def closeEvent(self, xEvent):
        logging.info("closeEvent called")
        
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
        self.xSender.GlobalClose.emit()

        logging.info("Closing done, shutting down")
        logging.info("Goodbye, World")
