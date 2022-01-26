from PyQt5 import QtCore, QtGui, QtWidgets
import re
import sys



class cUtils:
    
    @staticmethod
    def RemoveDups(x):
        return list(set(x))



class cSender(QtCore.QObject):
    UpdateEditors           = QtCore.pyqtSignal()
    CloseTab4QWidget        = QtCore.pyqtSignal(QtWidgets.QWidget)
    RemoteDragEnterEvent    = QtCore.pyqtSignal(QtGui.QDragEnterEvent)
    RemoteDropEvent         = QtCore.pyqtSignal(QtGui.QDropEvent)
    UpdateTabSaveColor      = QtCore.pyqtSignal()
    UpdateCorrectorState    = QtCore.pyqtSignal(bool)
    UpdateCompleter         = QtCore.pyqtSignal()

class cCodeEditor(QtWidgets.QPlainTextEdit):
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
                ("\d+",                                     xStyles["const"]),
                ('_[^ ]*',                                  xStyles["vars"]),
                ("'[^']*'",                                 xStyles["constItal"]),
                ('\".*$',                                   xStyles["fazzedOut"]),
                (';$',                                      xStyles["fazzedOut"]),
                
            
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
        
        self.InitUI()
    
    
    def InsertCompletion(self, xFinalCompletion):
        if self.xCompleter.widget() is not self:
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
                
        except FileNotFoundError:
            #if path was not found kill instance
            QtWidgets.QMessageBox.about(self, "File lost", f"Reference to file at {self.xFilePath} has been lost\nThis my be due to the deletion or renaming of that file".format())
            self.xSender.CloseTab4QWidget.emit(self)
            
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
        self.verticalScrollBar().setStyleSheet(self.xScrollStyle.format(  sizeMod = "width:20px;", handelColor = "#444444"))
        self.horizontalScrollBar().setStyleSheet(self.xScrollStyle.format(sizeMod = "hight:20px;", handelColor = "#444444"))

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

        xRawChop  = self.ChopChopSplit(self.toPlainText(), xDelims)
        xNewModel = self.xBaseCommands + [x for x in xRawChop \
                       if x not in (xCompletionPrefix, '')
                       
                       
                    ]
        
        print(cUtils.RemoveDups(xNewModel))
        self.xCompleter.SetCompleterModel(cUtils.RemoveDups(xNewModel))


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


        if xEvent.key() == QtCore.Qt.Key_Return and self.xCompleterStatus:
            self.InsertCompletion(self.xCompleter.popup().currentIndex().data())
            
        else:
            super().keyPressEvent(xEvent)
        
class cWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.xTabContent = []
        self.xSender = cSender()
        self.xSender.CloseTab4QWidget.connect(self.CloseTab4QWidget)
        self.xSender.RemoteDragEnterEvent.connect(self.dragEnterEvent)
        self.xSender.RemoteDropEvent.connect(self.dropEvent)
        self.xSender.UpdateTabSaveColor.connect(self.UpdateTabSaveColor)
                
        self.setAcceptDrops(True)
        self.xFontFamily = "consolas"

        self.xTabHost = QtWidgets.QTabWidget()
        self.xSettingsHandle = QtCore.QSettings("BaabnqIde", "MainSettings")
        self.LoadSetttings(self.xSettingsHandle)
        
        self.InitUI()

    def InitUI(self):

        self.setStyleSheet("""
        QMainWindow {background-color:#555555;}
    
        QMenuBar {
            background-color: #333333;
            color: white;
        }
        QTabBar               {background: gray;}
        QTabBar::tab:selected {background: red;} 
        """)




        xCentralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(xCentralWidget)
        self.xMainLayout = QtWidgets.QGridLayout(xCentralWidget)

        
        self.xTabHost.setStyleSheet("""
        QWidget {background-color: #333333} 
        QTabWidget::pane {border: 0;} 
        QTabBar::tab {background: #454545;} 
        QTabBar::tab::selected {background-color: #202020;}
        
        """)
        self.xTabHost.setTabsClosable(False)
        self.xMainLayout.addWidget(self.xTabHost)

        self.xMenu = self.menuBar()
        self.xMenuFile = self.xMenu.addMenu("&File")
        self.xMenuView = self.xMenu.addMenu("&View")
        self.xMenuOptions = self.xMenu.addMenu("&Options")
        self.xDebug = self.xMenu.addMenu("&DEV DEBUG(don't use this)")

        self.xMenuFile.addAction(self.NewMenuSubOption("Open File", self.OpenFileGui, "Ctrl+O"))
        self.xMenuFile.addAction(self.NewMenuSubOption("Close File", lambda: self.CloseTab(self.xTabHost.currentIndex()), "Ctrl+W"))
        self.xMenuFile.addAction(self.NewMenuSubOption("Save File", self.SaveFileGui, "Ctrl+S"))
        self.xMenuFile.addAction(self.NewMenuSubOption("Refresh Editors", self.RefreshGui, ""))
        self.xMenuFile.addAction(self.NewMenuSubOption("Exit", self.ExitGui, "Esc"))
        
        #very ugly line for zooming, directly calls zoomIn method of the qplaintextedit
        self.xMenuView.addAction(self.NewMenuSubOption("Zoom in", lambda: self.xTabHost.currentWidget().zoomIn(+1), "Ctrl++"))
        self.xMenuView.addAction(self.NewMenuSubOption("Zoom out", lambda: self.xTabHost.currentWidget().zoomIn(-1), "Ctrl+-"))
        self.xMenuView.addAction(self.NewMenuSubOption("Corrector Enabled", self.ToggleCorrector, "Ctrl+Space", True))

        self.xDebug.addAction(self.NewMenuSubOption("Reload Tab Colors", self.UpdateTabSaveColor, ""))


        self.setWindowTitle("Baabnq IDE")
        self.show()



    def ToggleCorrector(self):
        xCheckedState = self.xMenuView.actions()[2].isChecked()
        self.xSender.UpdateCorrectorState.emit(xCheckedState)
        self.xSender.UpdateCompleter.emit()

    #helper method used for constructing the menu bar
    def NewMenuSubOption(self, xName = "", xActionFunc = None, xShort = "", xCheckable = False):
        xNewAction = QtWidgets.QAction(xName, self, checkable = xCheckable)
        xNewAction.triggered.connect(xActionFunc)
        xNewAction.setShortcut(QtGui.QKeySequence(xShort))
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

    def CloseTab(self, xTabIndex):
        if xTabIndex < 0: return
        
        self.xTabHost.removeTab(xTabIndex)
        self.xTabContent[xTabIndex][0].close()
        self.xTabContent.pop(xTabIndex)

    #user file save
    def SaveFileGui(self):
        self.xTabHost.currentWidget().Save()
        self.xSender.UpdateTabSaveColor.emit()
    
    def SaveAll(self):
        for xTabIter in self.xTabContent:
            xTabIter[0].Save()
    
    
    def OpenCodeEditorTab(self, xPath): 
        xCodeEditor = cCodeEditor(self.xSender, self.xFontFamily)
        
        self.xTabHost.addTab(xCodeEditor, self.Path2Name(xPath))
        self.xTabContent.append((xCodeEditor, ))
        
        xCodeEditor.xFilePath = xPath
        self.xSender.UpdateEditors.emit()
        
        xCodeEditor.xIsSaved = True
        self.UpdateTabSaveColor()
        
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

        xTabDataList = eval(self.xSettingsHandle.value("tabInstanceList"))
        for xTabDataIter in xTabDataList:
            self.OpenCodeEditorTab(xTabDataIter["filePath"])
            self.xTabContent[-1][0].setFont(QtGui.QFont(self.xFontFamily, xTabDataIter["zoom"]))
            
            
        
        self.xTabHost.setCurrentIndex(xSettingsHandle.value("selectedTabIndex"))
        
        
    def SaveSettings(self, xSettingsHandle):
        xSettingsHandle.setValue("windowPos", self.pos())
        xSettingsHandle.setValue("windowSize", self.size())

        xTabDataList = []
        
        #get data from tab content
        for xTabIter in self.xTabContent:
            xTabDataList.append({
                "filePath" : xTabIter[0].xFilePath,
                "zoom"     : xTabIter[0].font().pointSize()
                
                })
        
        xSettingsHandle.setValue("tabInstanceList",  str(xTabDataList))
        xSettingsHandle.setValue("selectedTabIndex", self.xTabHost.currentIndex())            
        
        
        
        
    @staticmethod
    def Path2Name(xPath):
        xMatch = re.search("[^\/]+\.[^\/]+$", xPath)
        return xMatch[0]


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
            xExitSaveDialog = QtWidgets.QMessageBox(self)
            xExitSaveDialog.setWindowTitle("Save?")
            xExitSaveDialog.setText("Save changes before closing?")
            xExitSaveDialog.setStandardButtons(QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
            xExitSaveDialog.setDefaultButton(QtWidgets.QMessageBox.Save)
            
            xSaveDecision = xExitSaveDialog.exec_()
            if xSaveDecision == QtWidgets.QMessageBox.Save:
                self.SaveAll()
                
            elif xSaveDecision == QtWidgets.QMessageBox.Discard:
                pass
            
            elif xSaveDecision == QtWidgets.QMessageBox.Cancel:
                xEvent.ignore()
                return
            
        self.SaveSettings(self.xSettingsHandle)
            
        

if __name__ == '__main__':
    xApp = QtWidgets.QApplication(sys.argv)
    xWindow = cWindow()
    
    sys.exit(xApp.exec())
