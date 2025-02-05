# encoding: utf-8

"""|Document| and closely related objects"""

from __future__ import absolute_import, division, print_function, unicode_literals

from docx.oxml.ns import qn

from docx.blkcntnr import BlockItemContainer
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_BREAK
from docx.section import Section, Sections
from docx.shared import ElementProxy, Emu


class Document(ElementProxy):
    """WordprocessingML (WML) document.

    Not intended to be constructed directly. Use :func:`docx.Document` to open or create
    a document.
    """

    __slots__ = ('_part', '__body')

    def __init__(self, element, part, fudge_markers = False):
        super(Document, self).__init__(element)
        self._part = part
        self.__body = None
        if fudge_markers: self.fudge_list_markers()

    def add_heading(self, text="", level=1):
        """Return a heading paragraph newly added to the end of the document.

        The heading paragraph will contain *text* and have its paragraph style
        determined by *level*. If *level* is 0, the style is set to `Title`. If *level*
        is 1 (or omitted), `Heading 1` is used. Otherwise the style is set to `Heading
        {level}`. Raises |ValueError| if *level* is outside the range 0-9.
        """
        if not 0 <= level <= 9:
            raise ValueError("level must be in range 0-9, got %d" % level)
        style = "Title" if level == 0 else "Heading %d" % level
        return self.add_paragraph(text, style)

    def add_page_break(self):
        """Return newly |Paragraph| object containing only a page break."""
        paragraph = self.add_paragraph()
        paragraph.add_run().add_break(WD_BREAK.PAGE)
        return paragraph

    def add_paragraph(self, text='', style=None):
        """
        Return a paragraph newly added to the end of the document, populated
        with *text* and having paragraph style *style*. *text* can contain
        tab (``\\t``) characters, which are converted to the appropriate XML
        form for a tab. *text* can also include newline (``\\n``) or carriage
        return (``\\r``) characters, each of which is converted to a line
        break.
        """
        return self._body.add_paragraph(text, style)

    def add_picture(self, image_path_or_stream, width=None, height=None):
        """
        Return a new picture shape added in its own paragraph at the end of
        the document. The picture contains the image at
        *image_path_or_stream*, scaled based on *width* and *height*. If
        neither width nor height is specified, the picture appears at its
        native size. If only one is specified, it is used to compute
        a scaling factor that is then applied to the unspecified dimension,
        preserving the aspect ratio of the image. The native size of the
        picture is calculated using the dots-per-inch (dpi) value specified
        in the image file, defaulting to 72 dpi if no value is specified, as
        is often the case.
        """
        run = self.add_paragraph().add_run()
        return run.add_picture(image_path_or_stream, width, height)

    def add_section(self, start_type=WD_SECTION.NEW_PAGE):
        """
        Return a |Section| object representing a new section added at the end
        of the document. The optional *start_type* argument must be a member
        of the :ref:`WdSectionStart` enumeration, and defaults to
        ``WD_SECTION.NEW_PAGE`` if not provided.
        """
        new_sectPr = self._element.body.add_section_break()
        new_sectPr.start_type = start_type
        return Section(new_sectPr, self._part)

    def add_table(self, rows, cols, style=None):
        """
        Add a table having row and column counts of *rows* and *cols*
        respectively and table style of *style*. *style* may be a paragraph
        style object or a paragraph style name. If *style* is |None|, the
        table inherits the default table style of the document.
        """
        table = self._body.add_table(rows, cols, self._block_width)
        table.style = style
        return table

    def fudge_list_markers(self):
        """
        Create fake list markers and overwrite paragraphs with list markers 
        that are list markers. 
        """
        
        # dig up id of enumeration and indentation level for each paragraph 
        # (iff relevant)
        paras_numPr = [p._element.xpath(".//w:numPr") 
                       for p in self.paragraphs]
        try:
            get = lambda pth, x: x.xpath(pth)[0].attrib.values()[0]
            para_num_groups = [(get(".//w:numId",p[0]),
                                get(".//w:ilvl",p[0])) if p 
                               else None 
                               for p in paras_numPr]
        except:
            # Abort silently.
            #self.fudge_status = "Aborted at search for numIds."
            return
        
        # Generate a surface representation of each enumeration, at each
        # point in that enumeration.
        enumerations = {}
        para_nums = []
        for g in para_num_groups:
            if g is None: 
                para_nums.append(None)
                continue

            # retain the enumeration for future groups
            if g in enumerations: enumerations[g] += 1 
            else: enumerations[g] = 1
            
            # TODO: integrate enumeration types (digital, alpha, roman, etc.)
            # from style file
            para_nums.append(unicode(enumerations[g]))
        
        #print zip(paras_numPr,para_num_groups,para_nums)
        
        #self.fudge_freq += len([n for n in para_nums if n is not None])

        # Overwrite the existing representation of the text in 
        for par,num in zip(self.paragraphs,para_nums):
            if num is None: continue
            #print(num, par.text)
            par.text = " ".join([num+")",
                                 "" if par.text is None else par.text])

    def add_comment(self, start_run, end_run,
                    author,
                    dtime,
                    comment_text,
                    initials=None):
        """Add comment spanning over one or more runs.

        Args:
            start_run: |CT_Run| instance, first run in comment
            author: (str) Comment author
            end_run: |CT_Run| instance, last run in comment.
            dtime: (str) Date and Time of comment, use
                str(datetime.datetime.now())
            comment_text: (str) Text body of comment
            initials: (str) Comment author initials. If None, determined with a
                heuristic from `author` variable
        Returns:
            Comment object
        """
        if initials is None:
            # Upper: use upper-case chars to determine initials
            # 'BlackBoiler' --> 'BB'
            # 'Ryan Mannion' --> 'RM'
            # 'ryan mannion' --> ''
            def upper(n): return "".join([c for c in n if c.isupper()])
            # Splitter: split name and use first chars to determine initials
            # ryan mannion --> RM
            # ryan --> R
            def splitter(n): return "".join([t[0] for t in n.split(" ")]).upper()

            initials = upper(author)
            if initials == '':
                initials = splitter(author)

        comment_part_element = self.comments_part.element
        comment = comment_part_element.add_comment(author, initials, dtime)
        comment._add_p(comment_text)
        start_run.mark_comment_start(comment._id)
        end_run.mark_comment_end(comment._id)

        return comment


    @property
    def core_properties(self):
        """
        A |CoreProperties| object providing read/write access to the core
        properties of this document.
        """
        return self._part.core_properties

    @property
    def comments_part(self):
        """
        A |Comments| object providing read/write access to the core
        properties of this document.
        """
        return self.part.comments_part
    
    # @property
    # def footnotes_part(self):
    #     """
    #     A |Footnotes| object providing read/write access to the core
    #     properties of this document.
    #     """
    #     return self.part._footnotes_part


    @property
    def inline_shapes(self):
        """
        An |InlineShapes| object providing access to the inline shapes in
        this document. An inline shape is a graphical object, such as
        a picture, contained in a run of text and behaving like a character
        glyph, being flowed like other text in a paragraph.
        """
        return self._part.inline_shapes

    @property
    def paragraphs(self):
        """
        A list of |Paragraph| instances corresponding to the paragraphs in
        the document, in document order. Note that paragraphs within revision
        marks such as ``<w:ins>`` or ``<w:del>`` do not appear in this list.
        """
        return self._body.paragraphs

    @property
    def part(self):
        """
        The |DocumentPart| object of this document.
        """
        return self._part

    def save(self, path_or_stream):
        """
        Save this document to *path_or_stream*, which can be either a path to
        a filesystem location (a string) or a file-like object.
        """
        self._part.save(path_or_stream)

    @property
    def sections(self):
        """|Sections| object providing access to each section in this document."""
        return Sections(self._element, self._part)

    @property
    def settings(self):
        """
        A |Settings| object providing access to the document-level settings
        for this document.
        """
        return self._part.settings

    @property
    def styles(self):
        """
        A |Styles| object providing access to the styles in this document.
        """
        return self._part.styles

    @property
    def tables(self):
        """
        A list of |Table| instances corresponding to the tables in the
        document, in document order. Note that only tables appearing at the
        top level of the document appear in this list; a table nested inside
        a table cell does not appear. A table within revision marks such as
        ``<w:ins>`` or ``<w:del>`` will also not appear in the list.
        """
        return self._body.tables

    @property
    def elements(self):
        return self._body.elements
    
    @property
    def abstractNumIds(self):
        """
        Returns list of all the 'w:abstarctNumId' of this document
        """
        return self._body.abstractNumIds
    
    @property
    def last_abs_num(self):
        last = self.abstractNumIds[-1]
        val = last.attrib.get(qn('w:abstractNumId'))
        return  last, val
    
    @property
    def _block_width(self):
        """
        Return a |Length| object specifying the width of available "writing"
        space between the margins of the last section of this document.
        """
        section = self.sections[-1]
        return Emu(
            section.page_width - section.left_margin - section.right_margin
        )

    @property
    def _body(self):
        """
        The |_Body| instance containing the content for this document.
        """
        if self.__body is None:
            self.__body = _Body(self._element.body, self)
        return self.__body


class _Body(BlockItemContainer):
    """
    Proxy for ``<w:body>`` element in this document, having primarily a
    container role.
    """
    def __init__(self, body_elm, parent):
        super(_Body, self).__init__(body_elm, parent)
        self._body = body_elm

    def clear_content(self):
        """
        Return this |_Body| instance after clearing it of all content.
        Section properties for the main document story, if present, are
        preserved.
        """
        self._body.clear_content()
        return self
