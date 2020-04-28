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

from watchdog.events import FileSystemEventHandler

from helper import Helper, Event
from logger import LOG


class ChangeHandler(FileSystemEventHandler):
    """Logs all the events captured."""

    helper = None

    def __init__(self, helper: Helper, *args, **kwargs):
        self.helper = helper
        super().__init__(*args, **kwargs)

    def on_moved(self, event):
        super(ChangeHandler, self).on_moved(event)
        if event.is_directory:
            return
        LOG.info("Moved %s: from %s to %s", 'file', event.src_path,
                 event.dest_path)
        self.helper.dispatch_change(Event.CHANGE, event.dest_path)

    def on_created(self, event):
        super(ChangeHandler, self).on_created(event)
        if event.is_directory:
            return
        LOG.info("Created %s: %s", 'file', event.src_path)
        LOG.debug('Ignoring creation, will catch on change notifier')
        # self.helper.dispatch_change(Event.ADD, event.src_path)

    def on_deleted(self, event):
        super(ChangeHandler, self).on_deleted(event)
        if event.is_directory:
            return
        LOG.info("Deleted %s: %s", 'file', event.src_path)
        self.helper.dispatch_change(Event.DELETE, event.src_path)

    def on_modified(self, event):
        super(ChangeHandler, self).on_modified(event)
        if event.is_directory:
            return
        LOG.info("Modified %s: %s", 'file', event.src_path)
        self.helper.dispatch_change(Event.CHANGE, event.src_path)
