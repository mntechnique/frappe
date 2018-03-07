
import frappe

def execute():
	# Update Social Logins in User
	run_patch()

	# Create Social Login Key(s) from Social Login Keys
	frappe.reload_doc("integrations", "doctype", "social_login_key", force=True)

	if not frappe.db.exists('DocType', 'Social Login Keys'):
		return

	social_login_keys = frappe.get_doc("Social Login Keys", "Social Login Keys")
	if social_login_keys.get("facebook_client_id") or social_login_keys.get("facebook_client_secret"):
		facebook_login_key = frappe.new_doc("Social Login Key")
		facebook_login_key.get_social_login_provider("Facebook", initialize=True)
		facebook_login_key.social_login_provider = "Facebook"
		facebook_login_key.client_id = social_login_keys.get("facebook_client_id")
		facebook_login_key.client_secret = social_login_keys.get("facebook_client_secret")
		if not (facebook_login_key.client_secret and facebook_login_key.client_id):
			facebook_login_key.enable_social_login = 0
		facebook_login_key.save()

	if social_login_keys.get("frappe_server_url"):
		frappe_login_key = frappe.new_doc("Social Login Key")
		frappe_login_key.get_social_login_provider("Frappe", initialize=True)
		frappe_login_key.social_login_provider = "Frappe"
		frappe_login_key.base_url = social_login_keys.get("frappe_server_url")
		frappe_login_key.client_id = social_login_keys.get("frappe_client_id")
		frappe_login_key.client_secret = social_login_keys.get("frappe_client_secret")
		if not (frappe_login_key.client_secret and frappe_login_key.client_id and frappe_login_key.base_url):
			frappe_login_key.enable_social_login = 0
		frappe_login_key.save()

	if social_login_keys.get("github_client_id") or social_login_keys.get("github_client_secret"):
		github_login_key = frappe.new_doc("Social Login Key")
		github_login_key.get_social_login_provider("GitHub", initialize=True)
		github_login_key.social_login_provider = "GitHub"
		github_login_key.client_id = social_login_keys.get("github_client_id")
		github_login_key.client_secret = social_login_keys.get("github_client_secret")
		if not (github_login_key.client_secret and github_login_key.client_id):
			github_login_key.enable_social_login = 0
		github_login_key.save()

	if social_login_keys.get("google_client_id") or social_login_keys.get("google_client_secret"):
		google_login_key = frappe.new_doc("Social Login Key")
		google_login_key.get_social_login_provider("Google", initialize=True)
		google_login_key.social_login_provider = "Google"
		google_login_key.client_id = social_login_keys.get("google_client_id")
		google_login_key.client_secret = social_login_keys.get("google_client_secret")
		if not (google_login_key.client_secret and google_login_key.client_id):
			google_login_key.enable_social_login = 0
		google_login_key.save()

	frappe.delete_doc("DocType", "Social Login Keys")

def run_patch():
	frappe.reload_doc("core", "doctype", "user", force=True)
	frappe.reload_doc("core", "doctype", "user_social_login", force=True)

	users = frappe.get_all("User", 
		fields=["name", "frappe_userid", "fb_userid", "fb_username", "github_userid", "github_username", "google_userid"], 
		filters={"name":("not in", ["Administrator", "Guest"])})

	idx = 0
	for user in users:
		if user.get("frappe_userid"):
			insert_user_social_login(user.name, user.modified_by, 'frappe', idx, user.get("frappe_userid"))
			idx += 1

		if user.get("fb_userid") or user.get("fb_username"):
			insert_user_social_login(user.name, 'facebook', user.get("fb_userid"), idx, user.get("fb_username"))
			idx += 1

		if user.get("github_userid") or user.get("github_username"):
			insert_user_social_login(user.name, 'github', user.get("github_userid"), idx, user.get("github_username"))
			idx += 1

		if user.get("google_userid"):
			insert_user_social_login(user.name, 'google', idx, user.get("google_userid"))
			idx += 1


def insert_user_social_login(user, modified_by, provider, idx, userid=None, username=None):
	source_cols = get_standard_cols() + get_provider_fields(provider)

	creation_time = frappe.utils.get_datetime_str(frappe.utils.get_datetime())
	values = [
		frappe.generate_hash(length=10),
		creation_time,
		creation_time,
		user,
		modified_by,
		user,
		"User",
		"social_logins",
		idx,
		provider
	]

	if userid:
		values.append("'{0}'".format(userid))

	if username:
		values.append("'{0}'".format(username))
	
	
	query = """INSERT INTO `tabUser Social Login` ({source_cols}) 
		VALUES ({values})
	""".format(
		source_cols = ", ".join(source_cols),
		values=", ".join(values),
	)

	print(query)


def get_provider_field_map():
	return frappe._dict({
		"frappe": ["frappe_userid"],
		"facebook": ["fb_userid", "fb_username"],
		"github": ["github_userid", "github_username"],
		"google": ["google_userid"],
	})

def get_provider_fields(provider):
		return get_provider_field_map().get(provider)

def get_standard_cols():
	return ["name", "creation", "modified", "owner", "modified_by", "parent", "parenttype", "parentfield", "idx", "provider"]
