from PyQt5 import QtCore, QtGui, QtWidgets

class cSender(QtCore.QObject):
    UpdateEditors               = QtCore.pyqtSignal()
    CloseTab4QWidget            = QtCore.pyqtSignal(QtWidgets.QWidget)
    RemoteDragEnterEvent        = QtCore.pyqtSignal(QtGui.QDragEnterEvent)
    RemoteDropEvent             = QtCore.pyqtSignal(QtGui.QDropEvent)
    UpdateTabSaveColor          = QtCore.pyqtSignal()
    UpdateCompleterState        = QtCore.pyqtSignal(bool)
    UpdateCompleterGlobal       = QtCore.pyqtSignal(bool)
    UpdateCompleter             = QtCore.pyqtSignal()
    SetCompilerCall             = QtCore.pyqtSignal(str)
    SetVirtMachCall             = QtCore.pyqtSignal(str)
    MoveCurrentEditor           = QtCore.pyqtSignal(int)