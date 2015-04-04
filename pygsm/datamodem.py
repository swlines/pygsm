#!/usr/bin/env python

from gsmmodem import GsmModem
import errors
import re

class DataModem(GsmModem):

	def __init__(self, *args, **kwargs):
		super(DataModem, self).__init__(*args, **kwargs)

		self.gprs_up = False
		self.apn_up = False
		self.internet_up = False

		self.apn = None
		self.apn_username = ""
		self.apn_password = ""

	def define_apn(self, apn, username, password):
		self.apn = apn
		self.apn_username = username
		self.apn_password = password

	def boot(self, reboot=False):
		super(DataModem, self).boot(reboot)

		while(True):
			# keep attempting this command as it doesn't work instantly on boot
			try:
				self.command("AT+CGATT=1")
				break
			except:
				pass

		self.command("AT+CSNS=4")

		return self

	def _disconnect(self):
		"""
		Disconnects from the existing CIP session
		"""
		self.command("AT+CIPSHUT", expected="SHUT OK", raise_errors=False, read_timeout=10)

	def _attach(self):
		"""
		Attach to the GPRS APN
		"""
		if not self.apn:
			raise errors.InvalidData

		# this will throw an error if the APN is already set
		try:
			self.command('AT+CSTT="%s","%s","%s"' % (self.apn, self.apn_username, self.apn_password))
		except:
			pass


		while(True):
			successful_connection = False

			self.wait_for_network()
			try:
				self.command('AT+CIICR')

			except errors.GsmError, err:
				self._disconnect()
				return self._connectivity_check()

			if self._connectivity_check():
				return True

	def _reconnect_gprs(self):
		"""
		Disconnects the GPRS PDP context entirely and reconnects
		"""
		self.command('AT+CGATT=0', raise_errors=False)

		try:
			self.command('AT+CGATT=1')
			self._attach()
		except:
			return False

	def _connectivity_check(self):
		self.wait_for_network()

		m = self.query('AT+CGATT?', '+CGATT: ')
		if m == '0':
			self._reconnect_gprs(self)

		self._write('AT+CIFSR\r')

		while(True):
			buf = self._read().strip()

			if buf == "ERROR":
				return False

			m = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", buf)
			if m:
				return True

			m = re.match(r"^\+(CM[ES]) ERROR: (\d+)$", buf)
			if m:
				type, code = m.groups()
				if code == '3':
					return self._attach()

				return False

		return False

	def _send(self, text):
		try:
			result = self.command('AT+CIPSEND', read_timeout=1)

		except errors.GsmReadTimeoutError, err:
			if err.pending_data[0] == ">":
				self.command(text, write_term=chr(26), expected='SEND OK')
				return True

			else:
				return False

	def _connect_gprs(self, destination, port, type, reattempt=True):
		#wait for the network
		self.wait_for_network()

		try:
			self.command('AT+CIPSTART="%s","%s","%s"' % (type, destination, port))
		except:
			pass 

		ip_status = False

		while(True):
			try:
				buf = self._read(read_timeout=15).strip()

			except errors.GsmReadTimeoutError:
				self._reconnect_gprs()
				return self._connect_gprs(destination, port, type, reattempt=False)

			# we are looking for the string CONNECT
			if 'CONNECT' in buf:

				if buf == 'CONNECT OK':
					return True

				if buf == 'CONNECT FAIL':
					if ip_status and reattempt:
						self._reconnect_gprs()
						return self._connect_gprs(destination, port, type, reattempt=False)

					else:
						return False

				if buf == 'ALREADY CONNECT':
					return False

			if buf == '+PDP: DEACT':
				return False

			if buf == 'STATE: IP STATUS':
				ip_status = True	

	def _close_gprs(self):
		self.command('AT+CIPSHUT', expected="SHUT OK", raise_errors=False)		


	def send_udp(self, destination, port, text):
		"""
		Sends a message over UDP to the given server
		"""
		#check connectivity and connect to the server
		if not self._connectivity_check() or not self._connect_gprs(destination, port, 'UDP'):
			return False

		res = self._send(text)
		if res:
			self._close_gprs()
			return True

		return False
			


		


