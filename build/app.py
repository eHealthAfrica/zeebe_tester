#!/usr/bin/env python

# Copyright (C) 2020 by eHealth Africa : http://www.eHealthAfrica.org
#
# See the NOTICE file distributed with this work for additional information
# regarding copyright ownership.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import time

from requests.exceptions import HTTPError
from watchdog.observers import Observer

from handler import ChangeHandler
from helper import Helper
from logger import LOG
from zb import ZeebeError


HELPER = Helper()
HANDLER = ChangeHandler(HELPER)


def test_consumer_connection() -> bool:
    try:
        HELPER.request('HEAD', '/job/describe')
        return True
    except HTTPError as her:
        LOG.error(f'Could not connect to consumer: {her}')
        return False


def test_zb_connection() -> bool:
    zeebe_connection = HELPER.zb()
    try:
        res = next(zeebe_connection.get_topology())
        LOG.debug(f'connected to {res.brokers}')
        return True
    except ZeebeError as zer:
        LOG.error(f'Could not connect to ZB: {zer}')
        return False


def test_connections():
    return test_zb_connection() and test_consumer_connection()


def monitor():
    observer = Observer()
    observer.schedule(HANDLER, '/code/assets', recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def update():
    HELPER.sync()


if __name__ == '__main__':
    test_connections()
    update()
    monitor()
