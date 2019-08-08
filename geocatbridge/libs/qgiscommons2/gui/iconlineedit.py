# -*- coding: utf-8 -*-

"""
***************************************************************************
    iconlineedit.py
    ---------------------
    Date                 : August 2016
    Copyright            : (C) 2016 Boundless, http://boundlessgeo.com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Alexander Bruy'
__date__ = 'August 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtWidgets import QLineEdit, QToolButton, QStyle


class IconLineEdit(QLineEdit):
    def __init__(self, parent=None):
        QLineEdit.__init__(self, parent)

        self.btnIcon = QToolButton(self)
        self.btnIcon.setEnabled(False)
        self.btnIcon.setStyleSheet("QToolButton { border: none; padding: 0px; }")

        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        self.setStyleSheet("QLineEdit {{ padding-left: {}px; }} ".format(self.btnIcon.sizeHint().width() + frameWidth + 1))
        msz = self.minimumSizeHint()
        self.setMinimumSize(max(msz.width(), self.btnIcon.sizeHint().height() + frameWidth * 2 + 2),
                            max(msz.height(), self.btnIcon.sizeHint().height() + frameWidth * 2 + 2))

    def resizeEvent(self, event):
        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)

        sz = self.btnIcon.sizeHint()
        self.btnIcon.move(frameWidth + 1,
                           (self.rect().bottom() + 1 - sz.height()) / 2)

    def setIcon(self, icon):
        self.btnIcon.setIcon(icon)
