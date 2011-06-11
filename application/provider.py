class Provider:
	"""Abstract provider class used to manipulate items"""

	is_local = True  # if provider handles local files
	protocols = ()  # list of supported protocols

	def __init__(self, parent, path=None, selection=None):
		self._parent = parent

		self._path = path
		self._selection = None
		
		# we need only existing items in selection list
		if selection is not None:
			self._selection = [item for item in selection if self.exists(item, path)]

	def is_file(self, path, relative_to=None):
		"""Test if given path is file"""
		pass

	def is_dir(self, path, relative_to=None):
		"""Test if given path is directory"""
		pass

	def is_link(self, path, relative_to=None):
		"""Test if given path is a link"""
		pass

	def exists(self, path, relative_to=None):
		"""Test if given path exists"""
		pass

	def unlink(self, path, relative_to=None):
		"""Unlink given path"""
		pass

	def remove_directory(self, path, recursive, relative_to=None):
		"""Remove directory and optionally its content"""
		pass

	def remove_file(self, path, relative_to=None):
		"""Remove file"""
		pass

	def create_file(self, path, mode=None, relative_to=None):
		"""Create empty file with specified mode set"""
		pass

	def create_directory(self, path, mode=None, relative_to=None):
		"""Create directory with specified mode set"""
		pass

	def get_file_handle(self, path, mode, relative_to=None):
		"""Open path in specified mode and return its handle"""
		pass

	def get_stat(self, path, relative_to=None):
		"""Return file statistics"""
		pass

	def get_selection(self, relative=False):
		"""Get list of selected items"""
		if self._selection is None:
			# get selection from parent
			result = self._parent._get_selection_list(relative=relative)

		else:
			# return predefined selection
			result = self._selection

		return result

	def get_path(self):
		"""Return parents path"""
		if self._path is None:
			# return parent path
			result = self._parent.path

		else:
			# return predefined path
			result = self._path

		return result

	def set_mode(self, path, mode, relative_to=None):
		"""Set access mode to specified path"""
		pass

	def set_owner(self, path, owner=-1, group=-1, relative_to=None):
		"""Set owner and/or group for specified path"""
		pass

	def remove_path(self, path, recursive=True, relative_to=None):
		"""Remove path"""
		if self.is_link(path, relative_to):  # handle links
			self.unlink(path, relative_to)

		elif self.is_dir(path, relative_to):  # handle directories
			self.remove_directory(path, recursive, relative_to)

		else:  # handle files
			self.remove_file(path, relative_to)

	def rename_path(self, source, destination, relative_to=None):
		"""Rename file/directory within parents path"""
		pass

	def list_dir(self, path, relative_to=None):
		"""Get directory list"""
		pass
	
	def get_parent(self):
		"""Return parent list"""
		return self._parent