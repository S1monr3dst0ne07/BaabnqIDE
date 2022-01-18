from PyQt5 import QtCore, QtGui, QtWidgets
import re
import sys




class cSender(QtCore.QObject):
    UpdateEditors = QtCore.pyqtSignal()
    CloseTab4QWidget = QtCore.pyqtSignal(QtWidgets.QWidget)
    RemoteDragEnterEvent = QtCore.pyqtSignal(QtGui.QDragEnterEvent)
    RemoteDropEvent = QtCore.pyqtSignal(QtGui.QDropEvent)
    UpdateTabSaveColor = QtCore.pyqtSignal()

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


class cCodeEditor(QtWidgets.QPlainTextEdit):
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
    
    
    def __init__(self, xSender):
        super().__init__()
        self.xFilePath = ""
        self.xIsSaved = True #keep track of if the file in this editor instance is saved to it's source
        self.xRestoreIsSavedState = None #switch state for restoring saved state when doing weird stuff
        
        self.xFontFamily = "Consolas"
        
        self.xSender = xSender
        xSender.UpdateEditors.connect(self.UpdateFromPath)
        self.textChanged.connect(self.Change)        
        
        self.InitUI()    
    
    #load file from path and update content of editor
    def UpdateFromPath(self):
        try:
            with open(self.xFilePath, "r") as xFileHandle:
                self.setPlainText(xFileHandle.read())
                
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
        
    #trigger that's called when the editor content changes, need for updating status stuff and such
    def Change(self):
        self.xIsSaved = False
        self.xSender.UpdateTabSaveColor.emit()
        
        
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
        
        self.InitUI()

    def InitUI(self):
        self.setStyleSheet("""
        QMainWindow {
            background-color:#555555;
        }
    
        QMenuBar {
            background-color: #333333;
            color: white;
        }               
        QTabBar {background: gray;}
        QTabBar::tab:selected {                            
            background: #0000ff;                             
        } 
        """)

        xCentralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(xCentralWidget)
        self.xMainLayout = QtWidgets.QGridLayout(xCentralWidget)

        
        self.xTabHost = QtWidgets.QTabWidget()
        self.xTabHost.setStyleSheet("QWidget {background-color: #333333} QTabWidget::pane {border: 0;} QTabBar::tab {background: #333333;} ")
        self.xTabHost.setTabsClosable(False)
        self.xMainLayout.addWidget(self.xTabHost)

        self.xMenu = self.menuBar()
        self.xMenuFile = self.xMenu.addMenu("&File")
        self.xMenuView = self.xMenu.addMenu("&View")
        self.xMenuOptions = self.xMenu.addMenu("&Options")

        self.xMenuFile.addAction(self.NewMenuSubOption("Open File", self.OpenFileGui, "Ctrl+O"))
        self.xMenuFile.addAction(self.NewMenuSubOption("Close File", lambda: self.CloseTab(self.xTabHost.currentIndex()), "Ctrl+W"))
        self.xMenuFile.addAction(self.NewMenuSubOption("Save File", self.SaveFileGui, "Ctrl+S"))
        self.xMenuFile.addAction(self.NewMenuSubOption("Refresh Editors", self.RefreshGui, ""))
        self.xMenuFile.addAction(self.NewMenuSubOption("Exit", self.ExitGui, "Esc"))
        
        #very ugly line for zooming, directly calls zoomIn method of the qplaintextedit
        self.xMenuView.addAction(self.NewMenuSubOption("Zoom in", lambda: self.xTabHost.currentWidget().zoomIn(+1), "Ctrl++"))
        self.xMenuView.addAction(self.NewMenuSubOption("Zoom in", lambda: self.xTabHost.currentWidget().zoomIn(-1), "Ctrl+-"))


        self.show()


    #helper method used for constructing the menu bar
    def NewMenuSubOption(self, xName, xActionFunc, xShort):
        xNewAction = QtWidgets.QAction(xName, self)
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
    
    
    def OpenCodeEditorTab(self, xPath): 
        xCodeEditor = cCodeEditor(self.xSender)
        xSyntaxHighlighter = cSyntaxHighlighter(xCodeEditor.document())
        
        self.xTabHost.addTab(xCodeEditor, self.Path2Name(xPath))
        self.xTabContent.append((xCodeEditor, xSyntaxHighlighter))
        
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

        

if __name__ == '__main__':
    xApp = QtWidgets.QApplication(sys.argv)
    xWindow = cWindow()
    
    sys.exit(xApp.exec())
