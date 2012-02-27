import os
import gtk
import time
import locale
import fnmatch
import user

from plugin_base.provider import FileType
from common import get_user_directory, UserDirectory

# constants
class OverwriteOption:
	RENAME = 0
	NEW_NAME = 1
	APPLY_TO_ALL = 2


class InputDialog:
	"""Simple input dialog

	This class can be extended with additional custom controls
	by accessing locally stored objects. Initially this dialog
	contains single label and text entry, along with two buttons.

	"""

	def __init__(self, application):
		self._dialog = gtk.Dialog(parent=application)

		self._application = application

		self._dialog.set_default_size(340, 10)
		self._dialog.set_resizable(True)
		self._dialog.set_skip_taskbar_hint(True)
		self._dialog.set_modal(True)
		self._dialog.set_transient_for(application)
		self._dialog.set_wmclass('Sunflower', 'Sunflower')

		self._dialog.vbox.set_spacing(0)

		self._container = gtk.VBox(False, 0)
		self._container.set_border_width(5)

		# create interface
		vbox = gtk.VBox(False, 0)
		self._label = gtk.Label('Label')
		self._label.set_alignment(0, 0.5)

		self._entry = gtk.Entry()
		self._entry.connect('activate', self._confirm_entry)

		button_ok = gtk.Button(stock=gtk.STOCK_OK)
		button_ok.connect('clicked', self._confirm_entry)
		button_ok.set_can_default(True)

		button_cancel = gtk.Button(stock=gtk.STOCK_CANCEL)

		# pack interface
		vbox.pack_start(self._label, False, False, 0)
		vbox.pack_start(self._entry, False, False, 0)

		self._container.pack_start(vbox, False, False, 0)

		self._dialog.add_action_widget(button_cancel, gtk.RESPONSE_CANCEL)
		self._dialog.action_area.pack_end(button_ok, False, False, 0)
		self._dialog.set_default_response(gtk.RESPONSE_OK)

		self._dialog.vbox.pack_start(self._container, True, True, 0)
		self._dialog.show_all()

	def _confirm_entry(self, widget, data=None):
		"""Enable user to confirm by pressing Enter"""
		if self._entry.get_text() != '':
			self._dialog.response(gtk.RESPONSE_OK)

	def set_title(self, title_text):
		"""Set dialog title"""
		self._dialog.set_title(title_text)

	def set_label(self, label_text):
		"""Provide an easy way to set label text"""
		self._label.set_text(label_text)

	def set_text(self, entry_text):
		"""Set main entry text"""
		self._entry.set_text(entry_text)

	def get_response(self):
		"""Return value and self-destruct

		This method returns tuple with response code and
		input text.

		"""
		code = self._dialog.run()
		result = self._entry.get_text()

		self._dialog.destroy()

		return (code, result)


class CreateDialog(InputDialog):
	"""Generic create file/directory dialog"""

	def __init__(self, application):
		InputDialog.__init__(self, application)

		self._permission_updating = False
		self._mode = 0644
		self._dialog_size = None

		self._container.set_spacing(5)

		# create advanced options expander
		expander = gtk.Expander(_('Advanced options'))
		expander.connect('activate', self._expander_event)
		expander.set_border_width(0)

		self._advanced = gtk.VBox(False, 5)
		self._advanced.set_border_width(5)

		table = gtk.Table(4, 4, False)

		# create widgets
		label = gtk.Label(_('User:'))
		label.set_alignment(0, 0.5)
		table.attach(label, 0, 1, 0, 1)

		label = gtk.Label(_('Group:'))
		label.set_alignment(0, 0.5)
		table.attach(label, 0, 1, 1, 2)

		label = gtk.Label(_('Others:'))
		label.set_alignment(0, 0.5)
		table.attach(label, 0, 1, 2, 3)

		# owner checkboxes
		self._permission_owner_read = gtk.CheckButton(_('Read'))
		self._permission_owner_read.connect('toggled', self._update_octal, (1 << 2) * 100)
		table.attach(self._permission_owner_read, 1, 2, 0, 1)

		self._permission_owner_write = gtk.CheckButton(_('Write'))
		self._permission_owner_write.connect('toggled', self._update_octal, (1 << 1) * 100)
		table.attach(self._permission_owner_write, 2, 3, 0, 1)

		self._permission_owner_execute = gtk.CheckButton(_('Execute'))
		self._permission_owner_execute.connect('toggled', self._update_octal, (1 << 0) * 100)
		table.attach(self._permission_owner_execute, 3, 4, 0, 1)

		# group checkboxes
		self._permission_group_read = gtk.CheckButton(_('Read'))
		self._permission_group_read.connect('toggled', self._update_octal, (1 << 2) * 10)
		table.attach(self._permission_group_read, 1, 2, 1, 2)

		self._permission_group_write = gtk.CheckButton(_('Write'))
		self._permission_group_write.connect('toggled', self._update_octal, (1 << 1) * 10)
		table.attach(self._permission_group_write, 2, 3, 1, 2)

		self._permission_group_execute = gtk.CheckButton(_('Execute'))
		self._permission_group_execute.connect('toggled', self._update_octal, (1 << 0) * 10)
		table.attach(self._permission_group_execute, 3, 4, 1, 2)

		# others checkboxes
		self._permission_others_read = gtk.CheckButton(_('Read'))
		self._permission_others_read.connect('toggled', self._update_octal, (1 << 2))
		table.attach(self._permission_others_read, 1, 2, 2, 3)

		self._permission_others_write = gtk.CheckButton(_('Write'))
		self._permission_others_write.connect('toggled', self._update_octal, (1 << 1))
		table.attach(self._permission_others_write, 2, 3, 2, 3)

		self._permission_others_execute = gtk.CheckButton(_('Execute'))
		self._permission_others_execute.connect('toggled', self._update_octal, (1 << 0))
		table.attach(self._permission_others_execute, 3, 4, 2, 3)

		# octal representation
		label = gtk.Label(_('Octal:'))
		label.set_alignment(0, 0.5)
		table.attach(label, 0, 1, 3, 4)

		self._permission_octal_entry = gtk.Entry(4)
		self._permission_octal_entry.set_width_chars(5)
		self._permission_octal_entry.connect('activate', self._entry_activate)
		table.attach(self._permission_octal_entry, 1, 2, 3, 4)
		table.set_row_spacing(2, 10)

		# pack interface
		self._advanced.pack_start(table, False, False, 0)
		expander.add(self._advanced)
		self._container.pack_start(expander, False, False, 0)

		self.update_mode()
		expander.show_all()

	def _entry_activate(self, widget, data=None):
		"""Handle octal mode change"""
		self._mode = int(widget.get_text(), 8)
		self.update_mode()

	def _update_octal(self, widget, data=None):
		"""Update octal entry box"""
		if self._permission_updating: return

		data = int(str(data), 8)
		self._mode += (-1, 1)[widget.get_active()] * data

		self.update_mode()

	def _update_checkboxes(self, widget=None, data=None):
		"""Update checkboxes accordingly"""
		self._permission_updating = True
		self._permission_owner_read.set_active(self._mode & 0b100000000)
		self._permission_owner_write.set_active(self._mode & 0b010000000)
		self._permission_owner_execute.set_active(self._mode & 0b001000000)
		self._permission_group_read.set_active(self._mode & 0b000100000)
		self._permission_group_write.set_active(self._mode & 0b000010000)
		self._permission_group_execute.set_active(self._mode & 0b000001000)
		self._permission_others_read.set_active(self._mode & 0b000000100)
		self._permission_others_write.set_active(self._mode & 0b000000010)
		self._permission_others_execute.set_active(self._mode & 0b000000001)
		self._permission_updating = False

	def _expander_event(self, widget, data=None):
		"""Return dialog size back to normal"""
		if widget.get_expanded():
			self.set_size_request(1, 1)
			self.resize(*self._dialog_size)

		else:
			self._dialog_size = self.get_size()
			self.set_size_request(-1, -1)

	def get_mode(self):
		"""Returns default directory/file creation mode"""
		return self._mode

	def set_mode(self, mode):
		"""Set directory/file creation mode"""
		self._mode = mode
		self.update_mode()

	def update_mode(self):
		"""Update widgets"""
		self._permission_octal_entry.set_text('{0}'.format(oct(self._mode)))
		self._update_checkboxes()


class FileCreateDialog(CreateDialog):

	def __init__(self, application):
		CreateDialog.__init__(self, application)

		self.set_title(_('Create empty file'))
		self.set_label(_('Enter new file name:'))

		# create option to open file in editor
		self._checkbox_edit_after = gtk.CheckButton(_('Open file in editor'))

		# create template list
		vbox_templates = gtk.VBox(False, 0)
		label_templates = gtk.Label(_('Template:'))
		label_templates.set_alignment(0, 0.5)

		cell_icon = gtk.CellRendererPixbuf()
		cell_name = gtk.CellRendererText()

		self._templates = gtk.ListStore(str, str, str)
		self._template_list = gtk.ComboBox(self._templates)
		self._template_list.set_row_separator_func(self._row_is_separator)
		self._template_list.connect('changed', self._template_changed)
		self._template_list.pack_start(cell_icon, False)
		self._template_list.pack_start(cell_name, True)

		self._template_list.add_attribute(cell_icon, 'icon-name', 2)
		self._template_list.add_attribute(cell_name, 'text', 0)

		# pack interface
		vbox_templates.pack_start(label_templates, False, False, 0)
		vbox_templates.pack_start(self._template_list, False, False, 0)

		self._container.pack_start(self._checkbox_edit_after, False, False, 0)
		self._container.pack_start(vbox_templates, False, False, 0)

		self._container.reorder_child(self._checkbox_edit_after, 1)
		self._container.reorder_child(vbox_templates, 1)

		# populate template list
		self._populate_templates()

		# show all widgets
		self._dialog.show_all()

	def _populate_templates(self):
		"""Populate templates list"""
		self._templates.clear()

		# add items from templates directory
		directory = get_user_directory(UserDirectory.TEMPLATES)
		file_list = []

		if directory is not None:
			file_list = os.listdir(directory)
			file_list = filter(lambda file_: file_[0] != '.', file_list)  # skip hidden files

		# add empty file
		self._templates.append((_('Empty File'), '', 'document'))
		if len(file_list) > 0:
			self._templates.append(('', '', ''))  # separator

		for file_ in file_list:
			name = os.path.splitext(file_)[0]
			full_path = os.path.join(user.home, 'Templates', file_)
			icon_name = self._application.icon_manager.get_icon_for_file(full_path)

			self._templates.append((name, full_path, icon_name))

		# select default item
		self._template_list.set_active(0)

	def _row_is_separator(self, model, row, data=None):
		"""Determine if row being drawn is a separator"""
		return model.get_value(row, 0) == ''

	def _template_changed(self, widget, data=None):
		"""Handle changing template"""
		file_name = os.path.splitext(self._entry.get_text())
		active_item = self._template_list.get_active()

		# change extension only if specific template is selected
		if active_item > 0:
			extension = os.path.splitext(self._templates[active_item][1])[1]
			self._entry.set_text('{0}{1}'.format(file_name[0], extension))

	def get_edit_file(self):
		"""Get state of 'edit after creating' checkbox"""
		return self._checkbox_edit_after.get_active()

	def get_template_file(self):
		"""Return full path to template file

		In case when 'Empty File' is selected, return None

		"""
		result = None
		active_item = self._template_list.get_active()

		if active_item > 0:
			result = self._templates[active_item][1]

		return result


class DirectoryCreateDialog(CreateDialog):

	def __init__(self, application):
		CreateDialog.__init__(self, application)

		self.set_title(_('Create directory'))
		self.set_label(_('Enter new directory name:'))
		self.set_mode(0755)


class CopyDialog:
	"""Dialog which will ask user for additional options before copying"""

	def __init__(self, application, provider, path):
		self._dialog = gtk.Dialog(parent=application)

		self._application = application
		self._provider = provider

		self._dialog.set_default_size(340, 10)
		self._dialog.set_resizable(True)
		self._dialog.set_skip_taskbar_hint(True)
		self._dialog.set_modal(True)
		self._dialog.set_transient_for(application)
		
		self._dialog.vbox.set_spacing(0)

		# create additional UI
		vbox = gtk.VBox(False, 0)
		vbox.set_border_width(5)

		self.label_destination = gtk.Label()
		self.label_destination.set_alignment(0, 0.5)
		self.label_destination.set_use_markup(True)
		self._update_label()

		self.entry_destination = gtk.Entry()
		self.entry_destination.set_text(path)
		self.entry_destination.set_editable(False)
		self.entry_destination.connect('activate', self._confirm_entry)

		# additional options
		separator = gtk.HSeparator()

		label_type = gtk.Label(_('Only files of this type:'))
		label_type.set_alignment(0, 0.5)

		self.entry_type = gtk.Entry()
		self.entry_type.set_text('*')
		self.entry_type.connect('changed', self._update_label)

		# create operation options
		self.checkbox_owner = gtk.CheckButton(_('Set owner on destination'))
		self.checkbox_mode = gtk.CheckButton(_('Set access mode on destination'))
		self.checkbox_timestamp = gtk.CheckButton(_('Set date and time on destination'))
		self.checkbox_silent = gtk.CheckButton(_('Silent mode'))

		align_silent = gtk.Alignment()
		align_silent.set_padding(0, 0, 15, 15)
		vbox_silent = gtk.VBox(False, 0)
		vbox_silent.set_sensitive(False)

		self.checkbox_merge = gtk.CheckButton(_('Merge directories'))
		self.checkbox_overwrite = gtk.CheckButton(_('Overwrite files'))

		self.checkbox_silent.connect('toggled', self._toggled_silent_mode, vbox_silent)
		self.checkbox_silent.set_tooltip_text(_(
										'Silent mode will enable operation to finish '
										'without disturbing you. If any errors occur, '
										'they will be presented to you after completion.'
									))

		self._create_buttons()

		# pack UI
		vbox_silent.pack_start(self.checkbox_merge, False, False, 0)
		vbox_silent.pack_start(self.checkbox_overwrite, False, False, 0)

		align_silent.add(vbox_silent)

		vbox.pack_start(self.label_destination, False, False, 0)
		vbox.pack_start(self.entry_destination, False, False, 0)
		vbox.pack_start(separator, False, False, 5)
		vbox.pack_start(label_type, False, False, 0)
		vbox.pack_start(self.entry_type, False, False, 0)
		vbox.pack_start(self.checkbox_owner, False, False, 0)
		vbox.pack_start(self.checkbox_mode, False, False, 0)
		vbox.pack_start(self.checkbox_timestamp, False, False, 0)
		vbox.pack_start(self.checkbox_silent, False, False, 0)
		vbox.pack_start(align_silent, False, False, 0)

		self._dialog.vbox.pack_start(vbox, False, False, 0)

		self._load_configuration()

		self._dialog.set_default_response(gtk.RESPONSE_OK)
		self._dialog.show_all()

	def _load_configuration(self):
		"""Load options from config file"""
		options = self._application.options

		self.checkbox_owner.set_active(options.getboolean('main', 'operation_set_owner'))
		self.checkbox_mode.set_active(options.getboolean('main', 'operation_set_mode'))
		self.checkbox_timestamp.set_active(options.getboolean('main', 'operation_set_timestamp'))
		self.checkbox_silent.set_active(options.getboolean('main', 'operation_silent'))
		self.checkbox_merge.set_active(options.getboolean('main', 'operation_merge_in_silent'))
		self.checkbox_overwrite.set_active(options.getboolean('main', 'operation_overwrite_in_silent'))

	def _save_configuration(self, widget=None, data=None):
		"""Save default dialog configuration"""
		options = self._application.options
		_bool = ('False', 'True')

		options.set('main', 'operation_set_owner', _bool[self.checkbox_owner.get_active()])
		options.set('main', 'operation_set_mode', _bool[self.checkbox_mode.get_active()])
		options.set('main', 'operation_set_timestamp', _bool[self.checkbox_timestamp.get_active()])
		options.set('main', 'operation_silent', _bool[self.checkbox_silent.get_active()])
		options.set('main', 'operation_merge_in_silent', _bool[self.checkbox_merge.get_active()])
		options.set('main', 'operation_overwrite_in_silent', _bool[self.checkbox_overwrite.get_active()])

	def _toggled_silent_mode(self, widget, container):
		"""Set container sensitivity based on widget status"""
		container.set_sensitive(widget.get_active())
		
	def _get_text_variables(self, count):
		"""Get text variables for update"""
		title = ngettext(
					'Copy item',
					'Copy items',
					count
				)
		label = ngettext(
					'Copy <b>{0}</b> item to:',
					'Copy <b>{0}</b> items to:',
					count
				)

		return title, label

	def _create_buttons(self):
		"""Create action buttons"""
		button_cancel = gtk.Button(_('Cancel'))
		button_copy = gtk.Button(_('Copy'))
		button_copy.set_flags(gtk.CAN_DEFAULT)

		image_save = gtk.Image()
		image_save.set_from_stock(gtk.STOCK_SAVE, gtk.ICON_SIZE_BUTTON)
		button_save = gtk.Button()
		button_save.set_image(image_save)
		button_save.connect('clicked', self._save_configuration)
		button_save.set_tooltip_text(_('Save default configuration'))

		align_save = gtk.Alignment()
		align_save.add(button_save)

		self._dialog.action_area.pack_start(align_save, True, True, 0)
		self._dialog.action_area.set_child_secondary(align_save, True)

		self._dialog.add_action_widget(button_cancel, gtk.RESPONSE_CANCEL)
		self._dialog.add_action_widget(button_copy, gtk.RESPONSE_OK)

		self._dialog.action_area.set_homogeneous(False)

	def _confirm_entry(self, widget, data=None):
		"""Enable user to confirm by pressing Enter"""
		if self.entry_destination.get_text() != '':
			self._dialog.response(gtk.RESPONSE_OK)

	def _get_item_count(self):
		"""Count number of items to copy"""
		list_ = self._provider.get_selection()
		result = len(list_)

		if hasattr(self, 'entry_type'):
			matches = fnmatch.filter(list_, self.entry_type.get_text())
			result = len(matches)

		return result

	def _update_label(self, widget=None, data=None):
		"""Update label based on file type and selection"""
		# get item count
		item_count = self._get_item_count()

		# get label text
		title, label = self._get_text_variables(item_count)

		# apply text
		self.set_title(title)
		self.label_destination.set_markup(label.format(item_count))

	def set_title(self, title_text):
		"""Set dialog title"""
		self._dialog.set_title(title_text)

	def get_response(self):
		"""Return value and self-destruct

		This method returns tupple with response code and
		dictionary with other selected options.

		"""
		code = self._dialog.run()
		options = (
				self.entry_type.get_text(),
				self.entry_destination.get_text(),
				self.checkbox_owner.get_active(),
				self.checkbox_mode.get_active(),
				self.checkbox_timestamp.get_active(),
				self.checkbox_silent.get_active(),
				self.checkbox_merge.get_active(),
				self.checkbox_overwrite.get_active()
			)

		self._dialog.destroy()

		return (code, options)


class MoveDialog(CopyDialog):
	"""Dialog which will ask user for additional options before moving"""

	def _get_text_variables(self, count):
		"""Get text variables for update"""
		title = ngettext(
					'Move item',
					'Move items',
					count
				)
		label = ngettext(
					'Move <b>{0}</b> item to:',
					'Move <b>{0}</b> items to:',
					count
				)

		return title, label

	def _create_buttons(self):
		"""Create action buttons"""
		button_cancel = gtk.Button(_('Cancel'))
		button_move = gtk.Button(_('Move'))
		button_move.set_flags(gtk.CAN_DEFAULT)

		self._dialog.add_action_widget(button_cancel, gtk.RESPONSE_CANCEL)
		self._dialog.add_action_widget(button_move, gtk.RESPONSE_OK)


class RenameDialog(InputDialog):
	"""Dialog used for renaming file/directory"""

	def __init__(self, application, selection):
		InputDialog.__init__(self, application)

		self.set_title(_('Rename file/directory'))
		self.set_label(_('Enter a new name for this item:'))
		self.set_text(selection)

		self._entry.select_region(0, len(os.path.splitext(selection)[0]))


class OverwriteDialog:
	"""Dialog used for confirmation of file/directory overwrite"""

	def __init__(self, application, parent):
		self._dialog = gtk.Dialog(parent=parent)

		self._application = application
		self._rename_value = ''
		self._time_format = application.options.get('main', 'time_format')

		self._dialog.set_default_size(400, 10)
		self._dialog.set_resizable(True)
		self._dialog.set_skip_taskbar_hint(False)
		self._dialog.set_modal(True)
		self._dialog.set_transient_for(parent)
		self._dialog.set_urgency_hint(True)

		self._dialog.vbox.set_spacing(0)

		hbox = gtk.HBox(False, 10)
		hbox.set_border_width(10)

		vbox = gtk.VBox(False, 10)
		vbox_icon = gtk.VBox(False, 0)

		# create interface
		icon = gtk.Image()
		icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, gtk.ICON_SIZE_DIALOG)

		self._label_title = gtk.Label()
		self._label_title.set_use_markup(True)
		self._label_title.set_alignment(0, 0.5)
		self._label_title.set_line_wrap(True)

		self._label_message = gtk.Label()
		self._label_message.set_alignment(0, 0.5)
		self._label_message.set_line_wrap(True)

		# inner hbox for original file
		hbox_original = gtk.HBox(False, 0)

		self._icon_original = gtk.Image()
		self._label_original = gtk.Label()
		self._label_original.set_use_markup(True)
		self._label_original.set_alignment(0, 0.5)

		# inner hbox for source file
		hbox_source = gtk.HBox(False, 0)

		self._icon_source = gtk.Image()
		self._label_source = gtk.Label()
		self._label_source.set_use_markup(True)
		self._label_source.set_alignment(0, 0.5)

		# rename expander
		self._expander_rename = gtk.Expander(label=_('Select a new name for the destination'))
		self._expander_rename.connect('activate', self._rename_toggled)
		hbox_rename = gtk.HBox(False, 10)

		self._entry_rename = gtk.Entry()
		button_reset = gtk.Button(_('Reset'))
		button_reset.connect('clicked', self._reset_rename_field)

		# apply to all check box
		self._checkbox_apply_to_all = gtk.CheckButton(_('Apply this action to all files'))
		self._checkbox_apply_to_all.connect('toggled', self._apply_to_all_toggled)

		# pack interface
		vbox_icon.pack_start(icon, False, False, 0)

		hbox_original.pack_start(self._icon_original, False, False, 10)
		hbox_original.pack_start(self._label_original, True, True, 0)

		hbox_source.pack_start(self._icon_source, False, False, 10)
		hbox_source.pack_start(self._label_source, True, True, 0)

		self._expander_rename.add(hbox_rename)

		hbox_rename.pack_start(self._entry_rename, False, False, 0)
		hbox_rename.pack_start(button_reset, False, False, 0)

		vbox.pack_start(self._label_title, False, False, 0)
		vbox.pack_start(self._label_message, False, False, 0)
		vbox.pack_start(hbox_original, False, False, 0)
		vbox.pack_start(hbox_source, False, False, 0)
		vbox.pack_start(self._expander_rename, False, False, 0)
		vbox.pack_start(self._checkbox_apply_to_all, False, False, 0)

		hbox.pack_start(vbox_icon, False, False, 0)
		hbox.pack_start(vbox, True, True, 0)

		self._dialog.vbox.pack_start(hbox, True, True, 0)

		self._create_buttons()
		self._dialog.show_all()

	def _create_buttons(self):
		"""Create basic buttons"""
		button_cancel = gtk.Button(stock=gtk.STOCK_CANCEL)
		button_skip = gtk.Button(label=_('Skip'))

		self._dialog.add_action_widget(button_cancel, gtk.RESPONSE_CANCEL)
		self._dialog.add_action_widget(button_skip, gtk.RESPONSE_NO)

	def _apply_to_all_toggled(self, widget, data=None):
		"""Event called upon clicking on "apply to all" check box"""
		checked = widget.get_active()
		self._expander_rename.set_sensitive(not checked)

	def _rename_toggled(self, widget, data=None):
		"""Event called upon activating expander"""
		expanded = widget.get_expanded()
		self._checkbox_apply_to_all.set_sensitive(expanded)

	def _reset_rename_field(self, widget, data=None):
		"""Reset rename field to predefined value"""
		self._entry_rename.set_text(self._rename_value)

	def _get_data(self, provider, path, relative_to=None):
		"""Return information for specified path using provider"""
		item_stat = provider.get_stat(path, relative_to=relative_to)

		if item_stat.type is FileType.DIRECTORY:
			size = len(provider.list_dir(path, relative_to=relative_to))
			icon = 'folder'

		else:
			size = item_stat.size
			icon = self._application.icon_manager.get_icon_for_file(
																os.path.join(
																			provider.get_path(),
																			path
																		))

		str_size = locale.format('%d', size, True)
		str_date = time.strftime(self._time_format, time.localtime(item_stat.time_modify))

		return (str_size, str_date, icon)

	def set_title_element(self, element):
		"""Set title label with appropriate formatting"""
		pass

	def set_message_element(self, element):
		"""Set message element"""
		pass

	def set_original(self, provider, path, relative_to=None):
		"""Set original element data"""
		data = self._get_data(provider, path, relative_to)

		self._icon_original.set_from_icon_name(data[2], gtk.ICON_SIZE_DIALOG)
		self._label_original.set_markup(
									'<b>{2}</b>\n'
									'<i>{3}</i>\t\t{0}\n'
									'<i>{4}</i>\t{1}'.format(
																data[0],
																data[1],
																_('Original'),
																_('Size:'),
																_('Modified:')
															)
								)

	def set_source(self, provider, path, relative_to=None):
		"""Set source element data"""
		data = self._get_data(provider, path, relative_to)

		self._icon_source.set_from_icon_name(data[2], gtk.ICON_SIZE_DIALOG)
		self._label_source.set_markup(
									'<b>{2}</b>\n'
									'<i>{3}</i>\t\t{0}\n'
									'<i>{4}</i>\t{1}'.format(
																data[0],
																data[1],
																_('Replace with'),
																_('Size:'),
																_('Modified:')
															)
								)

	def set_rename_value(self, name):
		"""Set rename default rename value"""
		self._rename_value = name
		self._entry_rename.set_text(name)

	def get_response(self):
		"""Return value and self-destroy

		This method returns tuple with response code and
		dictionary with other selected options.

		"""
		code = self._dialog.run()
		options = (
				self._expander_rename.get_expanded(),
				self._entry_rename.get_text(),
				self._checkbox_apply_to_all.get_active()
				)

		self._dialog.destroy()

		return (code, options)


class OverwriteFileDialog(OverwriteDialog):

	def __init__(self, application, parent):
		OverwriteDialog.__init__(self, application, parent)

		self._dialog.set_title(_('File conflict'))

	def _create_buttons(self):
		"""Create dialog specific button"""
		button_replace = gtk.Button(label=_('Replace'))
		button_replace.set_can_default(True)

		OverwriteDialog._create_buttons(self)
		self._dialog.add_action_widget(button_replace, gtk.RESPONSE_YES)

		self._dialog.set_default_response(gtk.RESPONSE_YES)

	def set_title_element(self, element):
		"""Set title label with appropriate formatting"""
		message = _('Replace file "{0}"?').format(element.replace('&', '&amp;'))
		self._label_title.set_markup('<span size="large" weight="bold">{0}</span>'.format(message))

	def set_message_element(self, element):
		"""Set message element"""
		message = _(
				'Another file with the same name already exists in '
				'"{0}". Replacing it will overwrite its content.'
			)

		self._label_message.set_text(message.format(element))


class OverwriteDirectoryDialog(OverwriteDialog):

	def __init__(self, application, parent):
		OverwriteDialog.__init__(self, application, parent)

		self._entry_rename.set_sensitive(False)
		self.set_title(_('Directory conflict'))

	def _create_buttons(self):
		"""Create dialog specific button"""
		button_merge = gtk.Button(label=_('Merge'))
		button_merge.set_can_default(True)

		OverwriteDialog._create_buttons(self)
		self._dialog.add_action_widget(button_merge, gtk.RESPONSE_YES)

		self._dialog.set_default_response(gtk.RESPONSE_YES)

	def set_title_element(self, element):
		"""Set title label with appropriate formatting"""
		message = _('Merge directory "{0}"?').format(element)
		self._label_title.set_markup('<span size="large" weight="bold">{0}</span>'.format(message))

	def set_message_element(self, element):
		"""Set message element"""
		message = _(
				'Directory with the same name already exists in '
				'"{0}". Merging will ask for confirmation before '
				'replacing any files in the directory that conflict '
				'with the files being copied.'
			)

		self._label_message.set_text(message.format(element))


class AddBookmarkDialog:
	"""This dialog enables user to change data before adding new bookmark"""

	def __init__(self, application, path):
		self._dialog = gtk.Dialog(parent=application)

		self._application = application

		# configure dialog
		self._dialog.set_title(_('Add bookmark'))
		self._dialog.set_default_size(340, 10)
		self._dialog.set_resizable(True)
		self._dialog.set_skip_taskbar_hint(True)
		self._dialog.set_modal(True)
		self._dialog.set_transient_for(application)

		self._dialog.vbox.set_spacing(0)

		# create component container
		vbox = gtk.VBox(False, 5)
		vbox.set_border_width(5)

		# bookmark name
		label_name = gtk.Label(_('Name:'))
		label_name.set_alignment(0, 0.5)
		self._entry_name = gtk.Entry()
		self._entry_name.connect('activate', self._confirm_entry)

		vbox_name = gtk.VBox(False, 0)

		# bookmark path
		label_path = gtk.Label(_('Location:'))
		label_path.set_alignment(0, 0.5)
		self._entry_path = gtk.Entry()
		self._entry_path.set_text(path)
		self._entry_path.set_editable(False)

		vbox_path = gtk.VBox(False, 0)

		# controls
		button_ok = gtk.Button(stock=gtk.STOCK_OK)
		button_ok.connect('clicked', self._confirm_entry)
		button_ok.set_can_default(True)

		button_cancel = gtk.Button(stock=gtk.STOCK_CANCEL)

		self._dialog.add_action_widget(button_cancel, gtk.RESPONSE_CANCEL)
		self._dialog.action_area.pack_end(button_ok, False, False, 0)
		self._dialog.set_default_response(gtk.RESPONSE_OK)

		# pack interface
		vbox_name.pack_start(label_name, False, False, 0)
		vbox_name.pack_start(self._entry_name, False, False, 0)

		vbox_path.pack_start(label_path, False, False, 0)
		vbox_path.pack_start(self._entry_path, False, False, 0)

		vbox.pack_start(vbox_name, False, False, 0)
		vbox.pack_start(vbox_path, False, False, 0)

		self._dialog.vbox.pack_start(vbox, False, False, 0)

		self._dialog.show_all()

	def _confirm_entry(self, widget, data=None):
		"""Enable user to confirm by pressing Enter"""
		if self._entry_name.get_text() != '':
			self._dialog.response(gtk.RESPONSE_OK)

	def get_response(self):
		"""Return value and self-destruct

		This method returns tupple with response code and
		input text.

		"""
		code = self._dialog.run()

		name = self._entry_name.get_text()
		path = self._entry_path.get_text()

		self._dialog.destroy()

		return (code, name, path)


class OperationError:
	"""Dialog used to ask user about error occured during certain operation."""

	def __init__(self, application):
		self._dialog = gtk.Dialog(parent=application)

		self._application = application

		# configure dialog
		self._dialog.set_title(_('Operation error'))
		self._dialog.set_default_size(340, 10)
		self._dialog.set_resizable(True)
		self._dialog.set_skip_taskbar_hint(True)
		self._dialog.set_modal(True)
		self._dialog.set_transient_for(application)

		self._dialog.vbox.set_spacing(0)

		# create component container
		hbox = gtk.HBox(False, 10)
		hbox.set_border_width(5)

		vbox = gtk.VBox(False, 10)
		vbox_icon = gtk.VBox(False, 0)

		# create interface
		icon = gtk.Image()
		icon.set_from_stock(gtk.STOCK_DIALOG_ERROR, gtk.ICON_SIZE_DIALOG)

		self._label_message = gtk.Label()
		self._label_message.set_alignment(0, 0)
		self._label_message.set_use_markup(True)
		self._label_message.set_line_wrap(True)
		self._label_message.set_size_request(340, -1)
		self._label_message.set_selectable(True)

		self._label_error = gtk.Label()
		self._label_error.set_alignment(0,0)
		self._label_error.set_line_wrap(True)
		self._label_error.set_size_request(340, -1)
		self._label_error.set_selectable(True)

		# create controls
		button_cancel = gtk.Button(label=_('Cancel'))
		button_skip = gtk.Button(label=_('Skip'))
		button_retry = gtk.Button(label=_('Retry'))

		self._dialog.add_action_widget(button_cancel, gtk.RESPONSE_CANCEL)
		self._dialog.add_action_widget(button_skip, gtk.RESPONSE_NO)
		self._dialog.add_action_widget(button_retry, gtk.RESPONSE_YES)

		button_skip.set_can_default(True)
		self._dialog.set_default_response(gtk.RESPONSE_NO)

		# pack interface
		vbox_icon.pack_start(icon, False, False, 0)

		vbox.pack_start(self._label_message, False, False, 0)
		vbox.pack_start(self._label_error, False, False, 0)

		hbox.pack_start(vbox_icon, False, False, 0)
		hbox.pack_start(vbox, True, True, 0)

		self._dialog.vbox.pack_start(hbox, False, False, 0)

		# show all components
		self._dialog.show_all()

	def set_message(self, message):
		"""Set dialog message"""
		self._label_message.set_markup(message)

	def set_error(self, error):
		"""Set error text"""
		self._label_error.set_markup(error)

	def get_response(self):
		"""Return dialog response and self-destruct"""
		code = self._dialog.run()
		self._dialog.destroy()

		return code


class CreateToolbarWidgetDialog:
	"""Create widget persisten dialog."""

	def __init__(self, application):
		self._dialog = gtk.Dialog(parent=application)

		self._application = application

		# configure dialog
		self._dialog.set_title(_('Add toolbar widget'))
		self._dialog.set_default_size(340, 10)
		self._dialog.set_resizable(True)
		self._dialog.set_skip_taskbar_hint(True)
		self._dialog.set_modal(True)
		self._dialog.set_transient_for(application)

		self._dialog.vbox.set_spacing(0)

		# create component container
		vbox = gtk.VBox(False, 5)
		vbox.set_border_width(5)

		# create interfacce
		vbox_name = gtk.VBox(False, 0)

		label_name = gtk.Label(_('Name:'))
		label_name.set_alignment(0, 0.5)

		self._entry_name = gtk.Entry(max=30)

		vbox_type = gtk.VBox(False, 0)

		label_type = gtk.Label(_('Type:'))
		label_type.set_alignment(0, 0.5)

		cell_renderer_icon = gtk.CellRendererPixbuf()
		cell_renderer_text = gtk.CellRendererText()
		cell_renderer_text.set_property('xalign', 0)
		self._type_list = gtk.ListStore(str, str, str)

		self._combobox_type = gtk.ComboBox(self._type_list)
		self._combobox_type.pack_start(cell_renderer_icon, False)
		self._combobox_type.pack_start(cell_renderer_text, True)
		self._combobox_type.add_attribute(cell_renderer_icon, 'icon-name', 2)
		self._combobox_type.add_attribute(cell_renderer_text, 'text', 1)

		# create controls
		button_add = gtk.Button(stock=gtk.STOCK_ADD)
		button_add.set_can_default(True)
		button_cancel = gtk.Button(stock=gtk.STOCK_CANCEL)

		self._dialog.add_action_widget(button_cancel, gtk.RESPONSE_CANCEL)
		self._dialog.add_action_widget(button_add, gtk.RESPONSE_ACCEPT)

		self._dialog.set_default_response(gtk.RESPONSE_ACCEPT)

		# pack interface
		vbox_name.pack_start(label_name, False, False, 0)
		vbox_name.pack_start(self._entry_name, False, False, 0)

		vbox_type.pack_start(label_type, False, False, 0)
		vbox_type.pack_start(self._combobox_type, False, False)

		vbox.pack_start(vbox_name, False, False, 0)
		vbox.pack_start(vbox_type, False, False, 0)

		self._dialog.vbox.pack_start(vbox, False, False, 0)

		# show all widgets
		self._dialog.show_all()

	def update_type_list(self, widgets):
		"""Update type list store"""
		self._type_list.clear()

		for key in widgets.keys():
			# get data
			data = widgets[key]

			# extract data from tuple
			text = data[0]
			icon = data[1]

			# add new item to the list
			self._type_list.append((key, text, icon))

	def get_response(self):
		"""Return dialog response and self-destruct"""
		name = None
		widget_type = None

		# clear text entry before showing
		self._entry_name.set_text('')

		# show dialog
		code = self._dialog.run()

		if code == gtk.RESPONSE_ACCEPT \
		and len(self._type_list) > 0:
			# get name and type
			name = self._entry_name.get_text()
			widget_type = self._type_list[self._combobox_type.get_active()][0]

		self._dialog.destroy()

		return code, name, widget_type


class InputRangeDialog(InputDialog):
	"""Dialog used for getting selection range"""

	def __init__(self, application, text):
		InputDialog.__init__(self, application)

		# set labels
		self.set_title(_('Select range'))
		self.set_label(_('Select part of the text:'))

		# configure entry
		self._entry.set_editable(False)
		self._entry.set_text(text)

	def get_response(self):
		"""Return selection selection_range and self-destruct"""
		code = self._dialog.run()
		selection_range = self._entry.get_selection_bounds()

		self._dialog.destroy()

		return code, selection_range


class ApplicationInputDialog(InputDialog):
	"""Input dialog for associations manager. Offers two fiels
	for entry: application name and command."""

	def __init__(self, application):
		InputDialog.__init__(self, application)

		# configure existing components
		self.set_title(_('Add application'))
		self.set_label(_('Application name:'))

		# create additional components
		vbox_command = gtk.VBox(False, 0)
		hbox_command = gtk.HBox(False, 5)

		label_command = gtk.Label('Command:')
		label_command.set_alignment(0, 0.5)

		button_select = gtk.Button()
		button_select.set_label(_('Select'))
		button_select.connect('clicked', self.__select_application)

		self._entry_command = gtk.Entry()
		
		# pack interface
		hbox_command.pack_start(self._entry_command, True, True, 0)
		hbox_command.pack_start(button_select, False, False, 0)

		vbox_command.pack_start(label_command, False, False, 0)
		vbox_command.pack_start(hbox_command, False, False, 0)

		self._container.pack_start(vbox_command, False, False, 0)
		self._container.set_spacing(5)

		# show components
		self._dialog.show_all()

	def __select_application(self, widget, data=None):
		"""Select application using ApplicationSelectDialog"""
		dialog = ApplicationSelectDialog(self._application)
		response = dialog.get_response()

		if response[0] == gtk.RESPONSE_OK:
			self._entry_command.set_text(response[2])

	def get_response(self):
		"""Get response from dialog"""
		code = self._dialog.run()

		name = self._entry.get_text()
		command = self._entry_command.get_text()

		self._dialog.destroy()

		return code, name, command


class ApplicationSelectDialog:
	"""Provides user with a list of installed applications and
	option to enter command"""
	
	help_url = 'standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-latest.html#exec-variables'
	
	def __init__(self, application, path=None):
		self._dialog = gtk.Dialog(parent=application)
		
		self._application = application
		self.path = path

		# configure dialog
		self._dialog.set_title(_('Open With'))
		self._dialog.set_default_size(500, 400)
		self._dialog.set_resizable(True)
		self._dialog.set_skip_taskbar_hint(True)
		self._dialog.set_modal(True)
		self._dialog.set_transient_for(application)
		self._dialog.set_wmclass('Sunflower', 'Sunflower')

		self._dialog.vbox.set_spacing(0)
		self._dialog.vbox.set_border_width(0)
		
		self._container = gtk.VBox(False, 5)
		self._container.set_border_width(5)

		# create interface		
		vbox_list = gtk.VBox(False, 0)
		
		label_open_with = gtk.Label()
		label_open_with.set_use_markup(True)
		label_open_with.set_alignment(0, 0.5)
		if path is None:
			label_open_with.set_label(_('Select application:'))
			
		else:
			label_open_with.set_label(_('Open <i>{0}</i> with:').format(os.path.basename(path)))
			
		# create application list
		list_container = gtk.ScrolledWindow()
		list_container.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		list_container.set_shadow_type(gtk.SHADOW_IN)
		
		self._store = gtk.ListStore(str, str, str, str, str)
		self._list = gtk.TreeView(model=self._store)
	
		cell_icon = gtk.CellRendererPixbuf()
		cell_name = gtk.CellRendererText()
		cell_generic = gtk.CellRendererText()
		
		column_application = gtk.TreeViewColumn()
		column_application.pack_start(cell_icon, False)
		column_application.pack_start(cell_name, True)
		column_application.add_attribute(cell_icon, 'icon-name', 0)
		column_application.add_attribute(cell_name, 'text', 1)
		column_application.set_expand(True)
		
		column_generic = gtk.TreeViewColumn()
		column_generic.pack_start(cell_generic, True)
		column_generic.add_attribute(cell_generic, 'markup', 4)
		
		self._list.append_column(column_application)
		self._list.append_column(column_generic)
		self._list.set_headers_visible(False)
		self._list.set_search_column(1)
		self._list.set_enable_search(True)
		self._list.connect('cursor-changed', self.__handle_cursor_change)
		self._list.connect('row-activated', self.__handle_row_activated)
		
		self._store.set_sort_column_id(1, gtk.SORT_ASCENDING)
		
		# create custom command entry
		self._expander_custom = gtk.Expander(label=_('Use a custom command'))
		
		hbox_custom = gtk.HBox(False, 7)
		
		self._entry_custom = gtk.Entry()
		
		# pack interface
		list_container.add(self._list)
		vbox_list.pack_start(label_open_with, False, False, 0)
		vbox_list.pack_start(list_container, True, True, 0)
		
		hbox_custom.pack_start(self._entry_custom, True, True, 0)
		self._expander_custom.add(hbox_custom)
		
		self._container.pack_start(vbox_list, True, True, 0)
		self._container.pack_start(self._expander_custom, False, False, 0)
		
		self.vbox.pack_start(self._container, True, True, 0)
				
		# create controls
		button_help = gtk.Button(stock=gtk.STOCK_HELP)
		button_help.connect('clicked', self._application.goto_web, self.help_url)
		
		if path is not None:
			button_ok = gtk.Button(stock=gtk.STOCK_OPEN)

		else:
			button_ok = gtk.Button(stock=gtk.STOCK_OK)

		button_ok.set_can_default(True)
		
		button_cancel = gtk.Button(stock=gtk.STOCK_CANCEL)
		
		self._dialog.action_area.pack_start(button_help, False, False, 0)
		self._dialog.add_action_widget(button_cancel, gtk.RESPONSE_CANCEL)
		self._dialog.add_action_widget(button_ok, gtk.RESPONSE_OK)
		self._dialog.set_default_response(gtk.RESPONSE_OK)
		
		# populate content
		self._load_applications()

		self._dialog.show_all()
		
	def __handle_cursor_change(self, widget, data=None):
		"""Handle setting or changing list cursor"""
		selection = widget.get_selection()
		item_store, selected_iter = selection.get_selected()
		
		if selected_iter is not None:
			command = item_store.get_value(selected_iter, 3)
			self._entry_custom.set_text(command)
			
	def __handle_row_activated(self, path=None, view_column=None, data=None):
		"""Handle choosing application by presing 'Enter'"""
		self._dialog.response(gtk.RESPONSE_OK)
		
	def _load_applications(self):
		"""Populate application list from config files"""
		application_list = self._application.associations_manager.get_all()

		for application in application_list:
			if '%' in application.command_line:
				self._store.append((
							application.icon, 
							application.name, 
							application.id, 
							application.command_line,
							'<small>{0}</small>'.format(application.description)
						))
		
	def get_response(self):
		"""Get response and destroy dialog"""
		code = self._dialog.run()
		is_custom = self._expander_custom.get_expanded()
		command = self._entry_custom.get_text()
		
		self._dialog.destroy()

		return code, is_custom, command
