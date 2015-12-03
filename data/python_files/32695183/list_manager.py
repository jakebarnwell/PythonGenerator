import gtk
from subprocess import Popen, PIPE
import threading
from constants import movie_list_columns
from constants import movie_grid_columns
import movie_tagger
import library_manager
import prefs_manager

class View(object):
	media = ''
	layout = ''
	view = None
	prefs = prefs_manager.PrefsManager()

	def create_column_list(self):
		return []
	
	def create_view(self):
		pass
	
	def load_library(self):
		pass
	
	def setup_context_menus(self):
		self.single_select_context_menu.append(self.single_edit_info_item)
		self.single_select_context_menu.append(self.single_remove_item)
		self.single_edit_info_item.show()
		self.single_remove_item.show()

		self.multiple_select_context_menu.append(self.multiple_edit_info_item)
		self.multiple_select_context_menu.append(self.multiple_remove_item)
		self.multiple_edit_info_item.show()
		self.multiple_remove_item.show()

		key, modifier = gtk.accelerator_parse('<Control>I')
		self.single_edit_info_item.add_accelerator('activate', self.accel_group, key, modifier, gtk.ACCEL_VISIBLE)
	
	def __init__(self):
		self.accel_group = gtk.AccelGroup()
		self.single_select_context_menu = gtk.Menu()
		self.multiple_select_context_menu = gtk.Menu()
		self.single_edit_info_item = gtk.MenuItem("Edit Info...")
		self.single_remove_item = gtk.MenuItem("Remove From Library")
		self.multiple_edit_info_item = gtk.MenuItem("Edit Info For Multiple Items...")
		self.multiple_remove_item = gtk.MenuItem("Remove From Library")
		self.setup_context_menus()


class MovieListView(View):
	media = 'movies'
	layout = 'list'
	view = gtk.TreeView()
	prefs = prefs_manager.PrefsManager()

	def create_column_list(self):
		"""Creates all columns with properties and returns them as a list."""
		columns = [gtk.TreeViewColumn(param['label'], param['renderer']) for param in movie_list_columns]

		for column in columns:
			column.set_reorderable(True)

		for index, column in enumerate(columns):
			column.set_sort_column_id(index)
			
			if movie_list_columns[index]['type'] == bool:
				column.add_attribute(movie_list_columns[index]['renderer'], 'active', index)
				movie_list_columns[index]['renderer'].connect('toggled', self.on_watched_toggle)
			else:
				column.add_attribute(movie_list_columns[index]['renderer'], 'text', index)

			column.set_cell_data_func(movie_list_columns[index]['renderer'],
										movie_list_columns[index]['func'],
										index)

		return columns
	
	def set_column_visibility(self):
		"""Sets whether each column is visible based on preferencs."""
		tag_dict = self.prefs.get_cols_choices(self.media)
		columns = self.view.get_columns()
		for column in columns:
			name = self.col_dict[column.get_title()]
			if name in tag_dict.keys():
				column.set_visible(tag_dict[name] == 'True')
	
	def save_column_order(self):
		"""Saves the column order to a preferences file."""
		columns = self.view.get_columns()
		col_pos = {}

		for pos, column in enumerate(columns):
			col_pos[self.col_dict[column.get_title()]] = str(pos)

		self.prefs.save_cols_positions(self.media, col_pos)
	
	def save_column_widths(self):
		"""Gets the current width of each column and saves it to a preferences file."""
		columns = self.view.get_columns()
		col_widths = {}
		for column in columns:
			col_widths[self.col_dict[column.get_title()]] = str(column.get_width())
		
		self.prefs.save_cols_widths(self.media, col_widths)
	
	def set_sorted_column(self):
		"""Sets the currently sorted column based on the saved preferences."""
		sorted_column_id = int(self.prefs.get_active_col(self.media))
		self.movie_list.set_sort_column_id(sorted_column_id, gtk.SORT_ASCENDING)

	def save_sorted_column(self):
		"""Saves the currently sorted column to a preferences file."""
		sorted_column_id = self.movie_list.get_sort_column_id()[0]
		columns = self.view.get_columns()
		column_name = self.col_dict[columns[sorted_column_id].get_title()]
		self.prefs.save_active_col(self.media, column_name)

	def create_view(self):
		"""Creates a TreeView and inserts all columns."""
		self.view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		self.view.set_rules_hint(True)
		self.view.set_model(self.movie_list)
		columns = self.create_column_list()
		positions = self.prefs.get_cols_positions(self.media)
		widths = self.prefs.get_cols_widths(self.media)

		for column in columns:
			column.set_resizable(True)
			column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
			width = int(widths[self.col_dict[column.get_title()]])

			if width > 0:
				column.set_fixed_width(width)

			self.view.insert_column(column, int(positions[self.col_dict[column.get_title()]]))

		self.set_column_visibility()

	def load_library(self):
		"""Loads the movie library into the current ListStore."""
		lib_manager = library_manager.MovieListManager()
		library = lib_manager.load_library()
		if self.movie_list.get_iter_root():
			self.movie_list.clear()
		
		for movie in library:
			self.movie_list.append(movie)
	
	def on_view_button_press(self, treeview, event):
		"""TreeView button press signal

		Checks for right click and pops up a menu

		"""
		if event.button == 3:
			path = treeview.get_path_at_pos(int(event.x), int(event.y))
			selection = treeview.get_selection()

			if path[0] not in selection.get_selected_rows()[1]:
				selection.unselect_all()
				selection.select_path(path[0])

			if selection.count_selected_rows() > 1:
				self.multiple_select_context_menu.popup(None, None, None, event.button, event.time)
			else:
				self.single_select_context_menu.popup(None, None, None, event.button, event.time)

			return True

	def on_edit_item_click(self, menu_item, data=None):
		"""Edit Item clicked signal.

		Gets the currently selected item and then opens a
		MovieTagger instance to edit the data.
		"""
		path_column = [prop['name'] for prop in movie_list_columns].index('path')

		movie_list, selected_rows = self.view.get_selection().get_selected_rows()

		if selected_rows:
			path = movie_list[selected_rows[0]][path_column]
			selected_movie = library_manager.MovieLibraryManager.get_item_from_library(path)
			movie_tagger.MovieTagger(selected_movie)
			return True
		else:
			return False
	
	def on_watched_toggle(self, cell, path, data=None):
		column_names = [prop['name'] for prop in movie_list_columns]
		watched_col = column_names.index('watched')
		path_col = column_names.index('path')
		selection = self.view.get_selection()

		for row in selection.get_selected_rows()[1]:
			if row:
				iter = self.movie_list.get_iter(row)
				self.movie_list[iter][watched_col] = not self.movie_list[iter][watched_col]
	
	def __init__(self):
		super(MovieListView, self).__init__()

		self.view.connect('button-press-event', self.on_view_button_press)
		self.single_edit_info_item.connect('activate', self.on_edit_item_click)

		self.movie_list = gtk.ListStore(*[param['type'] for param in movie_list_columns])

		self.col_dict = {}
		for param in movie_list_columns:
			self.col_dict[param['label']] = param['name']

		self.create_view()
		self.load_library()
		self.set_sorted_column()

class MovieGridView(View):
	media = 'movies'
	layout = 'grid'
	view = gtk.IconView()
	prefs = prefs_manager.PrefsManager()

	def create_view(self):
		self.view.set_selection_mode(gtk.SELECTION_MULTIPLE)
		style = self.view.get_style().copy()
		grey = gtk.gdk.Color('#4F4F4F')
		style.base[gtk.STATE_NORMAL] = grey
		self.view.set_style(style)
		self.view.set_model(self.movie_list)
		self.view.set_pixbuf_column(0)
		self.view.set_text_column(1)
		self.view.set_tooltip_column(2)

	def load_library(self):
		"""Loads the movie library into the current ListStore."""
		lib_manager = library_manager.MovieGridManager()
		library = lib_manager.load_library()
		if self.movie_list.get_iter_root():
			self.movie_list.clear()

		for movie in library:
			self.movie_list.append(movie)

		self.movie_list.set_sort_column_id(1, gtk.SORT_ASCENDING)

	def on_view_button_press(self, iconview, event):
		"""IconView button press signal

		Checks for right click and pops up a menu

		"""
		if event.button == 3:
			path = iconview.get_path_at_pos(int(event.x), int(event.y))

			if not path:
				return False

			if path not in iconview.get_selected_items():
				iconview.unselect_all()
				iconview.select_path(path[0])

			if len(iconview.get_selected_items()) > 1:
				self.multiple_select_context_menu.popup(None, None, None, event.button, event.time)
			else:
				self.single_select_context_menu.popup(None, None, None, event.button, event.time)

			return True

	def on_item_activated(self, iconview, path):
		if len(iconview.get_selected_items()) > 1:
			return False

		#gobject.threads_init()
		path_column = 1 + [prop['name'] for prop in movie_list_columns].index('path')
		movie_path = self.movie_list[path][path_column]
		process = Popen(['vlc', movie_path], stdout=PIPE, stderr=PIPE)
		process_func = lambda: process.communicate()
		play_thread = threading.Thread(target=process_func)
		play_thread.start()
		return True

	def on_edit_item_click(self, menu_item, data=None):
		"""Edit Item clicked signal.

		Gets the currently selected item and then opens a
		MovieTagger instance to edit the data.
		"""
		path_column = 1 + [prop['name'] for prop in movie_list_columns].index('path')

		selected_items = self.view.get_selected_items()

		if selected_items:
			path = self.movie_list[selected_items[0]][path_column]
			selected_movie = library_manager.MovieLibraryManager.get_item_from_library(path)
			movie_tagger.MovieTagger(selected_movie)
			return True
		else:
			return False
	
	def __init__(self):
		super(MovieGridView, self).__init__()

		self.view.connect('button-press-event', self.on_view_button_press)
		self.view.connect('item-activated', self.on_item_activated)
		self.single_edit_info_item.connect('activate', self.on_edit_item_click)

		list_types = [param['type'] for param in movie_grid_columns]
		self.movie_list = gtk.ListStore(gtk.gdk.Pixbuf, str, *list_types)
		self.create_view()
		self.load_library()
		

class MainView:
	current_view = View()
	movie_list_view = MovieListView()
	movie_grid_view = MovieGridView()

	def get_current_view_params(self):
		return {'media' : self.current_view.media,
				'layout' : self.current_view.layout}
	
	def set_current_view(self, media, layout, scrolled_window):
		"""Sets the current view based on media type and layout."""
		scrolled_window.hide()
		if scrolled_window.get_children():
			scrolled_window.remove(self.current_view.view)

		self.current_view = self.get_view(media, layout)
		scrolled_window.add(self.current_view.view)
		scrolled_window.show_all()
		#self.current_view.load_library()

	def get_view(self, media, layout):
		"""Gets the appropriate view class instance."""
		if media == 'movies' and layout == 'list':
			return self.movie_list_view
		elif media == 'movies' and layout == 'grid':
			return self.movie_grid_view
	
	def load_library(self):
		"""Loads the appropriate library into the current view."""
		self.current_view.load_library()
