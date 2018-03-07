# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.model.document import Document
import requests

class ExotelSettings(Document):
	def validate(self):
		def validate_credentials(self):
			response = requests.get('https://api.exotel.com/v1/Accounts/{sid}'.format(sid = self.exotel_sid),
				auth=(self.exotel_sid, self.exotel_token))
			if response.status_code not 200:
				frappe.throw(_("Invalid credentials. Please try again with valid credentials"))


@frappe.whitelist(allow_guest=True)
def handle_incoming_call(*args, **kwargs):
	""" Handles incoming calls in telephony service. """
	try:
		if args or kwargs:
			content = args or kwargs

			comm = frappe.new_doc("Communication")
			comm.subject = "Incoming Call " + frappe.utils.get_datetime_str(frappe.utils.get_datetime())
			comm.send_email = 0
			comm.communication_medium = "Phone"
			comm.phone_no = content.get("CallFrom")
			comm.comment_type = "Info"
			comm.communication_type = "Communication"
			comm.status = "Open"
			comm.sent_or_received = "Received"
			comm.content = "Incoming Call " + frappe.utils.get_datetime_str(frappe.utils.get_datetime()) + "<br>" + str(content)
			comm.communication_date = content.get("StartTime")
			comm.sid = content.get("CallSid")
			comm.exophone = content.get("CallTo")

			comm.save(ignore_permissions=True)
			frappe.db.commit()

			return comm
	except Exception as e:
		frappe.log_error(message=e, title="Error log for incoming call")

@frappe.whitelist(allow_guest=True)
def capture_call_details(*args, **kwargs):
	""" Captures post-call details in telephony service. """

	try:
		if args or kwargs:
			credentials = frappe.get_doc("Exotel Settings")
<<<<<<< HEAD

=======
>>>>>>> e1c66b71a... Added validations in Exotel Settings and code refactor in post-call API
			content = args or kwargs

			response = requests.get('https://api.exotel.com/v1/Accounts/{sid}/Calls/{callsid}.json'.format(sid = credentials.exotel_sid,callsid = content.get("CallSid")),\
				auth=(credentials.exotel_sid,credentials.exotel_token))

			content = response.json()["Call"]

			if response.status_code == 200:
				call = frappe.get_all("Communication", filters={"sid":content.get("CallSid")}, fields=["name"])
				comm = frappe.get_doc("Communication",call[0].name)
				comm.recording_url = content.get("RecordingUrl")
				comm.save(ignore_permissions=True)
				frappe.db.commit()
				return comm
			else:
				frappe.msgprint(_("Authenication error. Invalid exotel credentials."))	
	except Exception as e:
		frappe.log_error(message=e, title="Error in capturing call details")

@frappe.whitelist()
def handle_outgoing_call(To, CallerId,reference_doctype,reference_name):
	"""Handles outgoing calls in telephony service.
	
	:param From: Number of user
	:param To: Number of customer
	:param CallerId: Exophone number
	:param reference_doctype: links reference doctype,if any
	:param reference_name: links reference docname,if any

	"""
	r = frappe.request
	try:
		credentials = frappe.get_doc("Exotel Settings")	

		response = requests.post('https://api.exotel.in/v1/Accounts/{sid}/Calls/connect.json'.format(sid=credentials.exotel_sid),
        auth = (credentials.exotel_sid,credentials.exotel_token),
		data = {
			'From': frappe.get_doc("User",frappe.session.user).phone or frappe.get_doc("User",frappe.session.user).mobile_no,
			'To': To,
			'CallerId': CallerId,
			'StatusCallback': 'http://dev.mntechnique.com/api/method/frappe.integrations.doctype.exotel_settings.exotel_settings.capture_call_details'
		})

		if response.status_code == 200:
			content = response.json()["Call"]

			comm = frappe.new_doc("Communication")
			comm.subject = "Outgoing Call " + frappe.utils.get_datetime_str(frappe.utils.get_datetime())
			comm.send_email = 0
			comm.communication_medium = "Phone"
			comm.phone_no = content.get("To")
			comm.comment_type = "Info"
			comm.communication_type = "Communication"
			comm.status = "Open"
			comm.sent_or_received = "Sent"
			comm.content = "Outgoing Call " + frappe.utils.get_datetime_str(frappe.utils.get_datetime()) + "<br>" + str(content)
			comm.communication_date = content.get("StartTime")
			comm.recording_url = content.get("RecordingUrl")
			comm.sid = content.get("Sid")
			comm.reference_doctype = reference_doctype
			comm.reference_name = reference_name

			comm.save(ignore_permissions=True)
			frappe.db.commit()

			return comm
		else:
			frappe.msgprint(_("Authenication error. Invalid exotel credentials."))
	except Exception as e:
		frappe.log_error(message=e, title="Error log for outgoing call")