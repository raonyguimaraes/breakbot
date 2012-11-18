#!/usr/bin/python
# Copyright 2012 Bruno Gonzalez
# This software is released under the GNU AFFERO GENERAL PUBLIC LICENSE (see agpl-3.0.txt or www.gnu.org/licenses/agpl-3.0.html)
import threading
from message import Message
from timestamp import Timestamp

from Yowsup.Tools.utilities import Utilities
from Yowsup.connectionmanager import YowsupConnectionManager
import time
from log import info, error

class WAInterface(threading.Thread):
    def __init__(self, username, identity, msg_handler, stopped_handler):
        threading.Thread.__init__(self)
        self.connected = False
        self.must_run = True
        self.msg_handler = msg_handler
        self.stopped_handler = stopped_handler
        self.username = username
        self.identity = identity
        self.cm = YowsupConnectionManager()
        self.cm.setAutoPong(True)
        self.signalsInterface = self.cm.getSignalsInterface()
        self.methodsInterface = self.cm.getMethodsInterface()
        self.signalsInterface.registerListener("message_received", self.onMessageReceived)
        self.signalsInterface.registerListener("group_messageReceived", self.onGroup_MessageReceived)
        self.signalsInterface.registerListener("auth_success", self.onAuthSuccess)
        self.signalsInterface.registerListener("auth_fail", self.onAuthFailed)
        self.signalsInterface.registerListener("disconnected", self.onDisconnected)
        self.signalsInterface.registerListener("receipt_messageSent", self.onMessageSent)
        self.signalsInterface.registerListener("receipt_messageDelivered", self.onMessageDelivered)
        self.signalsInterface.registerListener("ping", self.onPing)
    def onMessageReceived(self, messageId, jid, messageContent, timestamp, wantsReceipt, pushName):
        try:
            messageContent = unicode(messageContent, "utf-8")
            message = Message(kind="wa", nick_full=jid, chan=self.username, msg=messageContent)
            message.time = Timestamp(ms_int = timestamp*1000)
            self.msg_handler(message)
            sendReceipts = True
            if wantsReceipt and sendReceipts:
                self.wait_connected()
                self.methodsInterface.call("message_ack", (jid, messageId))
        except:
            error("Error while handling message")
    def onGroup_MessageReceived(self, messageId, jid, author, messageContent, timestamp, wantsReceipt, pushName):
        try:
            messageContent = unicode(messageContent, "utf-8")
            message = Message(kind="wa", nick_full=author, chan=jid, msg=messageContent)
            message.time = Timestamp(ms_int = timestamp*1000)
            self.msg_handler(message)
            sendReceipts = True
            if wantsReceipt and sendReceipts:
                self.wait_connected()
                self.methodsInterface.call("message_ack", (jid, messageId))
        except:
            error("Error while handling message")

    def run(self):
        try:
            info("Connecting as %s" %self.username)
            self.must_run = True
            self.methodsInterface.call("auth_login", (self.username, Utilities.getPassword(self.identity)))
            self.wait_connected()
            info("Connected as %s" %self.username)
            while self.must_run:
                if not self.connected:
                    self.methodsInterface.call("auth_login", (self.username, Utilities.getPassword(self.identity)))
                time.sleep(0.5)
                #raw_input()
        except:
            error("Main loop stopping")
        info("Main loop closing")
        self.connected = False
        self.stopped_handler()
        self.must_run = False
    def stop(self):
        self.must_run = False
    def send(self, target, text):
        self.wait_connected()
        self.methodsInterface.call("message_send", (target, text.encode("utf-8")))
        info((" >>> Sent WA message: %s: %s" %(target, text)).encode("utf-8"))
    def onAuthSuccess(self, username):
        info("Authed %s" % username)
        self.connected = True
        self.methodsInterface.call("ready")
    def onAuthFailed(self, username, err):
        info("Auth Failed!")
    def onDisconnected(self, reason):
        info("Disconnected because %s" %reason)
        self.connected = False
    def onMessageSent(self, jid, messageId):
        info("Message successfully sent to %s" % jid)
    def onMessageDelivered(self, jid, messageId):
        info("Message successfully delivered to %s" %jid)
        self.wait_connected()
        self.methodsInterface.call("delivered_ack", (jid, messageId))
    def onPing(self, pingId):
        info("Pong! (%s)" %pingId)
        self.wait_connected()
        self.methodsInterface.call("pong", (pingId,))
    def wait_connected(self):
        while not self.connected:
            if not self.must_run:
                raise Exception("bot does not intend to connect")
            time.sleep(0.1)
