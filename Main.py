from PyQt5 import QtCore, QtGui, QtWidgets
import re
import sys
import ctypes
import time
import shlex


class cUtils:
    xScrollStyle = """
    QScrollBar::up-arrow, QScrollBar::down-arrow {{
        background: none;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: none;
    }}
            
    QScrollBar {{
        border: 1px solid #111111;
        background: solid #111111;

        {sizeMod}
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop: 0 {handelColor}, stop: 0.5 {handelColor}, stop:1 {handelColor});
        min-height: 0px;
    }}
    QScrollBar::add-line {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop: 0 {handelColor}, stop: 0.5 {handelColor},  stop:1 {handelColor});
        height: 0px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
    }}
    QScrollBar::sub-line {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop: 0 {handelColor}, stop: 0.5 {handelColor},  stop:1 {handelColor});
        height: 0 px;
        subcontrol-position: top;
        subcontrol-origin: margin;
    }}
                                            """
    
    xQPushButtonCss = """
QPushButton:!pressed
{
  border: 1px solid #ffffff;
}
QPushButton:hover:!pressed
{
  border: 1px solid #ffffff;
  background-color: #666666;
}
QPushButton:pressed
{
  border: 1px solid #6D81FF;
}

    
    """
    
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
    def Quotes(xRaw):
        return '"' + xRaw + '"'
                

class cSender(QtCore.QObject):
    UpdateEditors           = QtCore.pyqtSignal()
    CloseTab4QWidget        = QtCore.pyqtSignal(QtWidgets.QWidget)
    RemoteDragEnterEvent    = QtCore.pyqtSignal(QtGui.QDragEnterEvent)
    RemoteDropEvent         = QtCore.pyqtSignal(QtGui.QDropEvent)
    UpdateTabSaveColor      = QtCore.pyqtSignal()
    UpdateCorrectorState    = QtCore.pyqtSignal(bool)
    UpdateCompleter         = QtCore.pyqtSignal()
    SetCompilerCall         = QtCore.pyqtSignal(str)
    SetVirtMachCall         = QtCore.pyqtSignal(str)

class cCodeEditor(QtWidgets.QPlainTextEdit):
    class cLineNumberArea(QtWidgets.QWidget):
        def __init__(self, xEditor):
            super().__init__(xEditor)
            self.xEditor = xEditor
    
        def sizeHint(self):
            return Qsize(self.xEditor.LineNumberAreaWidth(), 0)
        
        def paintEvent(self, event):
            self.xEditor.LineNumberAreaPaintEvent(event)
    
    
    class cCompleter(QtWidgets.QCompleter):
        def __init__(self):
            QtWidgets.QCompleter.__init__(self)

        def splitPath(self, xPath):
            return xPath.split(" ")

        def pathFromIndex(self, xIndex):
            return self.model().data(xIndex, QtCore.Qt.DisplayRole)

        def SetCompleterModel(self, xNewModel):
            xModel = QtGui.QStandardItemModel(self)
            
            for xModelItemIter in xNewModel:
                xModel.appendRow(QtGui.QStandardItem(xModelItemIter))
            
            self.setModel(xModel)
        
    class cSyntaxHighlighter(QtGui.QSyntaxHighlighter):
        #color for syntax highlighting
        xStyles = {
                "constItal":        [[255, 127, 000], True],
                "const":            [[255, 127, 000], False],
                "normalCommands":   [[000, 255, 000], False],
                "ops":              [[255, 000, 000], False],
                "vars":             [[000, 255, 255], False],
                "jumpOps":          [[255, 255, 000], False],
                "stackCommands":    [[255, 000, 255], False],
                "fazzedOut":        [[127, 127, 127], True],
                "memAlloc":         [[127, 142, 255], False],
            }
        
        
        #regex rules for syntax highlighting
        xRules = [
                
                ('put|print|input|putstr|asm|use',          xStyles["normalCommands"]),
                ('pull|push|sub|return',                    xStyles["stackCommands"]),
                ('=|\<|\>|==|!=|\+|-|&|\||\^|\>\>|\<\<',    xStyles["ops"]),
                ('->|<-|new|free',                          xStyles["memAlloc"]),
                ('lab|jump',                                xStyles["jumpOps"]),
                ("\W\d+\W",                                 xStyles["const"]),
                ('_[^ ]*',                                  xStyles["vars"]),
                ('\".*$',                                   xStyles["fazzedOut"]),
                (';',                                       xStyles["fazzedOut"]),
                ("'[^']*'",                                 xStyles["constItal"]),
                
            
            ]
    
        xRulesQRegExp = [(QtCore.QRegExp(xExp), xStyle) for (xExp, xStyle) in xRules]
        
        def __init__(self, xDoc):
            QtGui.QSyntaxHighlighter.__init__(self, xDoc)
    
        def getFormat(self, xStyle):
            xFormat = QtGui.QTextCharFormat()
            if len(xStyle) > 0: xFormat.setForeground(QtGui.QColor(*xStyle[0]))
            if len(xStyle) > 1: xFormat.setFontItalic(xStyle[1])
            return xFormat
    
        def highlightBlock(self, xText):
            
            for (xExp, xStyle) in self.xRulesQRegExp:
                
                #xIndex = xText.indexOf(xExp)
                xIndex = xExp.indexIn(xText)            
                while xIndex >= 0:
                    xLengh = xExp.matchedLength()
                    
                    self.setFormat(xIndex, xLengh, self.getFormat(xStyle))
                    xIndex = xExp.indexIn(xText, xIndex + xLengh)


    
    xBaseCommands = ["put", "print", "input", "putstr", "asm", "use", "pull", "push", "sub", "return", "new", "free", "lab", "jump"]
    

    def __init__(self, xSender, xFontFamily):
        super().__init__()
        self.xFilePath = ""
        self.xIsSaved = True #keep track of if the file in this editor instance is saved to it's source
        self.xRestoreIsSavedState = None #switch state for restoring saved state when doing weird stuff
        
        self.xSyntaxHighlighter = self.cSyntaxHighlighter(self.document())
        self.xCompleter         = self.cCompleter()
        self.xCompleter.setWidget(self)
        self.UpdateCompleterModel("")
        self.xCompleterStatus = False

        self.xCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.xCompleter.activated.connect(self.InsertCompletion)

        self.xFontFamily = xFontFamily
        
        self.xSender = xSender
        xSender.UpdateEditors.connect(self.UpdateFromPath)
        self.textChanged.connect(self.Change)  
        self.xSender.UpdateCorrectorState.connect(self.SetCompleterStatus)
        self.xSender.UpdateCompleter.connect(self.UpdateCompleter)



        self.xLineNumberArea = self.cLineNumberArea(self)

        self.blockCountChanged.connect(self.UpdateLineNumberAreaWidth)
        self.updateRequest.connect(self.UpdateLineNumberArea)
        self.cursorPositionChanged.connect(self.HighlightCurrentLine)
        
        self.UpdateLineNumberAreaWidth(0)



        
        self.InitUI()
    
    
    def InsertCompletion(self, xFinalCompletion):
        if self.xCompleter.widget() is not self or xFinalCompletion is None:
            return

        xTextCursor = self.textCursor()
        xExtra = len(xFinalCompletion) - len(self.xCompleter.completionPrefix())
        xTextCursor.movePosition(QtGui.QTextCursor.Left)
        xTextCursor.movePosition(QtGui.QTextCursor.EndOfWord)
        xTextCursor.insertText(xFinalCompletion[-xExtra:])
        self.setTextCursor(xTextCursor)
        
            
    def SetCompleterStatus(self, xNewStatus):
        self.xCompleterStatus = xNewStatus    
    
    #load file from path and update content of editor
    def UpdateFromPath(self):
        try:
            with open(self.xFilePath, "r") as xFileHandle:
                self.setPlainText(xFileHandle.read())
                self.xIsSaved = True
                return True
                
        except FileNotFoundError:
            #if path was not found kill instance
            QtWidgets.QMessageBox.about(self, "File lost", f"Reference to file at {self.xFilePath} has been lost\nThis my be due to the deletion or renaming of that file".format())
            self.xSender.CloseTab4QWidget.emit(self)#
            return False
            
    #write editor content back to path
    def Save(self):
        try:
            with open(self.xFilePath, "w") as xFileHandle:
                xFileHandle.write(self.toPlainText())
                
            self.xIsSaved = True
                
        except Exception as E:
            QtWidgets.QMessageBox.about(self, E)
                
    
    def InitUI(self):
        self.setFont(QtGui.QFont(self.xFontFamily))
        self.setStyleSheet("background-color: #333333; color: #ffffff; border: 0px;")
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

        #override the look of the scroll bar to match the overall theme (which btw is a pain in the ass)
        self.verticalScrollBar().setStyleSheet(  cUtils.xScrollStyle.format(sizeMod = "width:20px;", handelColor = "#444444"))
        self.horizontalScrollBar().setStyleSheet(cUtils.xScrollStyle.format(sizeMod = "hight:20px;", handelColor = "#444444"))

    #drag and drop events
    def dragEnterEvent(self, xEvent):
        self.xSender.RemoteDragEnterEvent.emit(xEvent)
        self.xRestoreIsSavedState = self.xIsSaved
        
    def dropEvent(self, xEvent):
        self.xSender.RemoteDropEvent.emit(xEvent)
        self.xIsSaved = self.xRestoreIsSavedState
        self.xSender.UpdateTabSaveColor.emit()

    def TextUnderCursor(self):
        xTextCursor = self.textCursor()
        xTextCursor.select(QtGui.QTextCursor.WordUnderCursor)
        return xTextCursor.selectedText()

    #trigger that's called when the editor content changes, need for updating status stuff and such
    def Change(self):        
        self.xIsSaved = False
        self.xSender.UpdateTabSaveColor.emit()
        self.xSender.UpdateCompleter.emit()

    def ChopChopSplit(self, xStr, xDelimiters):
        xList = [xStr]
        
        
        for xDelimIter in xDelimiters:
            xNewList = []
            
            for x in xList: xNewList += x.split(xDelimIter)
            xList = xNewList

        return xList

    #xCompletionPrefix is give to be excluded
    def UpdateCompleterModel(self, xCompletionPrefix):      
        xDelims = (" ", ";", "\n")

        xNewModel = self.xBaseCommands + self.ChopChopSplit(self.toPlainText(), xDelims)
        xNewModelFilter = [x for x in xNewModel \
                       if x not in (xCompletionPrefix, '')
                       
                       
                    ]
        
        self.xCompleter.SetCompleterModel(cUtils.RemoveDups(xNewModelFilter))


    def UpdateCompleter(self):
        
        #update completer
        xCompletionPrefix = self.TextUnderCursor()
        self.xCompleter.setCompletionPrefix(xCompletionPrefix)
        self.UpdateCompleterModel(xCompletionPrefix)


        xCursorRect = self.cursorRect()
        xCursorRect.setWidth(self.xCompleter.popup().sizeHintForColumn(0) + self.xCompleter.popup().verticalScrollBar().sizeHint().width())
        self.xCompleter.complete(xCursorRect)

        xMatchCount = self.xCompleter.completionCount()
        xVisible = xCompletionPrefix != "" and xMatchCount > 0 and self.xCompleterStatus
        
        #set visibility of pop-up
        self.xCompleter.popup().show() if xVisible else self.xCompleter.popup().hide()

    def keyPressEvent(self, xEvent):
        if xEvent.key() == QtCore.Qt.Key_Tab and self.xCompleterStatus:
            self.InsertCompletion(self.xCompleter.popup().currentIndex().data())
            
        else:
            self.xSender.UpdateCompleter.emit()
            super().keyPressEvent(xEvent)







    def LineNumberAreaWidth(self):
        xDigits = 1
        xCount = max(1, self.blockCount())
        while xCount >= 10:
            xCount /= 10
            xDigits += 1
        xSpace = 3 + self.fontMetrics().width('9') * xDigits
        return xSpace


    def UpdateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.LineNumberAreaWidth(), 0, 0, 0)


    def UpdateLineNumberArea(self, xRect, xDy):

        if xDy:
            self.xLineNumberArea.scroll(0, xDy)
        else:
            self.xLineNumberArea.update(0, xRect.y(), self.xLineNumberArea.width(),
                       xRect.height())

        if xRect.contains(self.viewport().rect()):
            self.UpdateLineNumberAreaWidth(0)


    def resizeEvent(self, xEvent):
        super().resizeEvent(xEvent)

        xContRect = self.contentsRect();
        self.xLineNumberArea.setGeometry(QtCore.QRect(xContRect.left(), xContRect.top(),
                    self.LineNumberAreaWidth(), xContRect.height()))


    def LineNumberAreaPaintEvent(self, xEvent):
        xPainter = QtGui.QPainter(self.xLineNumberArea)

        xPainter.fillRect(xEvent.rect(), QtGui.QColor("#2a2a2a"))
        xPainter.setPen(                QtGui.QColor('#8E8E8E'))
        xPainter.setFont(QtGui.QFont(self.xFontFamily, self.font().pointSize()))

        xBlock = self.firstVisibleBlock()
        xBlockNumber = xBlock.blockNumber()
        xTop = self.blockBoundingGeometry(xBlock).translated(self.contentOffset()).top()
        xBottom = xTop + self.blockBoundingRect(xBlock).height()

        # Just to make sure I use the right font
        xHeight = self.fontMetrics().height()
        while xBlock.isValid() and (xTop <= xEvent.rect().bottom()):
            if xBlock.isVisible() and (xBottom >= xEvent.rect().top()):
                xNumber = str(xBlockNumber + 1)
                xPainter.drawText(0, int(xTop), self.xLineNumberArea.width(), xHeight,
                 QtCore.Qt.AlignRight, xNumber)

            xBlock = xBlock.next()
            xTop = xBottom
            xBottom = xTop + self.blockBoundingRect(xBlock).height()
            xBlockNumber += 1


    def HighlightCurrentLine(self):
        xExtraSelections = []

        if not self.isReadOnly():
            xSelection = QtWidgets.QTextEdit.ExtraSelection()

            xLineColor = QtGui.QColor("#4C4C4C")

            xSelection.format.setBackground(xLineColor)
            xSelection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            xSelection.cursor = self.textCursor()
            xSelection.cursor.clearSelection()
            xExtraSelections.append(xSelection)
        self.setExtraSelections(xExtraSelections)









class cRunConsole(QtWidgets.QPlainTextEdit):
    def __init__(self, xParent):
        super().__init__()
        self.xAutoScroll = False
        self.setFont(QtGui.QFont())
        self.setStyleSheet("background-color: #333333; color: #ffffff; border: 0px;")
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

        #override the look of the scroll bar to match the overall theme (which btw is a pain in the ass)
        self.verticalScrollBar().setStyleSheet(  cUtils.xScrollStyle.format(sizeMod = "width:20px;", handelColor = "#444444"))
        self.horizontalScrollBar().setStyleSheet(cUtils.xScrollStyle.format(sizeMod = "hight:20px;", handelColor = "#444444"))
        
        self.textChanged.connect(self.Change)
    
    def SetAutoScroll(self, xNewState):
        self.xAutoScroll = xNewState
    
              
    def Change(self):
        if self.xAutoScroll:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class cWindow(QtWidgets.QMainWindow):
    class cAsyncProgressTracker(QtCore.QThread):
        def __init__(self, xDisplayObject, xSourceProcess, xDisplayName):
            super().__init__()
            self.xDisplayObject = xDisplayObject #object the progress will be displayed in
            self.xDisplayName   = xDisplayName
            self.xSourceProcess = xSourceProcess
            self.xStopFlag = False

        def __del__(self):
            self.quit()
            self.wait()
        
        def stop(self):
            self.xStopFlag = True
        
        def run(self):
            xPointAnimation = 1
            while self.xSourceProcess.state() != QtCore.QProcess.NotRunning and not self.xStopFlag:
                time.sleep(0.1)
                self.xDisplayObject.setText(self.xDisplayName + xPointAnimation * ".")

                if xPointAnimation < 3: xPointAnimation += 1
                else                  : xPointAnimation = 0

            self.xDisplayObject.setText("")


    class cRunConfigDialog(QtWidgets.QWidget):
        def __init__(self, xSender):
            super().__init__()
            self.xSender = xSender

            xPointSize = 10

            self.setStyleSheet("background-color:#555555; color:#ffffff")
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
            self.xCompilerCall.setFont(QtGui.QFont("Consolas", xPointSize))
            self.xVirtMachCall.setFont(QtGui.QFont("Consolas", xPointSize))
            self.xCompilerCall.setStyleSheet("border: 1px solid white; ")
            self.xVirtMachCall.setStyleSheet("border: 1px solid white;")
            self.xCompilerCall.setFixedHeight(self.xCompilerCall.font().pointSize() * 2)
            self.xVirtMachCall.setFixedHeight(self.xVirtMachCall.font().pointSize() * 2)

            self.xLayout.addWidget(self.xCompilerCall, 1, 1)
            self.xLayout.addWidget(self.xVirtMachCall, 2, 1)



            xCompilerText = QtWidgets.QLabel("Compiler: ")
            xVirtMachText = QtWidgets.QLabel("VirtMach: ")
            xCompilerText.setFont(QtGui.QFont("Consolas", xPointSize))
            xVirtMachText.setFont(QtGui.QFont("Consolas", xPointSize))
            xCompilerText.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            xVirtMachText.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            
            self.xLayout.addWidget(xCompilerText, 1, 0)
            self.xLayout.addWidget(xVirtMachText, 2, 0)
            
            xApplyButton = QtWidgets.QPushButton("Apply")
            xApplyButton.setStyleSheet(cUtils.xQPushButtonCss)
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
        
        self.xProcessTracker = None
        self.xCompilerProcess = None
        self.xVirtMachProcess = None
        
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
        self.xFontFamily = "consolas"        
        self.xDialogInstance = None
        
        self.InitUI()

    def InitUI(self):

#        QTabBar               {background: gray;}
#        QTabBar::tab:selected {background: red;} 
        self.setStyleSheet("""
        QMainWindow {background-color:#555555;}
    
        QMenuBar {
            background-color: #333333;
            color: white;
        }
        """)




        xCentralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(xCentralWidget)
        self.xMainLayout = QtWidgets.QGridLayout(xCentralWidget)
        self.xSplitterContainer = QtWidgets.QSplitter()
        self.xMainLayout.addWidget(self.xSplitterContainer, 0, 0)
        
        #process status
        self.xProcessStatus = QtWidgets.QLabel()
        self.xProcessStatus.setFixedHeight(15)
        self.xProcessStatus.setFont(QtGui.QFont(self.xFontFamily, 10))
        self.xProcessStatus.setStyleSheet("color: white")
        self.xMainLayout.addWidget(self.xProcessStatus, 1, 0)



        #main tab host
        self.xTabHost = QtWidgets.QTabWidget()
        self.xSettingsHandle = QtCore.QSettings("BaabnqIde", "MainSettings")
        self.xTabHost.setStyleSheet("""
        QWidget {background-color: #333333} 
        QTabWidget::pane {border: 0;} 
        QTabBar::tab {background: #454545;} 
        QTabBar::tab::selected {background-color: #202020;}
        
        
        """)
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
        
        #very ugly line for zooming, directly calls zoomIn method of the qplaintextedit
        def GlobalZoom(xDelta):
            if any([x[0].hasFocus() for x in self.xTabContent]):
                self.xTabHost.currentWidget().zoomIn(xDelta)
                
            elif self.xConsole.hasFocus():
                self.xConsole.zoomIn(xDelta)
                
                
        self.xMenuView.addAction(self.NewMenuSubOption("Zoom in",  lambda: GlobalZoom(+1), "Ctrl++"))
        self.xMenuView.addAction(self.NewMenuSubOption("Zoom out", lambda: GlobalZoom(-1), "Ctrl+-"))

        self.xConsoleSubmenu = self.xMenuOptions.addMenu("Console")        
        def HandleClickAutoScroll(): return self.xConsole.SetAutoScroll(self.xConsoleSubmenu.actions()[1].isChecked())
        self.HandleClickAutoScroll = HandleClickAutoScroll
        self.xConsoleSubmenu.addAction(self.NewMenuSubOption("Clear", self.xConsole.clear, "Ctrl+1"))
        self.xConsoleSubmenu.addAction(self.NewMenuSubOption("Autoscroll  Enabled", HandleClickAutoScroll, "", True))
                
        self.xMenuOptions.addAction(self.NewMenuSubOption("Corrector Enabled", self.ToggleCorrector, "Ctrl+Space", True))
        self.xMenuOptions.addAction(self.NewMenuSubOption("Run Config", self.RunConfigGui, ""))

        self.xMenuRun.addAction(self.NewMenuSubOption("Run", self.RunCurrentProgram, "F1"))
        self.xMenuRun.addAction(self.NewMenuSubOption("Terminate", self.KillCurrentProgram, "Shift+F1"))



        self.setWindowTitle("Baabnq IDE")
        self.LoadSetttings(self.xSettingsHandle)
        self.show()


    def Compile(self, xSourcePath = "", xDestPath = "", StdoutHandleFunc = None, xFinishInvoke = cUtils.Noop):
        def HandleOutput():
            StdoutHandleFunc(self.xCompilerProcess.readAllStandardOutput().data().decode())
                
        if self.xCompilerProcess: self.xCompilerProcess.kill()
        self.xCompilerProcess = QtCore.QProcess()
        
        if StdoutHandleFunc:
            self.xCompilerProcess.readyReadStandardOutput.connect(HandleOutput)
        
        xCallArgs = shlex.split(self.xCompilerCall.replace("<input>", cUtils.Quotes(xSourcePath)).replace("<output>", cUtils.Quotes(xDestPath)))
        print(xCallArgs)
        self.xCompilerProcess.start(xCallArgs[0], xCallArgs[1:])
        
        if self.xProcessTracker and self.xProcessTracker.isRunning(): self.xProcessTracker.stop()
        self.xProcessTracker = self.cAsyncProgressTracker(self.xProcessStatus, self.xCompilerProcess, "Compiling")
        self.xProcessTracker.finished.connect(xFinishInvoke)
        self.xProcessTracker.start()

    def Launch(self, xSourcePath = "", StdoutHandleFunc = None, xFinishInvoke = cUtils.Noop):
        def HandleOutput():
            StdoutHandleFunc(self.xVirtMachProcess.readAllStandardOutput().data().decode())
        
        if self.xVirtMachProcess: self.xVirtMachProcess.kill()
        self.xVirtMachProcess = QtCore.QProcess()
        
        if StdoutHandleFunc:
            self.xVirtMachProcess.readyReadStandardOutput.connect(HandleOutput)
        
        xCallArgs = shlex.split(self.xVirtMachCall.replace("<file>", cUtils.Quotes(xSourcePath)))
        print(xCallArgs)
        self.xVirtMachProcess.start(xCallArgs[0], xCallArgs[1:])
        
        if self.xProcessTracker and self.xProcessTracker.isRunning(): self.xProcessTracker.stop()
        self.xProcessTracker = self.cAsyncProgressTracker(self.xProcessStatus, self.xVirtMachProcess, "Running")
        self.xProcessTracker.finished.connect(xFinishInvoke)
        self.xProcessTracker.start()


    def RunCurrentProgram(self):
        def HandleLaunch():
            self.Launch("build.s1", self.Write2Console)
        
        def HandleCompilerOut(xStdout):
            print(xStdout)
        
        def HandleCompile():
            self.Compile(self.xTabHost.currentWidget().xFilePath, "build.s1", HandleCompilerOut, HandleLaunch)
        
        HandleCompile()



    def Write2Console(self, xNewText):
        self.xConsole.insertPlainText(xNewText)
            
    def KillCurrentProgram(self):
        if self.xCompilerProcess: self.xCompilerProcess.kill()
        if self.xVirtMachProcess: self.xVirtMachProcess.kill()

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
            if xCurrentWidget.xIsSaved: xColor = QtGui.QColor("#05A000")
            else:                       xColor = QtGui.QColor("#FF5200")
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
        
        if self.xCompilerProcess: self.xCompilerProcess.kill()

        

if __name__ == '__main__':
    xApp = QtWidgets.QApplication(sys.argv)
    xWindow = cWindow()
    
    sys.exit(xApp.exec())
