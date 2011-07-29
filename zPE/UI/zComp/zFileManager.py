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
import sqlite3

import pygtk
pygtk.require('2.0')
import gtk
import gobject


######## ######## ######## ######## ########
########       zDisplayPanel        ########
######## ######## ######## ######## ########

class zDisplayPanel(gtk.VBox):
    '''A Read-Only Display Panel Used by zEdit Class'''
    _DB_FILE = None # overall db setting; this *will* take precedence if set

    def __init__(self, db_file = None, editor = None):
        '''
        db_file = None
            the database file name (full path prefered) that
            the display panel is to be connected to.
            Unless set, no information will be displayed.

        editor = None
            any editor that can open an indicated file with:
              editor.set_buffer(fn_list, tpye)
            method call.
        '''
        super(zDisplayPanel, self).__init__()

        self.__on_init = True

        self.__db_file = None
        self.__conn = None
        self.__c = None

        self.__active_job = None
        self.__active_step = None

        self.__job_list = [
            # (id, name), (id, name), ...
            ]
        self.__step_list = [
            # (dd, step), (dd, step), ...
            ]

        self.set_db(db_file)
        self.set_editor(editor)

        # layout of the frame:
        #
        #          scrolled_window
        #         /
        #   +-------+---------------+
        #   || job  ||              |_
        #   |+------||    center    | \
        #   +-------+|              |  scrolled_window
        #   || step ||              |
        #   |+------|+--------------|
        #   +-------+---------------+
        #     \
        #      scrolled_window

        self.minor_paned = gtk.VPaned()
        self.major_paned = gtk.HPaned()
        self.add(self.major_paned)

        self.job_panel = zListing(gtk.ListStore(str))
        self.step_panel = zListing(gtk.ListStore(str))

        self.job_panel.extend_columns(
            [ 'Job Name', 'Job ID' ], [ gtk.CellRendererText(), gtk.CellRendererText() ]
            )
        self.step_panel.extend_columns(
            [ 'DD Name', 'Step Name' ], [ gtk.CellRendererText(), gtk.CellRendererText() ]
            )

        self.job_panel.column_list[0].set_cell_data_func( self.job_panel.cell_list[0],  self.__cell_data_job_name)
        self.job_panel.column_list[1].set_attributes(     self.job_panel.cell_list[1],  text = 0)
        self.step_panel.column_list[0].set_attributes(    self.step_panel.cell_list[0], text = 0)
        self.step_panel.column_list[1].set_cell_data_func(self.step_panel.cell_list[1], self.__cell_data_step_name)

        scrolled_job = gtk.ScrolledWindow()
        scrolled_step = gtk.ScrolledWindow()

        scrolled_job.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        scrolled_job.set_placement(gtk.CORNER_TOP_RIGHT)
        scrolled_job.add(self.job_panel)

        scrolled_step.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        scrolled_step.set_placement(gtk.CORNER_TOP_RIGHT)
        scrolled_step.add(self.step_panel)

        self.minor_paned.pack1(scrolled_job, True, True)
        self.minor_paned.pack2(scrolled_step, True, True)

        self.center = gtk.TextView()
        self.center.set_editable(False)
        self.center.set_cursor_visible(False)

        scrolled_center = gtk.ScrolledWindow()
        scrolled_center.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
        scrolled_center.set_placement(gtk.CORNER_TOP_RIGHT)
        scrolled_center.add(self.center)

        self.major_paned.pack1(self.minor_paned, False, True)
        self.major_paned.pack2(scrolled_center, True, True)

        # connect signal for redirection
        self.job_panel.connect( 'focus-in-event',  self._focus_evnt_redirect, 'focus-in-event')
        self.step_panel.connect('focus-in-event',  self._focus_evnt_redirect, 'focus-in-event')
        self.center.connect(    'focus-in-event',  self._focus_evnt_redirect, 'focus-in-event')
        self.job_panel.connect( 'focus-out-event',  self._focus_evnt_redirect, 'focus-out-event')
        self.step_panel.connect('focus-out-event',  self._focus_evnt_redirect, 'focus-out-event')
        self.center.connect(    'focus-out-event',  self._focus_evnt_redirect, 'focus-out-event')

        # connect signal for internal usage
        self.job_panel.connect( 'cursor-changed', self._sig_job_selected)
        self.step_panel.connect('cursor-changed', self._sig_step_selected)

        self.job_panel.connect( 'button-press-event', self._sig_button_press)
        self.step_panel.connect('button-press-event', self._sig_button_press)


        # initiate the timer to watch the overall settings
        gobject.timeout_add(20, self.__watch_overall_settings)

        self.__on_init = False


    ### signal redirection definition
    def _focus_evnt_redirect(self, widget, event, sig):
        if self.is_focus():
            sig = 'focus-in-event'
        else:
            sig = 'focus-out-event'
        self.emit(sig, event)
    ### end of signal redirection definition


    ### signal definition
    def _sig_job_selected(self, treeview):
        tree_path = treeview.get_cursor()[0][-1]
        job_id = self.__job_list[tree_path][0]

        self.__active_step = None # reset active step since job panel is clicked
        self.__active_job = job_id

        self.update_step_list()
        self.update_content()

    def _sig_step_selected(self, treeview):
        tree_path = treeview.get_cursor()[0][-1]
        dd_name = self.__step_list[tree_path][0]

        self.__active_step = dd_name

        self.update_content()


    def _sig_button_press(self, treeview, event, data = None):
        if event.button != 3:
            return

        # create the menu
        menu = gtk.Menu()

        # fill the menu
        try:
            ( tree_path, tree_col, dummy_x, dummy_y ) = treeview.get_path_at_pos(int(event.x), int(event.y))
        except:
            # not on a row; select the last row
            try:
                iterator = treeview.model.get_iter_first()
                while treeview.model.iter_next(iterator):
                    iterator = treeview.model.iter_next(iterator)
                tree_path = treeview.model.get_path(iterator)
            except:
                # no row in the listing, early return
                return
        treeview.set_cursor(tree_path)

        mi_purge     = gtk.MenuItem('_Purge Selected Job')
        mi_purge_all = gtk.MenuItem('P_urge All Jobs')

        menu.append(mi_purge)
        menu.append(mi_purge_all)

        mi_purge.connect(    'activate', self._sig_purge_jobs, self.__active_job)
        mi_purge_all.connect('activate', self._sig_purge_jobs, '%')


        # popup the menu
        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)

    def _sig_purge_jobs(self, menuitem, job_pttn):
        self.delete_jobs(job_pttn)
    ### end of signal definition


    ### overridden function definition
    def is_focus(self):
        return self.job_panel.is_focus() or self.step_panel.is_focus() or self.center.is_focus()

    def grab_focus(self):
        self.job_panel.grab_focus()


    def modify_font(self, font_desc):
        font_desc.set_size(int(font_desc.get_size() * 0.85))
        self.job_panel.modify_font(font_desc)
        self.step_panel.modify_font(font_desc)
        self.center.modify_font(font_desc)
        # resize the major paned
        (w, h) = self.center.create_pango_layout('w').get_pixel_size()
        self.major_paned.set_position(max(w * 16, 160)) # 160 is the default header width

    def modify_base(self, state, color):
        self.job_panel.modify_base(state, color)
        self.step_panel.modify_base(state, color)
        self.center.modify_base(state, color)

    def modify_text(self, state, color):
        self.job_panel.modify_text(state, color)
        self.step_panel.modify_text(state, color)
        self.center.modify_text(state, color)
    ### end of overridden function definition


    ### database manipulation
    def connect_db(self):
        if not self.__db_file:
            raise ReferenceError('No DB file set. Set the DB using obj.set_db(db_file) or\n' +
                                 '\tzDisplayPanel.set_db_all(db_file) first.'
                                 )

        self.__conn = sqlite3.connect(self.__db_file)
        self.__conn.text_factory = str # map TEXT to str instead of unicode

        self.__c  = self.__conn.cursor()
        self.__c.execute('''PRAGMA foreign_keys = ON''')

        # initiate the listing
        self.update_job_list()

        return self.__conn

    def disconnect_db(self):
        self.__conn.commit()
        self.__c.close()
        self.__conn.close()
        self.__c = None
        self.__conn = None

        # initiate the listing
        self.clear_job_list()

    def is_connected_db(self):
        return self.__conn != None


    def delete_jobs(self, job_pttn):
        stmt = '''DELETE
                    FROM  JOB
                   WHERE  Job_ID LIKE ?
               '''
        self.__c.execute(stmt, (job_pttn,))
        self.__conn.commit()


    def fetch_content(self, job_id, dd_pttn = '%'):
        stmt = '''SELECT  Content
                    FROM  SPOOL
                   WHERE  Job_ID = ?
                     AND  Spool_key LIKE ?
                ORDER BY  row_id
               '''
        return ''.join([ row[0] for row in self.__c.execute(stmt, (job_id, dd_pttn)) ])

    def fetch_dd_list(self, job_id):
        stmt = '''SELECT  Spool_key, Step_Name
                    FROM  SPOOL
                   WHERE  Job_ID LIKE ?
                ORDER BY  row_id
               '''
        return [ row for row in self.__c.execute(stmt, (job_id,)) ]

    def fetch_job_list(self):
        stmt = '''SELECT  Job_ID, Job_Name
                    FROM  JOB
               '''
        return [ row for row in self.__c.execute(stmt) ]


    def get_db(self):
        return self.__db_file

    def set_db(self, db_file):
        if self.__on_init:
            return              # on initializing, early return

        if zDisplayPanel._DB_FILE:
            db_file = zDisplayPanel._DB_FILE # force switch to overall setting

        if self.__db_file:
            if os.path.samefile(self.__db_file, db_file):
                return          # no need to change, early return
            else:
                self.disconnect_db()

        if db_file:
            self.__db_file = os.path.abspath(os.path.expanduser(db_file))
            self.connect_db()
        else:
            self.__db_file = None

    @staticmethod
    def set_db_all(db_file):
        if db_file:
            zDisplayPanel._DB_FILE = os.path.abspath(os.path.expanduser(db_file))
        else:
            zDisplayPanel._DB_FILE = None
    ### end of database manipulation


    def buffer_save(self, buff):
        return self.buffer_save_as(buff)

    def buffer_save_as(self, buff):
        print self.get_editor().get_last_line()


    def get_editor(self):
        return self.__editor_frame

    def set_editor(self, editor):
        self.__editor_frame = editor


    def clear_content(self):
        self.center.get_buffer().set_text('')

    def update_content(self):
        if self.__active_step:
            text = self.fetch_content(self.__active_job ,self.__active_step)
        elif self.__active_job:
            text = self.fetch_content(self.__active_job)
        else:
            text = ''
        self.center.get_buffer().set_text(text)

    def clear_job_list(self):
        self.job_panel.model.clear()
        self.__job_list = []

    def update_job_list(self):
        self.clear_job_list()

        self.__job_list = self.fetch_job_list()
        found = None
        for indx in range(len(self.__job_list)):
            job_id = self.__job_list[indx][0]

            self.job_panel.model.append([job_id])
            if self.__active_job == job_id:
                found = indx

        if found != None:
            self.job_panel.set_cursor((found,))
        else:
            self.clear_step_list()
            self.clear_content()

    def clear_step_list(self):
        self.step_panel.model.clear()
        self.__step_list = []

    def update_step_list(self):
        self.clear_step_list()

        if not self.__active_job:
            return              # no job selected, early return

        self.__step_list = self.fetch_dd_list(self.__active_job)
        for (dd_name, step_name) in self.__step_list:
            self.step_panel.model.append([dd_name])


    ### cell data function
    def __cell_data_job_name(self, column, cell, model, iterator):
        if self.is_connected_db():
            cell.set_property('text', self.__job_list[ self.job_panel.model.get_path(iterator)[-1] ][1])

    def __cell_data_step_name(self, column, cell, model, iterator):
        if self.is_connected_db():
            cell.set_property('text', self.__step_list[ self.step_panel.model.get_path(iterator)[-1] ][0])
    ### end of cell data function


    ### supporting function
    def __watch_overall_settings(self):
        '''used with `timer`'''
        if zDisplayPanel._DB_FILE:
            self.set_db(zDisplayPanel._DB_FILE)

        job_list = self.fetch_job_list()
        if job_list != self.__job_list:
            self.update_job_list()

        return True
    ### end of supporting function


######## ######## ######## ######## ########
########          zListing          ########
######## ######## ######## ######## ########

class zListing(gtk.TreeView):
    '''An intergraded gtk.TreeView Used for File Listing'''
    def __init__(self, model = None):
        super(zListing, self).__init__(model)
        self.model = self.get_model()

        self.cell_list = []
        self.column_list = []


    ### overridden function definition
    def append_column(self, column_name, cell,
                      column_xalign = None,
                      column_resizable = None, column_sizing = None
                      ):
        return self.insert_column(
            column_name, cell, -1,
            column_xalign,
            column_resizable, column_sizing
            )

    def extend_columns(self, column_name_list, cell_list, attr_list_list = None,
                       column_xalign_list = None,
                       column_resizable_list = None, column_sizing_list = None
                       ):
        n_cols = len(column_name_list)

        if not column_xalign_list:
            column_xalign_list = [None] * n_cols
        if not column_resizable_list:
            column_resizable_list = [None] * n_cols
        if not column_sizing_list:
            column_sizing_list = [None] * n_cols

        rv = None
        for indx in range(n_cols):
            rv = self.append_column(
                column_name_list[indx], cell_list[indx],
                column_xalign    = column_xalign_list[indx],
                column_resizable = column_resizable_list[indx],
                column_sizing    = column_sizing_list[indx]
                )
        return rv

    def insert_column(self, column_name, cell, position,
                      column_xalign = None,
                      column_resizable = None, column_sizing = None):
        if position < 0:
            position = len(self.column_list)
        column = gtk.TreeViewColumn(column_name, cell)

        if column_xalign != None:
            cell.set_property('xalign', column_xalign)

        if column_resizable != None:
            column.set_resizable(column_resizable)

        if column_sizing != None:
            column.set_sizing(column_sizing)

        self.cell_list.insert(position, cell)
        self.column_list.insert(position, column)

        return super(zListing, self).insert_column(column, position)

    def remove_column(self, column):
        indx = self.column_list.index(column)

        self.cell_list.pop(indx)
        self.column_list.pop(indx)

        return super(zListing, self).remove_column(column)

    def insert_column_with_attributes(self, *arg):
        raise NotImplementedError('Method not implemented. use insert_column() followed by set_attributes() instead.')
    def insert_column_with_data_func(self, *arg):
        raise NotImplementedError('Method not implemented. use insert_column() followed by set_cell_data_func() instead.')
    def set_reorderable(self, setting):
        raise NotImplementedError('Method not implemented. try to handle drag and drop manually.')


    def move_column_after(column, base_column):
        cell = self.cell_list.pop(self.column_list.index(column))
        self.column_list.remove(column)
        if not base_column:
            self.cell_list.insert(0, cell)
            self.column_list.insert(0, column)
        else:
            indx = self.column_list.index(base_column) + 1
            self.cell_list.insert(indx, cell)
            self.column_list.insert(indx, column)
            
        super(zListing, self).move_column_after(column, base_column)


    def set_model(self, model):
        super(zListing, self).set_model(model)
        self.model = model
    ### end of overridden function definition



######## ######## ######## ######## ########
########        zFileManager        ########
######## ######## ######## ######## ########

class zFileManager(gtk.VBox):
    '''A Light-Weighted File Manager Used by zEdit Class'''
    column_names     = [ '', 'Name', 'Size', 'Last Changed', ]
    column_xalign    = [  1,  0,         1,   0 ]
    column_resizable = [ False,  True, True, True ]
    column_sizing    = [
        gtk.TREE_VIEW_COLUMN_AUTOSIZE,
        gtk.TREE_VIEW_COLUMN_FIXED,
        gtk.TREE_VIEW_COLUMN_AUTOSIZE,
        gtk.TREE_VIEW_COLUMN_AUTOSIZE,
        ]

    def __init__(self, editor = None):
        '''
        editor = None
            any editor that can open an indicated file with:
              editor.set_buffer(fn_list, tpye)
            method call.
        '''
        super(zFileManager, self).__init__()


        self.__file_list = []
        self.__dir_list = []

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
        self.treeview = zListing(gtk.ListStore(str, bool))
        self.center = self.treeview
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


        # create columns
        cell_list = [
            gtk.CellRendererPixbuf(),
            gtk.CellRendererText(),
            gtk.CellRendererText(),
            gtk.CellRendererText(),
            ]

        self.treeview.extend_columns(
            zFileManager.column_names, cell_list,
            column_xalign_list    = zFileManager.column_xalign,
            column_resizable_list = zFileManager.column_resizable,
            column_sizing_list    = zFileManager.column_sizing
            )

        # init widget reference relevant to editable column (file listing)
        self.treeview.fn_cell_rdr = self.treeview.cell_list[1]
        self.treeview.fn_tree_col = self.treeview.column_list[1]

        self.treeview.fn_tree_col.set_attributes(self.treeview.fn_cell_rdr, text = 0, editable = 1)
        self.treeview.fn_tree_col.set_cell_data_func(self.treeview.fn_cell_rdr, self.__cell_data_func)


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

        # initiate the timer to watch the overall settings
        gobject.timeout_add(20, self.__watch_overall_settings)


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


    def buffer_save(self, buff):
        return buff.name, '(Cannot save this buffer)'

    def buffer_save_as(self, buff):
        return self.buffer_save(buff)


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
        self.__file_list = []
        self.__dir_list = []
        for non_hidden in [ fn for fn in os.listdir(self.dirname) if fn[0] <> '.' ]:
            fn_list = [ self.dirname, non_hidden ]
            if io_encap.is_dir(fn_list):
                self.__dir_list.append(non_hidden)
            else:
                self.__file_list.append(non_hidden)

        self.__file_list.sort(key = str.lower)
        self.__dir_list.sort(key = str.lower)
        self.__dir_list = ['..'] + self.__dir_list

        # update model with the listing
        self.treeview.model.clear()
        for fn in self.__dir_list:
            self.treeview.model.append([fn, False])
        for fn in self.__file_list:
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


    ### supporting function
    def __watch_overall_settings(self):
        '''used with `timer`'''
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

        if file_list != self.__file_list or dir_list != self.__dir_list:
            self.refresh_folder()

        return True
    ### end of supporting function
