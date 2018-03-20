# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.model.document import Document
from six.moves.urllib.parse import urlparse
import requests

class ExotelSettings(Document):
	def validate(self):
		self.validate_credentials()

	def validate_credentials(self):
		response = requests.get('https://api.exotel.com/v1/Accounts/{sid}'.format(sid = self.exotel_sid),
			auth=(self.exotel_sid, self.exotel_token))
		if(response.status_code != 200):
			frappe.throw(_("Invalid credentials. Please try again with valid credentials"))

def make_popup(caller_no):
	contact_lookup = frappe.db.get_list("Contact", or_filters={"phone":caller_no, "mobile_no":caller_no})

	popup_html = """<h4 class="text-muted">No data</h4>"""

	if len(contact_lookup) > 0:
		contact_doc = frappe.get_doc("Contact", contact_lookup[0].get("name"))
		if(contact_doc.get_link_for('Customer')):		
			customer_name = frappe.db.get_value("Dynamic Link", {"parent":contact_doc.get("name")}, "link_name")
			customer_full_name = frappe.db.get_value("Customer", customer_name, "customer_name")
			popup_html = render_popup("Customer", caller_no, customer_full_name)
			
		elif(contact_doc.get_link_for('Lead')):
			lead_full_name = frappe.get_doc("Lead",contact_doc.get_link_for('Lead')).lead_name
			popup_html = render_popup("Lead", caller_no, lead_full_name)

	else:
		popup_html = render_popup("Unknown Caller", caller_no, "Unknown")

	return popup_html

def render_popup(title, number, name):
	popup_data = {
		"title": title,
		"number": number,
		"name": name,
		"call_timestamp": frappe.utils.datetime.datetime.strftime(frappe.utils.datetime.datetime.today(), '%d/%m/%Y %H:%M:%S')
	}
	html = frappe.render_template("frappe/public/js/integrations/call_popup.html", popup_data)
	return html

def display_popup(caller_no):
	try:
		popup_html = make_popup(caller_no)
		users = frappe.get_all("Has Role", filters={"parenttype":"User","role":"Support Team"}, fields=["parent"])
		agents = [user.get("parent") for user in users]
		agents = list(set(agents))
		for agent in agents:
			frappe.async.publish_realtime(event="msgprint", message=popup_html, user=agent)	

	except Exception as e:
		frappe.log_error(message=frappe.get_traceback(), title="Error in popup display")

@frappe.whitelist(allow_guest=True)
def handle_incoming_call(*args, **kwargs):
	""" Handles incoming calls in telephony service. """
	try:
		if args or kwargs:
			content = args or kwargs
			if(frappe.get_doc("Telephony Settings").show_popup_for_incoming_calls):
				caller_no = content.get("CallFrom")

				contact_lookup = frappe.get_list("Contact", or_filters={"phone":caller_no, "mobile_no":caller_no})

				if len(contact_lookup) > 0:
					caller = contact_lookup[0].get("name")
					frappe.async.publish_realtime(event="msgprint", message=caller)
				else:
					caller = "Unknown"
					frappe.async.publish_realtime(event="msgprint", message=caller)
			
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
		frappe.log_error(message=frappe.get_traceback(), title="Error log for incoming call")

@frappe.whitelist(allow_guest=True)
def capture_call_details(*args, **kwargs):
	""" Captures post-call details in telephony service. """

	try:
		if args or kwargs:
			credentials = frappe.get_doc("Exotel Settings")
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
		frappe.log_error(message=frappe.get_traceback(), title="Error in capturing call details")

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
		
		endpoint = "/api/method/frappe.integrations.doctype.exotel_settings.exotel_settings.capture_call_details"
		url = frappe.request.url

		server_url = '{uri.scheme}://{uri.netloc}'.format(
			uri=urlparse(url)
		)
		status_callback_url = server_url + endpoint

		response = requests.post('https://api.exotel.in/v1/Accounts/{sid}/Calls/connect.json'.format(sid=credentials.exotel_sid),
        auth = (credentials.exotel_sid,credentials.exotel_token),
		data = {
			'From': frappe.get_doc("User",frappe.session.user).phone or frappe.get_doc("User",frappe.session.user).mobile_no,
			'To': To,
			'CallerId': CallerId,
			'StatusCallback': status_callback_url
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
		frappe.log_error(message=frappe.get_traceback(), title="Error log for outgoing call")


@frappe.whitelist(allow_guest=True)
def test_method(*args, **kwargs):
	contacts = []
	try:
		if args or kwargs:
			contacts = frappe.get_all("Contact", fields=["*"])
		else:
			return "No args or kwargs"
	except Exception as e:
		return e.message

	if len(contacts) > 0:
		return "Contacts have been found"
	else:
		return "Contacts have not been found"
