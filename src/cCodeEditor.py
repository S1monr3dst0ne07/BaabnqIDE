from PyQt5 import QtCore, QtGui, QtWidgets

import re
import sys
import ctypes
import time
import shlex
import logging

from cUtils import *





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
            self.xModel = None
            QtWidgets.QCompleter.__init__(self)

        def splitPath(self, xPath):
            return xPath.split(" ")

        def pathFromIndex(self, xIndex):
            return self.model().data(xIndex, QtCore.Qt.DisplayRole)

        def SetCompleterModel(self, xNewModel):
            self.xModel = xNewModel
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
                
                ('put|print|input|putchr|asm|use',          xStyles["normalCommands"]),
                ('pull|push|sub|return',                    xStyles["stackCommands"]),
                ('=|\<|\>|==|!=|\+|-|&|\||\^|\>\>|\<\<|~',  xStyles["ops"]),
                ('->|<-|new|free|static',                   xStyles["memAlloc"]),
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


    
    xBaseCommands = ["put", "print", "input", "putchr", "asm", "use", "pull", "push", "sub", "return", "new", "free", "lab", "jump", "static"]
    

    def __init__(self, xParent):
        super().__init__()
        self.xFilePath = ""
        self.xIsSaved = True #keep track of if the file in this editor instance is saved to it's source
        self.xRestoreIsSavedState = None #switch state for restoring saved state when doing weird stuff
        
        self.xSyntaxHighlighter = self.cSyntaxHighlighter(self.document())
        self.xCompleter         = self.cCompleter()
        self.xCompleter.setWidget(self)
        self.UpdateCompleterModel("")
        self.xCompleterStatus = False
        self.xCompleterStatusGlobal = False

        self.xCompleter.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.xCompleter.activated.connect(self.InsertCompletion)

        self.xFontFamily = xParent.xFontFamily
        self.xParent = xParent
        
        self.xSender = xParent.xSender
        self.xSender.UpdateEditors.connect(self.UpdateFromPath)
        self.textChanged.connect(self.Change)  
        self.xSender.UpdateCompleter.connect(self.UpdateCompleter)
        self.xSender.UpdateCompleterState.connect(self.SetCompleterStatus)
        self.xSender.UpdateCompleterGlobal.connect(self.UpdateCompleterGlobal)



        self.xLineNumberArea = self.cLineNumberArea(self)

        self.blockCountChanged.connect(self.UpdateLineNumberAreaWidth)
        self.updateRequest.connect(self.UpdateLineNumberArea)
        self.cursorPositionChanged.connect(self.HighlightCurrentLine)
        self.xParent.xSender.UpdateLinenumberDisplay.connect(self.xLineNumberArea.update)
        
        self.UpdateLineNumberAreaWidth(0)

        self.xBreakpoints = []

        
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
        logging.debug(f"Set Completer Status: {xNewStatus}".format())
        self.xCompleterStatus = xNewStatus    
    
    def UpdateCompleterGlobal(self, xNewStatus):
        logging.debug(f"Set Completer Global: {xNewStatus}".format())
        self.xCompleterStatusGlobal = xNewStatus  
    
    
    #load file from path and update content of editor
    def UpdateFromPath(self):
        logging.info("Updating to editor")
        logging.debug(f"Path: {self.xFilePath}".format())

        try:
            with open(self.xFilePath, "r") as xFileHandle:
                self.setPlainText(xFileHandle.read())
                self.xIsSaved = True
                logging.info("Update to editor complete")
                
                return True
                
        except FileNotFoundError:
            #if path was not found kill instance
            logging.error("Error while updating, probably FileNotFoundError")
            QtWidgets.QMessageBox.about(self, "File lost", f"Reference to file at {self.xFilePath} has been lost\nThis my be due to the deletion or renaming of that file".format())
            self.xSender.CloseTab4QWidget.emit(self)
            return False
            
    #write editor content back to path
    def Save(self):
        logging.info("Saving editor content")
        logging.debug(f"Path: {self.xFilePath}".format())
        
        try:
            with open(self.xFilePath, "w") as xFileHandle:
                xFileHandle.write(self.toPlainText())
                
            self.xIsSaved = True
            logging.info("Saving complete")
            
        except Exception as E:
            logging.error(f"Error while saving: {E}".format())
            QtWidgets.QMessageBox.about(self, E)
                
    
    def InitUI(self):
        self.setFont(QtGui.QFont(self.xFontFamily))
        self.setStyleSheet(cUtils.xStyleHandle["CodeEditor"])
        self.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

        #override the look of the scroll bar to match the overall theme (which btw is a pain in the ass)
        xHandleColor = cUtils.xStyleHandle["ScrollStyleHandelColor"]
        self.verticalScrollBar().setStyleSheet(  cUtils.xStyleHandle["ScrollStyle"].format(sizeMod = "width:20px;", handleColor = xHandleColor))
        self.horizontalScrollBar().setStyleSheet(cUtils.xStyleHandle["ScrollStyle"].format(sizeMod = "hight:20px;", handleColor = xHandleColor))


    #drag and drop events
    def dragEnterEvent(self, xEvent):
        self.xSender.RemoteDragEnterEvent.emit(xEvent)
        self.xRestoreIsSavedState = self.xIsSaved
        
    def dropEvent(self, xEvent):
        self.xSender.RemoteDropEvent.emit(xEvent)
        self.xIsSaved = self.xRestoreIsSavedState
        self.xSender.UpdateTabSaveColor.emit()

        #give empty qdropevent to super, otherwise the qplaintextedit gets confused
        xDummyMimeData = QtCore.QMimeData()
        xDummyMimeData.setText("")
        xDummyEvent = QtGui.QDropEvent(xEvent.posF(), xEvent.possibleActions(), xDummyMimeData, xEvent.mouseButtons(), xEvent.keyboardModifiers())
        super().dropEvent(xDummyEvent)

    def TextUnderCursor(self):
        xTextCursor = self.textCursor()
        xTextCursor.select(QtGui.QTextCursor.WordUnderCursor)
        return xTextCursor.selectedText()

    #trigger that's called when the editor content changes, need for updating status stuff and such
    def Change(self):        
        self.xIsSaved = False
        self.xSender.UpdateTabSaveColor.emit()
        self.xSender.UpdateCompleter.emit()

    #xCompletionPrefix is give to be excluded
    def UpdateCompleterModel(self, xCompletionPrefix):
        logging.info("Completer Model Updated")
        
        xDelims = (" ", ";", "\n")

        xNewModel = self.xBaseCommands + cUtils.ChopChopSplit(self.toPlainText(), xDelims)
        xNewModelFilter = [x for x in xNewModel \
                       if x not in (xCompletionPrefix, '')
                       
                       
                    ]
        
        xFinalModel = cUtils.RemoveDups(xNewModelFilter)
        self.xModel = xFinalModel
        logging.debug(f"Model Filtered: {xFinalModel}".format())
        self.xCompleter.SetCompleterModel(xFinalModel)


    def UpdateCompleter(self):
        
        #update completer
        xCompletionPrefix = self.TextUnderCursor()
        self.xCompleter.setCompletionPrefix(xCompletionPrefix)
        self.UpdateCompleterModel(xCompletionPrefix)


        xCursorRect = self.cursorRect()
        xCursorRect.setWidth(self.xCompleter.popup().sizeHintForColumn(0) + self.xCompleter.popup().verticalScrollBar().sizeHint().width())
        self.xCompleter.complete(xCursorRect)

        xMatchCount = self.xCompleter.completionCount()
        xVisible =  xCompletionPrefix != "" and         \
                    xMatchCount > 0 and                 \
                    self.xCompleterStatus and           \
                    self.xCompleterStatusGlobal and     \
                    xCompletionPrefix not in self.xBaseCommands

                
        #set visibility of pop-up
        self.xCompleter.popup().show() if xVisible else self.xCompleter.popup().hide()

    def keyPressEvent(self, xEvent):
        
        if xEvent.key() == QtCore.Qt.Key_Tab:
            if self.xCompleter.popup().isVisible():
                self.InsertCompletion(self.xCompleter.popup().currentIndex().data())
            
            else:
                self.insertPlainText(" " * 4)
                self.xSender.UpdateCompleter.emit()
        
        else:
            super().keyPressEvent(xEvent)
            self.xSender.UpdateCompleter.emit()


    def focusInEvent(self, xEvent):
        #self.xCompleter.setWidget(self)
        super().focusInEvent(xEvent)

    def focusOutEvent(self, xEvent):
        super().focusOutEvent(xEvent)
        #self.xCompleter.setWidget(QtWidgets.QWidget())



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

        xPainter.fillRect(xEvent.rect(), QtGui.QColor(cUtils.xStyleHandle["LineNumBG"]))
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
                
                if xBlockNumber in self.xBreakpoints:
                    xPainter.setPen(QtGui.QColor(cUtils.xStyleHandle["Breakpoint"]))
                    xPainter.drawLine(0, int(xTop), self.xLineNumberArea.width(), int(xTop))
                
                xPainter.setPen(QtGui.QColor(cUtils.xStyleHandle["LineNumFG"]))
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

            xLineColor = QtGui.QColor(cUtils.xStyleHandle["HighlighedLine"])

            xSelection.format.setBackground(xLineColor)
            xSelection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
            xSelection.cursor = self.textCursor()
            xSelection.cursor.clearSelection()
            xExtraSelections.append(xSelection)
        self.setExtraSelections(xExtraSelections)
