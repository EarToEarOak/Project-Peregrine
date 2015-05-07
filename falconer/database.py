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

import sqlite3

from common.database import create_database, name_factory


class Database():
    def __init__(self):
        self._conn = None

    def __connect(self, fileName):
        self._conn = sqlite3.connect(fileName)
        self._conn.row_factory = name_factory

        create_database(self._conn)

    def open(self, fileName):
        self.__connect(fileName)

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def isConnected(self):
        if self._conn is None:
            return False

        return True

    def get_scans(self):
        cursor = self._conn.cursor()
        cmd = 'select * from Scans'
        cursor.execute(cmd)
        rows = cursor.fetchall()
        scans = [[row['TimeStamp'], row['Freq']] for row in rows]

        return scans

    def get_signals(self, filtered):
        cond = ' '

        if len(filtered):
            cond = ' where TimeStamp not in ('
            cond += str(filtered).strip('[]')
            cond += ')'

        cmd = 'select Freq, count(Freq) from Signals'
        cmd += cond
        cmd += 'group by Freq'

        cursor = self._conn.cursor()
        cursor.execute(cmd)
        rows = cursor.fetchall()
        signals = [[row['Freq'], row['count(Freq)']] for row in rows]

        return signals


if __name__ == '__main__':
    print 'Please run falconer.py'
    exit(1)
