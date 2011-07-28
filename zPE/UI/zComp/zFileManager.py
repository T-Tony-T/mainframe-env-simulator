# this is the file-manager module of the zComponent package

import io_encap
# this package should implement the following APIs:
#
#   is_binary(fn_list):         test if the fn_list corresponding to a binary file
#
#   is_file(fn_list):           test if the fn_list corresponding to a file
#   is_dir(fn_list):            test if the fn_list corresponding to a directory
#
#   new_file(fn_list):          create the file unless the fn_list corresponding to a file
#   new_dir(fn_list):           create the dir unless the fn_list corresponding to a directory
#
#   open_file(fn_list, mode):   open the file with the indicated mode
#
#   fetch(buff):                read content from the corresponding file to the zEditBuffer
#   flush(buff):                write content from the zEditBuffer to the corresponding file
#

from z_support import XPM, PIXBUF

from zBase import zTheme

import os, stat, time
import pygtk
pygtk.require('2.0')
import gtk


######## ######## ######## ######## ########
########        zFileManager        ########
######## ######## ######## ######## ########

class zFileManager(gtk.VBox):
    '''A Light-Weighted File Manager Used by zEdit Class'''
    column_names     = [ '', 'Name', 'Size', 'Last Changed' ]
    column_xalign    = [  1,  0,         1,   0 ]
    column_resizable = [ False,  True, True, True ]
    column_sizing    = [
        gtk.TREE_VIEW_COLUMN_AUTOSIZE,
        gtk.TREE_VIEW_COLUMN_FIXED,
        gtk.TREE_VIEW_COLUMN_AUTOSIZE,
        gtk.TREE_VIEW_COLUMN_AUTOSIZE
        ]

    def __init__(self, editor = None):
        '''
        editor = None
            any editor that can open an indicated file with:
              editor.set_buffer(fn_list, tpye)
            method call.
        '''
        super(zFileManager, self).__init__()

        self.set_editor(editor)

        # layout of the frame:
        #
        #   +------------+
        #   | path entry |
        #   +------------+_
        #   ||           | \
        #   ||           |  scrolled_window
        #   || treeview  |
        #   ||           |
        #   ||           |
        #   +------------+

        path_box = gtk.HBox()
        self.path_entry_label = gtk.Label('Path: ')
        self.path_entry = gtk.Entry()
        path_box.pack_start(self.path_entry_label, False, False, 0)
        path_box.pack_start(self.path_entry, True, True, 0)

        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        scrolled.set_placement(gtk.CORNER_TOP_RIGHT)
        self.treeview = gtk.TreeView()
        scrolled.add(self.treeview)

        self.pack_start(path_box, False, False, 0)
        self.pack_start(scrolled, True, True, 0)

        # init flags
        self.__cell_data_func_skip = { # if set, no auto testing
            'path' : None,             # path of the skipping item
            'type' : None,             # type of the skipping
            }
        self.__file_name_old = ''
        self.__on_setting_folder = False

        # init widget reference relevant to editable column (file listing)
        self.treeview.model = gtk.ListStore(str, bool)
        self.treeview.set_model(self.treeview.model)

        self.treeview.fn_cell_rdr = gtk.CellRendererText()

        self.treeview.fn_tree_col = gtk.TreeViewColumn(
            zFileManager.column_names[1], self.treeview.fn_cell_rdr, text = 0, editable = 1
            )
        self.treeview.fn_tree_col.set_cell_data_func(self.treeview.fn_cell_rdr, self.__cell_data_func)

        # create the TreeViewColumns to display the data
        self.treeview.cell_list   = [None] * len(zFileManager.column_names)
        self.treeview.column_list = [None] * len(zFileManager.column_names)

        # create column 0 (icon)
        self.treeview.cell_list[0] = gtk.CellRendererPixbuf()
        self.treeview.column_list[0] = gtk.TreeViewColumn(zFileManager.column_names[0], self.treeview.cell_list[0])

        # create column 1 (file name)
        self.treeview.cell_list[1] = self.treeview.fn_cell_rdr
        self.treeview.column_list[1] = self.treeview.fn_tree_col

        # create the rest of columns
        for n in range(2, len(zFileManager.column_names)):
            self.treeview.cell_list[n] = gtk.CellRendererText()
            self.treeview.column_list[n] = gtk.TreeViewColumn(zFileManager.column_names[n], self.treeview.cell_list[n])

        # add all columns
        for n in range(len(zFileManager.column_names)):
            self.treeview.cell_list[n].set_property('xalign', zFileManager.column_xalign[n])
            self.treeview.column_list[n].set_resizable(zFileManager.column_resizable[n])
            self.treeview.column_list[n].set_sizing(zFileManager.column_sizing[n])
            self.treeview.append_column(self.treeview.column_list[n])

        # connect signal for redirection
        self.path_entry.connect('focus-in-event',  self._focus_evnt_redirect, 'focus-in-event')
        self.treeview.connect(  'focus-in-event',  self._focus_evnt_redirect, 'focus-in-event')
        self.path_entry.connect('focus-out-event', self._focus_evnt_redirect, 'focus-out-event')
        self.treeview.connect(  'focus-out-event', self._focus_evnt_redirect, 'focus-out-event')

        # connect signal for internal usage
        self.path_entry.connect('activate', self._sig_open_file_from_entry)
        self.treeview.connect('row-activated', self._sig_open_file_from_tree)
        self.treeview.fn_cell_rdr.connect('edited', self._sig_entry_edited)

        # set cwd
        self.set_folder()


    ### signal redirection definition
    def _focus_evnt_redirect(self, widget, event, sig):
        if self.is_focus():
            sig = 'focus-in-event'
        else:
            sig = 'focus-out-event'
        self.emit(sig, event)
    ### end of signal redirection definition


    ### signal definition
    def _sig_entry_edited(self, tree_cell, tree_path, file_name):
        if self.__cell_data_func_skip['type']:
            # new
            if file_name:
                try:
                    # allocate the file/dir
                    if self.__cell_data_func_skip['type'] == 'file':
                        io_encap.new_file([self.dirname, file_name])
                    elif self.__cell_data_func_skip['type'] == 'dir':
                        io_encap.new_dir([self.dirname, file_name])
                except:
                    self.refresh_folder() # reset the current folder
                    raise
            else:
                # self.set_folder() will remove the empty line
                pass
        elif self.__file_name_old:
            # rename
            if file_name:
                # rename the file/dir
                os.renames(os.path.join(self.dirname, self.__file_name_old), os.path.join(self.dirname, file_name))
            else:
                # retain the old name
                self.treeview.model.set_value(iterator, 0, self.__file_name_old)

        # update info
        self.refresh_folder()


    def _sig_new_file(self, treeview, tree_path, new_type):
        iterator = self.treeview.model.get_iter(tree_path)
        tree_path_next = tree_path[:-1] + ( tree_path[-1] + 1, )

        # add new row in the fm
        self.__cell_data_func_skip['path'] = tree_path_next
        self.__cell_data_func_skip['type'] = new_type
        self.treeview.model.insert_after(iterator)

        # make it editable
        self.treeview.model.set_value(self.treeview.model.iter_next(iterator), 1, True)
        self.treeview.set_cursor(self.__cell_data_func_skip['path'], self.treeview.fn_tree_col, True)


    def _sig_open_file_from_entry(self, entry):
        fullpath = os.path.abspath(os.path.expanduser(self.path_entry.get_text()))
        fn_list = os.path.split(fullpath)

        if io_encap.is_dir(fn_list):
            self.set_folder(os.path.join(* fn_list))
        elif io_encap.is_file(fn_list):
            self.open_file(fn_list)
        else:
            self.path_entry.set_text(self.dirname + os.path.sep)
            self.path_entry.grab_focus()
            raise ValueError('Cannot open "{0}".\n    Make sure the path is spelled correctly.'.format(fullpath))

    def _sig_open_file_from_tree(self, treeview, tree_path, tree_col = None):
        iterator = self.treeview.model.get_iter(tree_path)
        fn_list = [ self.dirname, self.treeview.model.get_value(iterator, 0) ]

        if io_encap.is_dir(fn_list):
            self.set_folder(os.path.join(* fn_list))
        elif io_encap.is_file(fn_list):
            self.open_file(fn_list)


    def _sig_rename_file(self, treeview, tree_path):
        iterator = self.treeview.model.get_iter(tree_path)

        # record the old name
        self.__file_name_old = self.treeview.model.get_value(iterator, 0)

        # make it editable
        self.treeview.model.set_value(iterator, 1, True)
        self.treeview.set_cursor(tree_path, self.treeview.fn_tree_col, True)
    ### end of signal definition


    ### overridden function definition
    def is_focus(self):
        return self.path_entry.is_focus() or self.treeview.is_focus()

    def grab_focus(self):
        self.treeview.grab_focus()
        self.treeview.set_cursor((0,))


    def get_active_item(self):
        try:
            (tree_path, tree_col) = self.treeview.get_cursor()
        except:
            return None
        basename = self.treeview.model.get_value(self.treeview.model.get_iter(tree_path), 0)
        return (self.dirname, basename)


    def modify_font(self, font_desc):
        self.path_entry_label.modify_font(font_desc)
        self.path_entry.modify_font(font_desc)
        self.treeview.modify_font(font_desc)
        # resize the Name field
        (w, h) = self.create_pango_layout('w').get_pixel_size()
        self.treeview.fn_tree_col.set_fixed_width(w * zTheme.DISC['fn_len'])

    def modify_base(self, state, color):
        self.path_entry.modify_base(state, color)
        self.treeview.modify_base(state, color)

    def modify_text(self, state, color):
        self.path_entry.modify_text(state, color)
        self.treeview.modify_text(state, color)
    ### end of overridden function definition


    def open_file(self, fn_list):
        if not self.get_editor():
            raise ReferenceError('No editor set! Use `set_editor(editor)` first.')
        self.get_editor().set_buffer(fn_list, 'file')


    def get_editor(self):
        return self.__editor_frame

    def set_editor(self, editor):
        self.__editor_frame = editor


    def get_folder(self):
        return self.dirname

    def set_folder(self, fullpath = None):
        # get real path
        if not fullpath:
            new_dirname = os.path.expanduser('~')
        else:
            new_dirname = os.path.abspath(fullpath)

        # test permission
        if not os.access(new_dirname, os.F_OK):
            raise AssertionError('Fatal Error: directory does not exist!')
        if not os.access(new_dirname, os.R_OK):
            raise AssertionError('Permission Denied: directory not readable!')
        if not os.access(new_dirname, os.X_OK):
            raise AssertionError('Permission Denied: directory not navigable!')

        # begin to changing folder
        if self.__on_setting_folder:
            return              # early return
        else:
            self.__on_setting_folder = True

        self.dirname = new_dirname
        self.treeview.dirname = self.dirname

        # fetch file listing
        file_list = []
        dir_list = []
        for non_hidden in [ fn for fn in os.listdir(self.dirname) if fn[0] <> '.' ]:
            fn_list = [ self.dirname, non_hidden ]
            if io_encap.is_dir(fn_list):
                dir_list.append(non_hidden)
            else:
                file_list.append(non_hidden)

        file_list.sort(key = str.lower)
        dir_list.sort(key = str.lower)
        dir_list = ['..'] + dir_list

        # update model with the listing
        self.treeview.model.clear()
        for fn in dir_list:
            self.treeview.model.append([fn, False])
        for fn in file_list:
            self.treeview.model.append([fn, False])
        self.path_entry.set_text(self.dirname + os.path.sep)

        self.grab_focus()

        # clear flags
        for key in self.__cell_data_func_skip:
            self.__cell_data_func_skip[key] = None
        self.__file_name_old = ''

        self.__on_setting_folder = False


    def refresh_folder(self):
        self.set_folder(self.dirname)


    ### cell data function
    def __cell_data_func(self, column, cell, model, iterator):
        try:
            self.__file_pixbuf(0, iterator)
            self.__file_size(2, iterator)
            self.__file_last_changed(3, iterator)
        except:
            self.treeview.cell_list[0].set_property('pixbuf', None)
            self.treeview.cell_list[2].set_property('text', None)
            self.treeview.cell_list[3].set_property('text', '<Changed on disk>')

    def __file_pixbuf(self, indx, iterator):
        if ( self.__cell_data_func_skip['type']  and
             self.__cell_data_func_skip['path'] == self.treeview.model.get_path(iterator)
             ):
            if self.__cell_data_func_skip['type'] == 'file':
                pb = PIXBUF['file']
            else:
                pb = PIXBUF['folder']
        else:
            filename = os.path.join(self.dirname, self.treeview.model.get_value(iterator, 0))
            filestat = os.stat(filename)

            if stat.S_ISDIR(filestat.st_mode):
                pb = PIXBUF['folder']
            else:
                pb = PIXBUF['file']
        self.treeview.cell_list[indx].set_property('pixbuf', pb)


    def __file_size(self, indx, iterator):
        if ( self.__cell_data_func_skip['type']  and
             self.__cell_data_func_skip['path'] == self.treeview.model.get_path(iterator)
             ):
            self.treeview.cell_list[indx].set_property('text', '')
            return
            
        filename = os.path.join(self.dirname, self.treeview.model.get_value(iterator, 0))
        filestat = os.stat(filename)

        size = filestat.st_size
        if size < 1024:
            size = '{0}.0'.format(size) # the extra '.0' is required to pass the parser
            unit = 'B'
        elif size < 1048576:            # 1024 ^ 2
            size = '{0:.1f}'.format(size / 1024.0)
            unit = 'K'
        elif size < 1073741824:         # 1024 ^ 3
            size = '{0:.1f}'.format(size / 1048576.0)
            unit = 'M'
        else:
            size = '{0:.1f}'.format(size / 1073741824.0)
            unit = 'G'
        if size[-2:] == '.0':
            size = size[:-2]
        self.treeview.cell_list[indx].set_property('text', size + unit)


    def __file_last_changed(self, indx, iterator):
        if ( self.__cell_data_func_skip['type']  and
             self.__cell_data_func_skip['path'] == self.treeview.model.get_path(iterator)
             ):
            self.treeview.cell_list[indx].set_property('text', '')
            return

        filename = os.path.join(self.dirname, self.treeview.model.get_value(iterator, 0))
        filestat = os.stat(filename)

        self.treeview.cell_list[indx].set_property('text', time.ctime(filestat.st_mtime))
    ### end of cell data function
