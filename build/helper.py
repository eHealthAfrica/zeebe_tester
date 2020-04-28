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

from collections import defaultdict
import enum
import json
from json.decoder import JSONDecodeError
import os
from os.path import split as Split
from os.path import splitext

import requests
from requests.exceptions import HTTPError

from logger import LOG
from zb import ZeebeConfig, ZeebeConnection


class Event(enum.Enum):
    CHANGE = 1
    DELETE = 2


class FileType(enum.Enum):
    JOB = 1
    PIPELINE = 2
    BPMN = 3
    JSCALL = 4
    RESTCALL = 5
    ZEEBE = 6
    ZEEBECOMPLETE = 7
    ZEEBEMESSAGE = 8
    ZEEBESPAWN = 9


LOG.debug([i.name for i in FileType])


class Helper(object):
    _asset_path = '/code/assets'
    _local_zb_url = 'zeebe:26500'
    _url = 'http://consumer:9013'
    _default_consumer_user = 'admin'
    _default_consumer_password = 'password'
    zeebe_connection = None

    def __init__(self):
        self._set_zb()
        self._set_consumer()

    def _set_consumer(self):
        consumer_url = os.environ.get('CONSUMER_URL')
        self.session = requests.Session()
        if consumer_url:
            LOG.info(f'Using external consumer @ {consumer_url}')
            self._url = consumer_url
            consumer_user = os.environ.get('CONSUMER_USER')
            self.session.auth = (
                consumer_user,
                os.environ.get('CONSUMER_PASSWORD')
            )
        else:
            LOG.info(f'Using default consumer @ {self._url}')
            self.session.auth = (
                self._default_consumer_user,
                self._default_consumer_password
            )

    def _set_zb(self):
        zeebe_url = os.environ.get('ZEEBE_ADDRESS')
        if zeebe_url:
            LOG.info(f'Using External ZB @ {zeebe_url}')
            zb_config = ZeebeConfig(
                url=zeebe_url,
                client_id=os.environ.get('ZEEBE_CLIENT_ID'),
                client_secret=os.environ.get('ZEEBE_CLIENT_SECRET'),
                audience=os.environ.get('ZEEBE_AUDIENCE'),
                token_url=os.environ.get('ZEEBE_AUTHORIZATION_SERVER_URL')
            )
        else:
            LOG.info(f'No External ZB configured, using local @ {self._local_zb_url}')
            zb_config = ZeebeConfig(url=self._local_zb_url)
        self.zeebe_connection = ZeebeConnection(zb_config)

    def request(self, method, url, **kwargs):
        full_url = f'{self._url}{url}'
        LOG.debug(f'new request of {method} to {full_url}')
        res = self.session.request(method, full_url, **kwargs)
        res.raise_for_status()
        return res

    def zb(self):
        return self.zeebe_connection

    def _characterize(self, path) -> tuple:  # _id, _file_type, ext
        _, ext = splitext(path)
        head, tail = Split(path)
        _id = tail.split(ext)[0]
        _type = head.split('/')[-1]
        try:
            _file_type = FileType[_type.upper()]
        except KeyError as ker:
            raise KeyError(f'no handler for type: {_type}') from ker
        return (_id, _file_type, ext)

    def sync(self):
        assets = defaultdict(list)
        for root, dirs, files in os.walk(self._asset_path):
            for _file in files:
                path = os.path.join(root, _file)
                try:
                    _id, _type, ext = self._characterize(path)
                    assets[_type.name].append(path)
                except KeyError:
                    pass
        # we do this in reverse order of dependence for when we implement checking
        # of dependencies
        for k in list(FileType)[::-1]:
            paths = assets[k.name]
            if paths:
                for path in paths:
                    self.dispatch_change(Event.CHANGE, path)

    def dispatch_change(self, change: Event, path):
        try:
            try:
                _id, _file_type, ext = self._characterize(path)
            except KeyError as ker:
                LOG.error(ker)
                return
            try:
                if change is Event.DELETE:
                    LOG.debug('caught delete')
                    _contents = None
                elif ext == '.json':
                    _contents = self._get_file_contents(path, True)
                else:
                    _contents = self._get_file_contents(path, False)
            except JSONDecodeError:
                LOG.error(f'Could not decode valid json from {path}')
                return
            self.handle_change(change, _file_type, _id, _contents)
        except Exception as err:
            LOG.critical(f'Unexpected Critical Error: {type(err)}: {err}')

    def _get_file_contents(self, path, is_json=True):
        with open(path, 'rb') as f:
            if is_json:
                return json.load(f)
            else:
                return f.read()

    def handle_change(self, change: Event, _file_type: FileType, _id, _contents):
        _resource = _file_type.name.lower()
        LOG.debug(f'helper handling {change} on {_resource}/{_id}')
        if change is Event.DELETE and _file_type is not FileType.BPMN:
            self._delete(_file_type, _id)
        elif change is Event.DELETE and _file_type is FileType.BPMN:
            LOG.info('We cannot _yet_ automatically delete BPMNs from the brokers')
        elif _file_type is FileType.BPMN:
            LOG.debug('Working on adding BPMN')
            self.add_bpmn(_id, _contents)
        else:
            self._update(_resource, _id, _contents)

    def add_bpmn(self, _id, contents):
        try:
            res = next(self.zeebe_connection.deploy_workflow(_id, contents))
            LOG.debug(res)
        except Exception as err:
            LOG.critical(err)

    def _delete(self, resource_type, _id):
        try:
            res = self.request('get', f'/{resource_type}/delete?id={_id}')
            res.raise_for_status()
            LOG.info(f'DELETED {resource_type}/{_id}')
        except HTTPError:
            LOG.error(f'Failed to DELETE {resource_type}/{_id}')

    def _add(self, resource_type, _id, contents):
        try:
            res = self.request('post', f'/{resource_type}/add', json=contents)
            res.raise_for_status()
            LOG.info(f'UPDATED {resource_type}/{_id}')
        except HTTPError as her:
            LOG.info(f'Failed to UPDATE {resource_type}/{_id} : {her}')

    def _update(self, resource_type, _id, contents):
        try:
            res = self.request('get', f'/{resource_type}/get?id={_id}')
            res.raise_for_status()
            current = res.json()
        except HTTPError:
            LOG.debug(f'{resource_type}/{_id} does not exist, adding')
            return self._add(resource_type, _id, contents)
        del current['modified']
        if json.dumps(contents, sort_keys=True) == json.dumps(current, sort_keys=True):
            LOG.debug('No changes made, not updating')
        else:
            return self._add(resource_type, _id, contents)
