import gtk


class AcceleratorManager:
	"""This manager handles saving and loading of accelerators"""

	def __init__(self, application):
		self._application = application
		self._config = None

		self._groups = []
		self._group_names = []

	def _save_accelerator(self, section, name, accelerator=None, primary=True, can_overwrite=False):
		"""Save accelerator to config file"""
		if not primary:
			name = '{0}_2'.format(name)

		label = ''
		if accelerator is not None:
			label = gtk.accelerator_name(*accelerator)

		# don't allow overwriting user's configuration unless strictly specified
		if not self._config.has_option(section, name) \
		or (self._config.has_option(section, name) and can_overwrite):
			self._config.set(section, name, label)

	def _load_accelerator(self, section, name, primary=True):
		"""Load accelerator from config file"""
		result = None

		if not primary:
			name = '{0}_2'.format(name)

		# try to load only if config has accelerator specified
		if self._config.has_section(section) \
		and self._config.has_option(section, name):
			result = gtk.accelerator_parse(self._config.get(section, name))

		return result

	def _get_group_by_name(self, name):
		"""Get accelerator group based on it's name"""
		result = None

		for group in self._groups:
			if group._name == name:
				result = group
				break

		return result

	def register_group(self, group):
		"""Register group with manager"""
		if not self._config.has_section(group._name):
			self._config.add_section(group._name)

		# add group name to the list
		if group._name not in self._group_names:
			self._group_names.append(group._name)
		
		# add group to internal list
		self._groups.append(group)

		# add all the methods to config file
		for name in group._methods:
			# save primary accelerator
			if group._primary.has_key(name):
				self._save_accelerator(group._name, name, group._primary[name])

			else:
				self._save_accelerator(group._name, name)

			# save secondary accelerator
			if group._secondary.has_key(name):
				self._save_accelerator(group._name, name, group._secondary[name], primary=False)

	def get_groups(self):
		"""Get list of unique group names"""
		return self._group_names

	def get_group_title(self, name):
		"""Get title for specified group name"""
		result = ''

		# try to get group based on name
		group = self._get_group_by_name(name)

		if group is not None:
			result = group._title

		return result

	def get_methods(self, name):
		"""Get list of methods for a specific group"""
		methods = []

		# try to get group based on name
		group = self._get_group_by_name(name)

		if group is not None:
			methods = group._methods

		return methods

	def get_group_data(self, name):
		"""Convenience method that returns title and methods in one pass"""
		title = ''
		methods = []

		# try to get group based on name
		group = self._get_group_by_name(name)

		if group is not None:
			title = group._title
			methods = group._methods

		return title, methods

	def get_accelerator(self, group, name, primary=True):
		"""Get saved accelerator"""
		accelerator = self._load_accelerator(group, name, primary)

		# no user defined accelerator, get default
		if accelerator is None:
			group = self._get_group_by_name(group)

			if group is not None:
				accelerator = group.get_accelerator(name, primary)
				
		return accelerator

	def load(self, config):
		"""Load accelerator map"""
		self._config = config

	def save(self):
		"""Save accelerator map"""
		pass
