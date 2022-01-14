from PyQt5 import QtCore, QtGui, QtWidgets
import re
import sys









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
        border: 1px solid #999999;
        background: solid #111111;

        width:20px;
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
                                            """.format(handelColor = "#444444")
    
    
    def __init__(self):
        super().__init__()
        self.setFont(QtGui.QFont("Consolas"))
        self.setStyleSheet("background-color: #333333; color: #ffffff; border: 0px;")
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        
        self.verticalScrollBar().setStyleSheet(self.xScrollStyle)
        
        
class cWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.InitUI()

    def InitUI(self):
        self.setStyleSheet("background-color:#555555;")

        xCentralWidget = QtWidgets.QWidget(self)
        self.setCentralWidget(xCentralWidget)
        self.xMainLayout = QtWidgets.QGridLayout(xCentralWidget)

        self.xMainEditor = cCodeEditor()
        self.xMainLayout.addWidget(self.xMainEditor)
        
        self.xSyntaxHighlighter = cSyntaxHighlighter(self.xMainEditor.document())



        self.show()







    def keyPressEvent(self, xEvent):
        if xEvent.key() == QtCore.Qt.Key_Escape:
            self.close()





if __name__ == '__main__':
    xApp = QtWidgets.QApplication(sys.argv)
    xWindow = cWindow()
    
    sys.exit(xApp.exec())
