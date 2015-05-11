#!/usr/bin/env python

#
# Project Peregrine
#
#
# Copyright 2014 - 2015 Al Brown
#
# Wildlife tracking and mapping
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


import json

from PySide import QtGui, QtWebKit, QtCore, QtNetwork

from falconer import server, ui
from matplotlib import cm


RETRY_TIME = 2000
RETRIES = 5


class WidgetMap(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        self._signal = SignalMap()

        url = 'http://localhost:{}/map.html'.format(server.PORT)
        self._url = QtCore.QUrl(url)
        self._retries = RETRIES

        self._webMap = QtWebKit.QWebView()
        self._webMap.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        page = self._webMap.page()
        manager = page.networkAccessManager()
        manager.finished[QtNetwork.QNetworkReply].connect(self.__loaded)

        settings = page.settings()
        settings.setAttribute(QtWebKit.QWebSettings.DeveloperExtrasEnabled,
                              True)

        self._inspector = QtWebKit.QWebInspector(self)
        self._inspector.setPage(page)
        self._inspector.setVisible(False)
        shortcut = QtGui.QShortcut(self)
        shortcut.setKey(QtGui.QKeySequence(QtCore.Qt.Key_F12))
        shortcut.activated.connect(self.__on_inspector)

        frame = self._webMap.page().mainFrame()
        frame.setScrollBarPolicy(QtCore.Qt.Orientation.Horizontal,
                                 QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        frame.setScrollBarPolicy(QtCore.Qt.Orientation.Vertical,
                                 QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._controls = WidgetMapControls(self, self._webMap)

        splitter = QtGui.QSplitter(self)
        splitter.setOrientation(QtCore.Qt.Vertical)
        splitter.addWidget(self._webMap)
        splitter.addWidget(self._inspector)

        layoutV = QtGui.QVBoxLayout()
        layoutV.addWidget(splitter)
        layoutV.addWidget(self._controls)

        self.setLayout(layoutV)

        self._webMap.load(self._url)

    @QtCore.Slot(QtNetwork.QNetworkReply)
    def __loaded(self, reply):
        if reply.error() != QtNetwork.QNetworkReply.NoError:
            if self._retries:
                self._retries -= 1
                QtCore.QTimer.singleShot(RETRY_TIME, self.__on_retry)
            else:
                self._webMap.setHtml('Could not load map')

    @QtCore.Slot()
    def __on_inspector(self):
        self._inspector.setVisible(not self._inspector.isVisible())

    @QtCore.Slot()
    def __on_retry(self):
        self._webMap.load(self._url)

    @QtCore.Slot()
    def on_interaction(self,):
        self._controls.cancel_track()

    @QtCore.Slot(str)
    def on_layer_names(self, layers):
        self._controls.update_layers(json.loads(layers))

    @QtCore.Slot(str)
    def on_map_loaded(self):
        self._signal.loaded.emit()

    @QtCore.Slot()
    def on_colour(self):
        self._signal.colour.emit()

    def connect(self, loaded, colour):
        self._signal.loaded.connect(loaded)
        self._signal.colour.connect(colour)

    def set_settings(self, settings):
        self._controls.set_settings(settings)

    def transform_coords(self, xyz):
        return self._controls.transform_coords(xyz)

    def set_locations(self, locations):
        self.clear()
        self._controls.set_locations(locations)

    def update_heatmap(self, bounds):
        self._controls.update_heatmap(bounds)

    def clear(self):
        self._controls.clear()


class WidgetMapControls(QtGui.QWidget):
    def __init__(self, parent, webMap):
        QtGui.QWidget.__init__(self, parent)

        self._webMap = webMap

        self._settings = None
        self._follow = True

        self._signal = SignalMap()
        self._signal.colour.connect(parent.on_colour)

        ui.loadUi(self, 'map_controls.ui')

        self._comboLayers.addItem('Waiting...')
        colours = [colour for colour in cm.cmap_d]
        colours.sort()
        self._comboColour.addItems(colours)

        frame = self._webMap.page().mainFrame()
        self._mapLink = MapLink(frame)
        self._mapLink.connect(parent.on_interaction,
                              parent.on_layer_names,
                              parent.on_map_loaded,
                              parent.on_colour)
        frame.addToJavaScriptWindowObject('mapLink', self._mapLink)

    @QtCore.Slot(int)
    def on__comboLayers_activated(self, index):
        self._mapLink.set_layer(index)

    @QtCore.Slot(bool)
    def on__checkFollow_clicked(self, checked):
        self._follow = checked
        self.__follow()

    @QtCore.Slot(bool)
    def on__checkLocations_clicked(self, checked):
        self._mapLink.show_locations(checked)
        self.__follow()

    @QtCore.Slot(bool)
    def on__checkHeatmap_clicked(self, checked):
        self._mapLink.show_heatmap(checked)

    @QtCore.Slot(int)
    def on__sliderOpacity_valueChanged(self, opacity):
        self._mapLink.set_opacity(opacity)

    @QtCore.Slot(int)
    def on__comboColour_activated(self, index):
        colours = [colour for colour in cm.cmap_d]
        colours.sort()
        colour = colours[index]
        self._settings.heatmapColour = colour

        self._signal.colour.emit()

    def __follow(self):
        if self._follow:
            self._mapLink.follow()

    def set_settings(self, settings):
        self._settings = settings
        colours = [colour for colour in cm.cmap_d]
        colours.sort()
        index = colours.index(settings.heatmapColour)
        self._comboColour.setCurrentIndex(index)

    def update_layers(self, names):
        self._comboLayers.clear()
        self._comboLayers.addItems(names)

        layer = self._mapLink.get_layer()
        self._comboLayers.setCurrentIndex(layer)

        self.setEnabled(True)

    def cancel_track(self):
        self._follow = False
        self._checkFollow.setChecked(self._follow)

    def set_locations(self, locations):
        self._mapLink.set_locations(locations)
        self.__follow()

    def transform_coords(self, xyz):
        return self._mapLink.transform_coords(xyz)

    def update_heatmap(self, bounds):
        self._mapLink.update_heatmap(bounds)

    def clear(self):
        self._follow = True
        self._checkFollow.setChecked(self._follow)
        self._mapLink.clear()


class MapLink(QtCore.QObject):
    def __init__(self, frame):
        QtCore.QObject.__init__(self)
        self._frame = frame

        self._signal = SignalMap()

    def __exec_js(self, js):
        return self._frame.evaluateJavaScript(js)

    @QtCore.Slot()
    def on_interaction(self):
        self._signal.interaction.emit()

    @QtCore.Slot(str)
    def on_layer_names(self, names):
        self._signal.layers.emit(names)
        self._signal.loaded.emit()

    def connect(self, interaction, layer, loaded, colour):
        self._signal.interaction.connect(interaction)
        self._signal.layers.connect(layer)
        self._signal.loaded.connect(loaded)
        self._signal.colour.connect(colour)

    def transform_coords(self, coords):
        transformed = []
        for coord in coords:
            js = 'transformCoord({}, {});'.format(coord[0], coord[1])
            trans = self.__exec_js(js)
            trans.extend([coord[2]])
            transformed.append(trans)

        return transformed

    def get_layer(self):
        js = 'getLayer();'
        return self.__exec_js(js)

    def set_layer(self, layer):
        js = 'setLayer({});'.format(layer)
        self.__exec_js(js)

    def set_locations(self, locations):
        for location in locations:
            js = 'addLocations({}, {});'.format(location[0], location[1])
            self.__exec_js(js)

    def update_heatmap(self, bounds):
        js = 'setHeatmap({}, {}, {}, {});'.format(*bounds)
        self.__exec_js(js)

    def show_locations(self, show):
        js = 'showLocations({});'.format('{}'.format(show).lower())
        self.__exec_js(js)

    def show_heatmap(self, show):
        js = 'showHeatmap({});'.format('{}'.format(show).lower())
        self.__exec_js(js)

    def set_opacity(self, opacity):
        js = 'setOpacity({});'.format(opacity / 100.)
        self.__exec_js(js)

    def follow(self):
        js = 'follow();'
        self.__exec_js(js)

    def clear(self):
        js = 'clear();'
        self.__exec_js(js)


class SignalMap(QtCore.QObject):
    interaction = QtCore.Signal()
    layers = QtCore.Signal(str)
    loaded = QtCore.Signal()
    colour = QtCore.Signal()


if __name__ == '__main__':
    print 'Please run falconer.py'
    exit(1)
