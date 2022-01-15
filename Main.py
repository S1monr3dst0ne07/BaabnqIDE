from PyQt5 import QtCore, QtGui, QtWidgets
import re
import sys




class cSender(QtCore.QObject):
    UpdateEditors = QtCore.pyqtSignal()



class cSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    xStyles = {
            "const":            [[255, 127, 000], False],
            "normalCommands":   [[000, 255, 000], False],
            "ops":              [[255, 000, 000], False],
            "vars":             [[000, 255, 255], False],
            "jumpOps":          [[255, 255, 000], False],
        }
    
    
    xRules = [
            
            ('put|print|input|putstr|asm|use',          xStyles["normalCommands"]),
            ('=|\<|\>|==|!=|\+|-|&|\||\^|\>\>|\<\<',    xStyles["ops"]),
            ('lab|jump',                                xStyles["jumpOps"]),
            ('_[^ ]*',                                  xStyles["vars"]),
            ("\d+",                                     xStyles["const"]),
            ("'[^']*'",                                 xStyles["const"]),
        
        
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
        self.xSender = xSender
        xSender.UpdateEditors.connect(self.UpdateFromPath)
        
        
        self.InitUI()
    
    
    def UpdateFromPath(self):
        try:
            with open(self.xFilePath, "r") as xFileHandle:
                self.setPlainText(xFileHandle.read())
                
        except FileNotFoundError:
            #if path was not found kill instance
            self.close()
            
    
    def InitUI(self):
        self.setFont(QtGui.QFont("Consolas"))
        self.setStyleSheet("background-color: #333333; color: #ffffff; border: 0px;")
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        
        self.verticalScrollBar().setStyleSheet(self.xScrollStyle.format(  sizeMod = "width:20px;", handelColor = "#444444"))
        self.horizontalScrollBar().setStyleSheet(self.xScrollStyle.format(sizeMod = "hight:20px;", handelColor = "#444444"))
        
        
class cWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.xTabInstances = []
        self.xSender = cSender()
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
        """)

        xCentralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(xCentralWidget)
        self.xMainLayout = QtWidgets.QGridLayout(xCentralWidget)

        
        self.xTabHost = QtWidgets.QTabWidget()
        self.xMainLayout.addWidget(self.xTabHost)

        self.xMenu = self.menuBar()
        self.xMenuFile = self.xMenu.addMenu("&File")
        self.xMenuOptions = self.xMenu.addMenu("&Options")

        self.xMenuFile.addAction(self.NewMenuSubOption("Open", self.OpenFileGui))



        self.show()


    def NewMenuSubOption(self, xName, xActionFunc):
        xNewAction = QtWidgets.QAction(xName, self)
        xNewAction.triggered.connect(xActionFunc)
        return xNewAction

    
    def OpenFileGui(self):
        xPath, _ = QtWidgets.QFileDialog.getOpenFileName(None, 'Open File', '', 'Baabnq File (*.baabnq)')
        if xPath != "": 
            self.OpenCodeEditorTab(xPath)


    def OpenCodeEditorTab(self, xPath): 
        xCodeEditor = cCodeEditor(self.xSender)
        xSyntaxHighlighter = cSyntaxHighlighter(xCodeEditor.document())
        
        self.xTabHost.addTab(xCodeEditor, self.Path2Name(xPath))
        
        #save reference to both the editor and it's highlighter
        self.xTabInstances.append((xCodeEditor, xSyntaxHighlighter))
        
        xCodeEditor.xFilePath = xPath
        self.xSender.UpdateEditors.emit()
        
    @staticmethod
    def Path2Name(xPath):
        return re.search("\/([^\/]+)\.", xPath).group(1)

    def keyPressEvent(self, xEvent):
        if xEvent.key() == QtCore.Qt.Key_Escape:
            self.close()





if __name__ == '__main__':
    xApp = QtWidgets.QApplication(sys.argv)
    xWindow = cWindow()
    
    sys.exit(xApp.exec())
