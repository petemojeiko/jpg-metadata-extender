'''The JPEG METADATA EXTENDER module provides a GUI built with Tkinter
that accepts user input regarding a set of JPEG images, and on execution
will apply the user input and JPEG-specific EXIF data in an XML
file for each image

AUTHOR =  Pete Mojeiko
EMAIL =   petemojeiko@gmail.com
TWITTER = @ifthisthenbreak
'''

__version__ = '0.1'

from Tkinter import *
import tkFileDialog as tkF

import os
import glob
import pickle
from collections import OrderedDict
from time import localtime, strftime

import xml.etree.ElementTree as ET
from PIL import Image
import ExifTags


class App(Frame):
    '''The GUI class. Builds the interface and manages functions up to the
    execution of the metadata generator class'''
    
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent

        self.execute_frame = Frame(self)
        self.directory_frame = Frame(self)
        self.photographer_field_frame = Frame(self, bd=2, relief=GROOVE)
        self.client_field_frame = Frame(self, bd=2, relief=GROOVE)
        self.block_frame = Frame(self, bd=2, relief=GROOVE)
        
        self.directory_frame.grid(row=1, column=0, columnspan=2, sticky=NSEW, ipadx=2, ipady=2)
        self.execute_frame.grid(row=2, column=0, columnspan=2, sticky=NSEW, ipadx=2, ipady=2)
        self.photographer_field_frame.grid(row=0, column=0, sticky=N, ipadx=2, ipady=2)
        self.client_field_frame.grid(row=0, column=1, sticky=N, ipadx=2, ipady=2)
        self.block_frame.grid(row=0, column=2, rowspan=3, sticky=NSEW, ipadx=2, ipady=2)

        self.rowconfigure(0, weight=1)
        self.columnconfigure(2, weight=1)
        
        self.state = 'unsaved'

        self._init_menu()
        self._init_fields()

        for widget in self._widget_fields().values():
            widget.bind('<FocusIn>', self._field_highlighter)
            widget.bind('<FocusOut>', self._drop_highlighter)

    def _init_menu(self):
        self.menubar = Menu(self)

        self.filemenu = Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label='New Template', command=self._new)
        self.filemenu.add_command(label='Open...', command=self._open)
        self.filemenu.add_command(label='Save', command=self._save)
        self.filemenu.add_command(label='Save as...', command=self._save_as)
        self.filemenu.add_separator()
        self.filemenu.add_command(label='Exit', command=self.parent.destroy)
        self.menubar.add_cascade(label='File', menu=self.filemenu)

        self.helpmenu = Menu(self.menubar, tearoff=0)
        self.helpmenu.add_command(label='Help', command=self._help)
        self.helpmenu.add_separator()
        self.helpmenu.add_command(label='About', command=self._about)
        self.menubar.add_cascade(label='Help', menu=self.helpmenu)

        self.parent.config(menu=self.menubar)

    def _init_fields(self):
        '''Creates all widgets and initializes dictionaries to hold
        user-input metadata values'''
        self.photographer_fields = OrderedDict.fromkeys(['p_Organization','p_Name','p_Address','p_City','p_State','p_Zip','p_Phone','p_Email'])
        self.client_fields = OrderedDict.fromkeys(['c_Organization','c_Name','c_Address','c_City','c_State','c_Zip','c_Phone','c_Email'])
        self.text_blocks = OrderedDict.fromkeys(['Abstract','Process'])

        # Photographer Information Fields
        photographer_inner = Frame(self.photographer_field_frame)
        photographer_inner.grid(row=0, column=0, columnspan=2, sticky=W)
        self.photographer_field_toggle = BooleanVar()
        self.photographer_field_toggle.set(True)
        row = 1
        for field in self.photographer_fields:
            Label(self.photographer_field_frame, text=field[2:] + ':').grid(row=row, column=0, sticky=W)
            self.photographer_fields[field] = Entry(self.photographer_field_frame, font=('Courier', 10))
            self.photographer_fields[field].grid(row=row, column=1)
            row += 1
        Checkbutton(photographer_inner, text='Photographer:', variable=self.photographer_field_toggle,
                    command=lambda: self._disable_fields('photographer_fields')).pack()
        
        # Client Information Fields
        client_inner = Frame(self.client_field_frame)
        client_inner.grid(row=0, column=0, columnspan=2, sticky=W)
        self.client_field_toggle = BooleanVar()
        self.client_field_toggle.set(True)
        row = 1
        for field in self.client_fields:
            Label(self.client_field_frame, text=field[2:] + ':').grid(row=row, column=0, sticky=W)
            self.client_fields[field] = Entry(self.client_field_frame, font=('Courier', 10))
            self.client_fields[field].grid(row=row, column=1)
            row += 1
        Checkbutton(client_inner, text='Client:', variable=self.client_field_toggle,
                    command=lambda: self._disable_fields('client_fields')).pack()

        # Abstract and Process Step Text Blocks
        self.abstract_toggle = BooleanVar()
        self.process_toggle = BooleanVar()
        self.abstract_toggle.set(True)
        self.process_toggle.set(True)
        abstract_check = Checkbutton(self.block_frame, text='Abstract:', variable=self.abstract_toggle,
                                     command=lambda: self._disable_fields('abstract'))
        process_check = Checkbutton(self.block_frame, text='Process Steps:', variable=self.process_toggle,
                                    command=lambda: self._disable_fields('process'))
        abstract_check.grid(row=0, column=0, sticky=W)
        process_check.grid(row=2, column=0, sticky=W)
        row = 1
        for field in self.text_blocks:
            self.text_blocks[field] = Text(self.block_frame, width=52, height=7, font=('Courier', 10), wrap=WORD)
            self.text_blocks[field].grid(row=row, column=0, sticky=NSEW)
            text_scroller = Scrollbar(self.block_frame)
            text_scroller.grid(row=row, column=1, sticky=NS)
            self.text_blocks[field].config(yscrollcommand=text_scroller.set)
            text_scroller.config(command=self.text_blocks[field].yview)
            row += 2
        self.block_frame.columnconfigure(0, weight=1)
        self.block_frame.rowconfigure(1, weight=1)
        self.block_frame.rowconfigure(3, weight=1)

        # JPG Directory Widgets
        Label(self.directory_frame, text='Image Directory:').grid(row=0, column=0, columnspan=2, sticky=W)
        Button(self.directory_frame, text='>>>', font=('Courier', 8), command=self._select_directory).grid(row=1, column=0)
        self.image_directory = Entry(self.directory_frame, width=30)
        self.image_directory.grid(row=1, column=1, sticky=EW)
        self.image_directory.bind('<FocusIn>', self._field_highlighter)
        self.image_directory.bind('<FocusOut>', self._drop_highlighter)
        self.directory_frame.columnconfigure(1, weight=1)
        self.image_count = Label(self.directory_frame, text=' ')
        self.image_count.grid(row=2, column=0, columnspan=2, sticky=E)

        # Execute Button
        Button(self.execute_frame, text='Create Metadata', command=self._execute_metadata).pack()
            
    def _field_highlighter(self, event):
        event.widget.config(bg='lemon chiffon')

    def _drop_highlighter(self, event):
        event.widget.config(bg='white')

    def _select_directory(self):
        try:
            directory = tkF.askdirectory(parent=self.parent, mustexist=1, title='Select Image Directory')
            self.image_directory.delete(0, END)
            self.image_directory.insert(0, directory)
            images = len(glob.glob(os.path.join(directory, '*.jpg')))
            self.image_count.config(text=str(images) + ' JPG images found in directory.')
        except IOError:
            return

    def _disable_fields(self, fields):
        '''Sets Entry and Text states to normal or disabled on Checkbutton toggle'''
        widget_fields = self._widget_fields()
        if fields == 'photographer_fields':
            for k,v in widget_fields.iteritems():
                if k.startswith('p_') and self.photographer_field_toggle.get():
                    v.config(state=NORMAL)
                elif k.startswith('p_'):
                    v.config(state=DISABLED)
        if fields == 'client_fields':
            for k,v in widget_fields.iteritems():
                if k.startswith('c_') and self.client_field_toggle.get():
                    v.config(state=NORMAL)
                elif k.startswith('c_'):
                    v.config(state=DISABLED)
        if fields == 'abstract':
            for k,v in widget_fields.iteritems():
                if k == 'Abstract' and self.abstract_toggle.get():
                    print 0
                    v.config(state=NORMAL, bg='white')
                elif k == 'Abstract':
                    print 1
                    v.config(state=DISABLED, bg='gray93')
        if fields == 'process':
            for k,v in widget_fields.iteritems():
                if k == 'Process' and self.process_toggle.get():
                    v.config(state=NORMAL, bg='white')
                elif k == 'Process':
                    v.config(state=DISABLED, bg='gray93')

    def _value_fields(self):
        '''Returns a dict of the values from the Entry and Text widgets'''
        fields = OrderedDict()
        fields_list = []
        if self.photographer_field_toggle.get():
            fields_list.append(self.photographer_fields)
        if self.client_field_toggle.get():
            fields_list.append(self.client_fields)
        if self.abstract_toggle.get():
            fields['Abstract'] = self.text_blocks['Abstract']
        if self.process_toggle.get():
            fields['Process'] = self.text_blocks['Process']
        
        for d in fields_list:
            for k,v in d.iteritems():
                fields.setdefault(k,v)
        
        for k,v in fields.iteritems():
            if v.winfo_class() == 'Entry':
                fields[k] = v.get()
            if v.winfo_class() == 'Text':
                fields[k] = v.get(1.0, 'end-1c')
        return fields

    def _widget_fields(self):
        '''Returns a dict of the instances of the Entry and Text widgets'''
        fields = {}

        fields['Abstract'] = self.text_blocks['Abstract']
        fields['Process'] = self.text_blocks['Process']
        
        for d in [self.photographer_fields, self.client_fields]:
            for k,v in d.iteritems():
                fields.setdefault(k,v)
        
        return fields

    def _save(self):
        if self.state == 'unsaved':
            self._save_as()
        else:
            pickle.dump(self._value_fields(), open(self.save_file, 'wb'))

    def _save_as(self):
        try:
            self.save_file = tkF.asksaveasfilename(defaultextension='.txt',
                                                   filetypes=[('Metadata Configure File', '.txt')],
                                                   parent=self.parent, title='Save Configuration File As...')
            self.state = 'saved'
            self._save()
        except IOError:
            return

    def _new(self):
        if self.state == 'unsaved':
            pass # TO-DO: popup confirm
        for widget in self._widget_fields().values():
            widget.config(state=NORMAL, bg='white')
            if widget.winfo_class() == 'Entry':
                widget.delete(0, END)
            elif widget.winfo_class() == 'Text':
                widget.delete(1.0, END)
        for toggle in [self.photographer_field_toggle, self.client_field_toggle,
                       self.abstract_toggle, self.process_toggle]:
            toggle.set(True)
        self.state = 'unsaved'
        self.save_file = None

    def _open(self):
        try:
            open_file = tkF.askopenfilename(defaultextension='.txt',
                                            filetypes=[('Metadata Configure File', '*.txt')],
                                            parent=self.parent, title='Open Configuration File...')
            raw_fields = pickle.load(open(open_file, 'rb'))
            for k,v in raw_fields.iteritems():
                if k.startswith('p_'):
                    self.photographer_fields[k].delete(0, END)
                    self.photographer_fields[k].insert(0, v)
                elif k.startswith('c_'):
                    self.client_fields[k].delete(0, END)
                    self.client_fields[k].insert(0, v)
                elif k == 'Abstract':
                    self.text_blocks['Abstract'].delete(1.0, END)
                    self.text_blocks['Abstract'].insert(1.0, v)
                elif k == 'Process':
                    self.text_blocks['Process'].delete(1.0, END)
                    self.text_blocks['Process'].insert(1.0, v)
            self.save_file = open_file
        except IOError:
            return

    def _help(self):
        help_window = Toplevel(self)
        Label(help_window, text='HELP', font=('Courier', 12)).pack(anchor=W)
        help_content = '''Enter values into the fields for Photographer
information, client information, abstract (description of photo set)
and process steps. Sections can be turned on or off.

Select the directory containing the JPEG photo set and click "Create
Metadata" to execute the tool. An XML file will be generated for
each photo, which will contain the data entered about the photo set
and image-specific data extracted from each JPEG (EXIF data).
        '''
        text = Text(help_window, width=70, height=10, wrap=WORD)
        text.pack()
        text.insert(1.0, help_content.strip('\n'))
        text.config(state=DISABLED)
        
    def _about(self):
        about_window = Toplevel(self)
        Label(about_window, text='ABOUT', font=('Courier', 12)).pack(anchor=W)
        Label(about_window, text='JPEG Metadata Extender').pack()
        Label(about_window, text='Version: ' + __version__).pack()
        Label(about_window, text='Author: Pete Mojeiko').pack()
        Label(about_window, text='Email: petemojeiko@gmail.com').pack()
        Label(about_window, text='Twitter: @ifthisthenbreak').pack()

    def _execute_metadata(self):
        '''Gathers critical args for the MetadataGenerator and creates an instance
        of it'''
        image_paths = glob.glob(os.path.join(self.image_directory.get(), '*.jpg'))
        images = [os.path.basename(i) for i in image_paths]
        field_toggles = {'photographer_field_toggle': self.photographer_field_toggle.get(),
                         'client_field_toggle': self.client_field_toggle.get(),
                         'abstract_toggle': self.abstract_toggle.get(),
                         'process_toggle': self.process_toggle.get()}
        if len(images) == 0:
            # TO-DO: popup message
            return
        else:
            MetadataGenerator(self.image_directory.get(), images, self._value_fields(), field_toggles)


class MetadataGenerator():
    '''Back-end processes that handle the generation of XML files'''

    def __init__(self, image_directory, images, value_fields, toggles):
        self.image_directory = image_directory
        self.images = images
        self.value_fields = value_fields
        self.toggles = toggles

        for image in self.images:
            with open(os.path.join(self.image_directory, image)) as image_instance:
                self._create_metadata(image, image_instance)

    def _create_metadata(self, image, image_instance):
        '''Writes an XML file for image'''
        
        root = ET.Element('image')
        
        header = ET.SubElement(root, 'header')
        name = ET.SubElement(header, 'image-name')
        date = ET.SubElement(header, 'pubdate')
        name.text = image
        date.text = strftime('%m%d%Y', localtime())
        
        self.exif = ET.SubElement(root, 'exif')
        self._exif_element(image)
        
        if self.toggles['photographer_field_toggle']:
            self.photographer = ET.SubElement(root, 'photographer')
            self._photographer_element()
            
        if self.toggles['client_field_toggle']:
            self.client = ET.SubElement(root, 'client')
            self._client_element()
            
        if self.toggles['abstract_toggle']:
            self.abstract = ET.SubElement(root, 'abstract')
            self._abstract_element()
            
        if self.toggles['process_toggle']:
            self.process = ET.SubElement(root, 'process-steps')
            self._process_element()

        tree = ET.ElementTree(root)
        # ET.dump(tree) # prints out tree
        tree.write(os.path.join(self.image_directory, image[:-4] + '.xml'))

    def _exif_element(self, image):
        '''Extracts EXIF data to dictionary and inserts k,v pairs
        as SubElements and text attributes'''
        image = Image.open(os.path.join(self.image_directory, image))
        exif_data = {ExifTags.TAGS[k]: v                  # format exif
                     for k, v in image._getexif().items() # data to dict
                     if k in ExifTags.TAGS}

        for k,v in exif_data.iteritems():
            if type(v) == dict: # exclude dicts as values
                pass
            elif type(v) == str and v.find('\\'): # exclude byte strings as values
                pass                              # TO-DO: interpret byte strings
            else:
                k = ET.SubElement(self.exif, k)
                k.text = str(v)

    def _photographer_element(self):
        for k,v in self.value_fields.iteritems():
            if k.startswith('p_'):
                k = ET.SubElement(self.photographer, k)
                k.text = str(v)

    def _client_element(self):
        for k,v in self.value_fields.iteritems():
            if k.startswith('c_'):
                k = ET.SubElement(self.client, k)
                k.text = str(v)
                
    def _abstract_element(self):
        for k,v in self.value_fields.iteritems():
            if k == 'Abstract':
                k = ET.SubElement(self.abstract, k)
                k.text = str(v)

    def _process_element(self):
        for k,v in self.value_fields.iteritems():
            if k == 'Process':
                k = ET.SubElement(self.process, k)
                k.text = str(v)

def main():
    root = Tk()
    root.title('JPEG Metadata Extender')
    app = App(root)
    app.pack(fill=BOTH, expand=1)
    root.mainloop()

if __name__ == '__main__':
    main()
