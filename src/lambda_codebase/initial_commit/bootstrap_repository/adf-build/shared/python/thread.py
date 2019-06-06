# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


# pylint: skip-file

from threading import Thread


class PropagatingThread(Thread):
    def run(self):
        self.exc = None
        try:
            if hasattr(self, '_Thread__target'):
                self.ret = self._Thread__target(
                    *self._Thread__args,
                    **self._Thread__kwargs
                )
            else:
                self.ret = self._target(
                    *self._args,
                    **self._kwargs
                )
        except BaseException as e:
            self.exc = e

    def join(self):
        super(PropagatingThread, self).join()
        if self.exc:
            raise self.exc
        return self.ret
