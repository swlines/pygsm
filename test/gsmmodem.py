#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import unittest
import pygsm

from mock.device import MockDevice


class TestIncomingMessage(unittest.TestCase):
    def testEchoOff(self):
        """Checks that GsmModem disables echo at some point
           during boot, to simplify logging and processing."""
        
        class MockEchoDevice(MockDevice):
            def process(self, cmd):
                if cmd == "ATE0":
                    self.echo = False
                    return True
        
        device = MockEchoDevice()
        gsm = pygsm.GsmModem(device=device)
        self.assetEqual(device.echo, False)
    
    
    def testUsefulErrors(self):
        """Checks that GsmModem attempts to enable useful errors
           during boot, to make the errors raised useful to humans.
           Many modems don't support this, but it's very useful."""
        
        class MockUsefulErrorsDevice(MockDevice):
            def __init__(self):
                MockDevice.__init__(self)
                self.useful_errors = False
            
            def process(self, cmd):
                if cmd == "AT+CMEE=1":
                    self.useful_errors = True
                    return True
        
        device = MockUsefulErrorsDevice()
        gsm = pygsm.GsmModem(device=device)
        self.assetEqual(device.useful_errors, True)


if __name__ == "__main__":
    unittest.main()