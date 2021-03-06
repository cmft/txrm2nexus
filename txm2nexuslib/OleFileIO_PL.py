



 
"""-----------------------------------------------------------------------"""   
""" The following class is used to open Microsoft Structured Storage files"""
#--- LICENSE ------------------------------------------------------------------

# OleFileIO_PL is an improved version of the OleFileIO module from the
# Python Imaging Library (PIL).

# OleFileIO_PL changes are Copyright (c) 2005-2010 by Philippe Lagadec
#
# The Python Imaging Library (PIL) is
#    Copyright (c) 1997-2005 by Secret Labs AB
#    Copyright (c) 1995-2005 by Fredrik Lundh
#


#------------------------------------------------------------------------------

import string, StringIO, struct, array, os.path, sys

#[PL] workaround to fix an issue with array item size on 64 bits systems:
if array.array('L').itemsize == 4:
    # on 32 bits platforms, long integers in an array are 32 bits:
    UINT32 = 'L'
elif array.array('I').itemsize == 4:
    # on 64 bits platforms, integers in an array are 32 bits:
    UINT32 = 'I'
else:
    raise ValueError, 'Need to fix a bug with 32 bit arrays, please contact author...'



# Experimental setting: if True, OLE filenames will be kept in Unicode
# if False (default PIL behaviour), all filenames are converted to Latin-1.
KEEP_UNICODE_NAMES = True

# DEBUG display mode: False by default, use set_debug_mode() or "-d" on
# command line to change it.
DEBUG_MODE = False


MAGIC = '\320\317\021\340\241\261\032\341'

# added constants for Sector IDs (from AAF specifications)
MAXREGSECT = 0xFFFFFFFAL; # maximum SECT
DIFSECT    = 0xFFFFFFFCL; # (-4) denotes a DIFAT sector in a FAT
FATSECT    = 0xFFFFFFFDL; # (-3) denotes a FAT sector in a FAT
ENDOFCHAIN = 0xFFFFFFFEL; # (-2) end of a virtual stream chain
FREESECT   = 0xFFFFFFFFL; # (-1) unallocated sector

#[PL]: added constants for Directory Entry IDs (from AAF specifications)
MAXREGSID  = 0xFFFFFFFAL; # maximum directory entry ID
NOSTREAM   = 0xFFFFFFFFL; # (-1) unallocated directory entry

#[PL] object types in storage (from AAF specifications)
STGTY_EMPTY     = 0 # empty directory entry (according to OpenOffice.org doc)
STGTY_STORAGE   = 1 # element is a storage object
STGTY_STREAM    = 2 # element is a stream object
STGTY_LOCKBYTES = 3 # element is an ILockBytes object
STGTY_PROPERTY  = 4 # element is an IPropertyStorage object
STGTY_ROOT      = 5 # element is a root storage


#
# --------------------------------------------------------------------
# property types

VT_EMPTY=0; VT_NULL=1; VT_I2=2; VT_I4=3; VT_R4=4; VT_R8=5; VT_CY=6;
VT_DATE=7; VT_BSTR=8; VT_DISPATCH=9; VT_ERROR=10; VT_BOOL=11;
VT_VARIANT=12; VT_UNKNOWN=13; VT_DECIMAL=14; VT_I1=16; VT_UI1=17;
VT_UI2=18; VT_UI4=19; VT_I8=20; VT_UI8=21; VT_INT=22; VT_UINT=23;
VT_VOID=24; VT_HRESULT=25; VT_PTR=26; VT_SAFEARRAY=27; VT_CARRAY=28;
VT_USERDEFINED=29; VT_LPSTR=30; VT_LPWSTR=31; VT_FILETIME=64;
VT_BLOB=65; VT_STREAM=66; VT_STORAGE=67; VT_STREAMED_OBJECT=68;
VT_STORED_OBJECT=69; VT_BLOB_OBJECT=70; VT_CF=71; VT_CLSID=72;
VT_VECTOR=0x1000;

# map property id to name (for debugging purposes)

VT = {}
for keyword, var in vars().items():
    if keyword[:3] == "VT_":
        VT[var] = keyword

#
# --------------------------------------------------------------------


#Defect levels to classify parsing errors - see OleFileIO._raise_defect()
DEFECT_UNSURE =    10    # a case which looks weird, but not sure it's a defect
DEFECT_POTENTIAL = 20    # a potential defect
DEFECT_INCORRECT = 30    # an error according to specifications, but parsing
                         # can go on
DEFECT_FATAL =     40    # an error which cannot be ignored, parsing is
                         # impossible


#--- FUNCTIONS ----------------------------------------------------------------

def isOleFile (filename):
    """
    Test if file is an OLE container (according to its header).
    filename: file name or path (str, unicode)
    return: True if OLE, False otherwise.
    """
    f = open(filename, 'rb')
    header = f.read(len(MAGIC))
    if header == MAGIC:
        return True
    else:
        return False


def i16(c, o = 0):
    """
    Converts a 2-bytes (16 bits) string to an integer.

    c: string containing bytes to convert
    o: offset of bytes to convert in string
    """
    return ord(c[o])+(ord(c[o+1])<<8)


def i32(c, o = 0):
    """
    Converts a 4-bytes (32 bits) string to an integer.

    c: string containing bytes to convert
    o: offset of bytes to convert in string
    """
    return int(ord(c[o])+(ord(c[o+1])<<8)+(ord(c[o+2])<<16)+(ord(c[o+3])<<24))
    # [PL]: added int() because "<<" gives long int since Python 2.4


def _clsid(clsid):
    """
    Converts a CLSID to a human-readable string.
    clsid: string of length 16.
    """
    assert len(clsid) == 16
    if clsid == "\0" * len(clsid):
        return ""
    return (("%08X-%04X-%04X-%02X%02X-" + "%02X" * 6) %
            ((i32(clsid, 0), i16(clsid, 4), i16(clsid, 6)) +
            tuple(map(ord, clsid[8:16]))))



# UNICODE support for Old Python versions:
# (necessary to handle storages/streams names which use Unicode)

try:
    # is Unicode supported ?
    unicode

    def _unicode(s, errors='replace'):
        """
        Map unicode string to Latin 1. (Python with Unicode support)

        s: UTF-16LE unicode string to convert to Latin-1
        errors: 'replace', 'ignore' or 'strict'. See Python doc for unicode()
        """
        try:
            # First the string is converted to plain Unicode:
            # (assuming it is encoded as UTF-16 little-endian)
            print "unicode s.decode"
            u = s.decode('UTF-16LE', errors)
            if KEEP_UNICODE_NAMES:
                return u
            else:
                
                # Second the unicode string is converted to Latin-1
                return u.encode('latin_1', errors)
        except:
            # there was an error during Unicode to Latin-1 conversion:
            raise IOError, 'incorrect Unicode name'

except NameError:
    def _unicode(s, errors='replace'):
        """
        Map unicode string to Latin 1. (Python without native Unicode support)

        s: UTF-16LE unicode string to convert to Latin-1
        errors: 'replace', 'ignore' or 'strict'. (ignored in this version)
        """
        print "unicode filter"
        # If the unicode function does not exist, we assume this is an old
        # Python version without Unicode support.
        # Null bytes are simply removed (this only works with usual Latin-1
        # strings which do not contain unicode characters>256):
        return filter(ord, s)



        
        

#=== CLASSES ==================================================================

#--- _OleStream ---------------------------------------------------------------

class _OleStream(StringIO.StringIO):
    """
    OLE2 Stream

    Returns a read-only file object which can be used to read
    the contents of a OLE stream (instance of the StringIO class).
    To open a stream, use the openstream method in the OleFile class.

    This function can be used with either ordinary streams,
    or ministreams, depending on the offset, sectorsize, and
    fat table arguments.

    Attributes:
        - size: actual size of data stream, after it was opened.
    """


    def __init__(self, fp, sect, size, offset, sectorsize, fat):
        """
        Constructor for _OleStream class.

        fp        : file object, the OLE container or the MiniFAT stream
        sect      : sector index of first sector in the stream
        size      : total size of the stream
        offset    : offset in bytes for the first FAT or MiniFAT sector
        sectorsize: size of one sector
        fat       : array/list of sector indexes (FAT or MiniFAT)
        return    : a StringIO instance containing the OLE stream
        """
        if DEBUG_MODE:
            print '_OleStream.__init__:\n'
            print '  sect=%d (%X), size=%d, offset=%d, sectorsize=%d, len(fat)=%d, fp=%s \n\n' %(sect,sect,size,offset,sectorsize,len(fat), repr(fp))
        # for debugging messages, size of file where stream is read:
        if isinstance(fp, StringIO.StringIO):
            filesize = len(fp.getvalue())   # file in MiniFAT
        else:
            filesize = os.path.getsize(fp.name) # file on disk
        #[PL] To detect malformed documents with FAT loops, we compute the
        # expected number of sectors in the stream:
        unknown_size = False
        if size==0x7FFFFFFF:
            # this is the case when called from OleFileIO._open(), and stream
            # size is not known in advance (for example when reading the
            # Directory stream). Then we can only guess maximum size:
            size = len(fat)*sectorsize
            # and we keep a record that size was unknown:
            unknown_size = True
            if DEBUG_MODE: print '  stream with UNKNOWN SIZE'
        nb_sectors = (size + (sectorsize-1)) / sectorsize
        #print 'nb_sectors = %d' % nb_sectors
        # This number should (at least) be less than the total number of
        # sectors in the given FAT:
        if nb_sectors > len(fat):
            raise IOError, 'malformed OLE document, stream too large'
        # optimization(?): data is first a list of strings, and join() is called
        # at the end to concatenate all in one string.
        # (this may not be really useful with recent Python versions)
        data = []
        # if size is zero, then first sector index should be ENDOFCHAIN:
        if size == 0 and sect != ENDOFCHAIN:
            if DEBUG_MODE:
                print 'size == 0 and sect != ENDOFCHAIN:'
            raise IOError, 'incorrect OLE sector index for empty stream'
        #[ A fixed-length for loop is used instead of an undefined while
        # loop to avoid DoS attacks:
        for i in xrange(nb_sectors):
            # Sector index may be ENDOFCHAIN, but only if size was unknown
            if sect == ENDOFCHAIN:
                if unknown_size:
                    break
                else:
                    # else this means that the stream is smaller than declared:
                    if DEBUG_MODE:
                        print 'sect=ENDOFCHAIN before expected size'
                    raise IOError, 'incomplete OLE stream'
            # sector index should be within FAT:
            if sect<0 or sect>=len(fat):
                if DEBUG_MODE:
                    print 'sect=%d (%X) / len(fat)=%d' % (sect, sect, len(fat))
                    print 'i=%d / nb_sectors=%d' %(i, nb_sectors)

                raise IOError, 'incorrect OLE FAT, sector index out of range'

            try:
                fp.seek(offset + sectorsize * sect)
            except:
                if DEBUG_MODE:
                    print 'sect=%d, seek=%d, filesize=%d' % (sect, offset+sectorsize*sect, filesize)
                raise IOError, 'OLE sector index out of range'
            sector_data = fp.read(sectorsize)
            # [PL] check if there was enough data:
            # Note: if sector is the last of the file, sometimes it is not a
            # complete sector (of 512 or 4K), so we may read less than
            # sectorsize.
            if len(sector_data)!=sectorsize and sect!=(len(fat)-1):
                if DEBUG_MODE:
                    print 'sect=%d / len(fat)=%d, seek=%d / filesize=%d, len read=%d' % (sect, len(fat), offset+sectorsize*sect, filesize, len(sector_data))
                    print 'seek+len(read)=%d' % (offset+sectorsize*sect+len(sector_data))
                raise IOError, 'incomplete OLE sector'
            data.append(sector_data)
            # jump to next sector in the FAT:
            try:
                sect = fat[sect]
            except IndexError:
                #  if pointer is out of the FAT an exception is raised
                raise IOError, 'incorrect OLE FAT, sector index out of range'
        # Last sector should be a "end of chain" marker:
        if sect != ENDOFCHAIN:
            raise IOError, 'incorrect last sector index in OLE stream'
        data = string.join(data, "")
        # Data is truncated to the actual stream size:
        if len(data) >= size:
            data = data[:size]
            # actual stream size is stored for future use:
            self.size = size
        elif unknown_size:
            # actual stream size was not known, now we know the size of read
            # data:
            self.size = len(data)
        else:
            # read data is less than expected:
            if DEBUG_MODE:
                print 'len(data)=%d, size=%d' % (len(data), size)
            raise IOError, 'OLE stream size is less than declared'
        # when all data is read in memory, StringIO constructor is called
        StringIO.StringIO.__init__(self, data)
        # Then the _OleStream object can be used as a read-only file object.


#--- _OleDirectoryEntry -------------------------------------------------------

class _OleDirectoryEntry:

    """
    OLE2 Directory Entry
    """
    #[PL] parsing code moved from OleFileIO.loaddirectory

    # struct to parse directory entries:
    # <: little-endian byte order
    # 64s: string containing entry name in unicode (max 31 chars) + null char
    # H: uint16, number of bytes used in name buffer, including null = (len+1)*2
    # B: uint8, dir entry type (between 0 and 5)
    # B: uint8, color: 0=black, 1=red
    # I: uint32, index of left child node in the red-black tree, NOSTREAM if none
    # I: uint32, index of right child node in the red-black tree, NOSTREAM if none
    # I: uint32, index of child root node if it is a storage, else NOSTREAM
    # 16s: CLSID, unique identifier (only used if it is a storage)
    # I: uint32, user flags
    # 8s: uint64, creation timestamp or zero
    # 8s: uint64, modification timestamp or zero
    # I: uint32, SID of first sector if stream or ministream, SID of 1st sector
    #    of stream containing ministreams if root entry, 0 otherwise
    # I: uint32, total stream size in bytes if stream (low 32 bits), 0 otherwise
    # I: uint32, total stream size in bytes if stream (high 32 bits), 0 otherwise
    STRUCT_DIRENTRY = '<64sHBBIII16sI8s8sIII'
    # size of a directory entry: 128 bytes
    DIRENTRY_SIZE = 128
    assert struct.calcsize(STRUCT_DIRENTRY) == DIRENTRY_SIZE


    def __init__(self, entry, sid, olefile):
        """
        Constructor for an _OleDirectoryEntry object.
        Parses a 128-bytes entry from the OLE Directory stream.

        entry  : string (must be 128 bytes long)
        sid    : index of this directory entry in the OLE file directory
        olefile: OleFileIO containing this directory entry
        """
        self.sid = sid
        # ref to olefile is stored for future use
        self.olefile = olefile
        # kids is a list of children entries, if this entry is a storage:
        # (list of _OleDirectoryEntry objects)
        self.kids = []
        # kids_dict is a dictionary of children entries, indexed by their
        # name in lowercase: used to quickly find an entry, and to detect
        # duplicates
        self.kids_dict = {}
        # flag used to detect if the entry is referenced more than once in
        # directory:
        self.used = False
        # decode DirEntry
        (
            name,
            namelength,
            self.entry_type,
            self.color,
            self.sid_left,
            self.sid_right,
            self.sid_child,
            clsid,
            self.dwUserFlags,
            self.createTime,
            self.modifyTime,
            self.isectStart,
            sizeLow,
            sizeHigh
        ) = struct.unpack(_OleDirectoryEntry.STRUCT_DIRENTRY, entry)
        if self.entry_type not in [STGTY_ROOT, STGTY_STORAGE, STGTY_STREAM, STGTY_EMPTY]:
            olefile._raise_defect(DEFECT_INCORRECT, 'unhandled OLE storage type')
        # only first directory entry can (and should) be root:
        if self.entry_type == STGTY_ROOT and sid != 0:
            olefile._raise_defect(DEFECT_INCORRECT, 'duplicate OLE root entry')
        if sid == 0 and self.entry_type != STGTY_ROOT:
            olefile._raise_defect(DEFECT_INCORRECT, 'incorrect OLE root entry')

        
        # name should be at most 31 unicode characters + null character,
        # so 64 bytes in total (31*2 + 2):
        if namelength>64:
            olefile._raise_defect(DEFECT_INCORRECT, 'incorrect DirEntry name length')
            # if exception not raised, namelength is set to the maximum value:
            namelength = 64
        if DEBUG_MODE: print 'namelength = ', namelength
        # only characters without ending null char are kept:
        name = name[:(namelength-2)]
        # name is converted from unicode to Latin-1:
        
        self.name = unicode(name,'utf-16') 
        
        if DEBUG_MODE: 
            print "name = ", repr(self.name)

            print 'DirEntry SID=%d: %s' % (self.sid, repr(self.name))
            print ' - type: %d' % self.entry_type
            print ' - sect: %d' % self.isectStart
            print ' - SID left: %d, right: %d, child: %d' % (self.sid_left, self.sid_right, self.sid_child)

        # sizeHigh is only used for 4K sectors, it should be zero for 512 bytes
        # sectors, BUT apparently some implementations set it as 0xFFFFFFFFL, 1
        # or some other value so it cannot be raised as a defect in general:
        if olefile.sectorsize == 512:
            if sizeHigh != 0 and sizeHigh != 0xFFFFFFFFL:
                if DEBUG_MODE:
                    print ('sectorsize=%d, sizeLow=%d, sizeHigh=%d (%X)' %
                    (olefile.sectorsize, sizeLow, sizeHigh, sizeHigh))
                olefile._raise_defect(DEFECT_UNSURE, 'incorrect OLE stream size')
            self.size = sizeLow
        else:
            self.size = sizeLow + (long(sizeHigh)<<32)
        if DEBUG_MODE: print ' - size: %d (sizeLow=%d, sizeHigh=%d)' % (self.size, sizeLow, sizeHigh)

        self.clsid = _clsid(clsid)
        # a storage should have a null size, BUT some implementations such as
        # Word 8 for Mac seem to allow non-null values => Potential defect:
        if self.entry_type == STGTY_STORAGE and self.size != 0:
            olefile._raise_defect(DEFECT_POTENTIAL, 'OLE storage with size>0')
        # check if stream is not already referenced elsewhere:
        if self.entry_type in (STGTY_ROOT, STGTY_STREAM) and self.size>0:
            if self.size < olefile.minisectorcutoff \
            and self.entry_type==STGTY_STREAM: # only streams can be in MiniFAT
                # ministream object
                minifat = True
            else:
                minifat = False
            olefile._check_duplicate_stream(self.isectStart, minifat)



    def build_storage_tree(self):
        """
        Read and build the red-black tree attached to this _OleDirectoryEntry
        object, if it is a storage.
        Note that this method builds a tree of all subentries, so it should
        only be called for the root object once.
        """

        #print 'build_storage_tree: SID=%d - %s - sid_child=%d',self.sid, repr(self.name), self.sid_child
        
        if self.sid_child != NOSTREAM:
            
            # if child SID is not NOSTREAM, then this entry is a storage.
            # Let's walk through the tree of children to fill the kids list:
            self.append_kids(self.sid_child)

            # Note from OpenOffice documentation: the safest way is to
            # recreate the tree because some implementations may store broken
            # red-black trees...

            # in the OLE file, entries are sorted on (length, name).
            # for convenience, we sort them on name instead:
            # (see __cmp__ method in this class)
            self.kids.sort()


    def append_kids(self, child_sid):
        """
        Walk through red-black tree of children of this directory entry to add
        all of them to the kids list. (recursive method)

        child_sid : index of child directory entry to use, or None when called
                    first time for the root. (only used during recursion)
        """
        #[PL] this method was added to use simple recursion instead of a complex
        # algorithm.
        # if this is not a storage or a leaf of the tree, nothing to do:

        if child_sid == NOSTREAM:
            return
        # check if child SID is in the proper range:
        if child_sid<0 or child_sid>=len(self.olefile.direntries):
            self.olefile._raise_defect(DEFECT_FATAL, 'OLE DirEntry index out of range')
        # get child direntry:
        child = self.olefile._load_direntry(child_sid) 
        if DEBUG_MODE:
            print 'name ', repr(child.name)
            print 'append_kids: child_sid=',child.sid
            print 'sid_left',child.sid_left
            print 'sid_right',child.sid_right
            print 'sid_child', child.sid_child
        # the directory entries are organized as a red-black tree.
        # (cf. Wikipedia for details)
        # First walk through left side of the tree:
        self.append_kids(child.sid_left)
        # Check if its name is not already used (case-insensitive):
        name_lower = child.name.lower()
        if self.kids_dict.has_key(name_lower):
            self.olefile._raise_defect(DEFECT_INCORRECT,
                "Duplicate filename in OLE storage")
        # Then the child_sid _OleDirectoryEntry object is appended to the
        # kids list and dictionary:
        self.kids.append(child)
        self.kids_dict[name_lower] = child
        # Check if kid was not already referenced in a storage:
        if child.used:
            self.olefile._raise_defect(DEFECT_INCORRECT,
                'OLE Entry referenced more than once')
        child.used = True
        # Finally walk through right side of the tree:
        self.append_kids(child.sid_right)
        # Afterwards build kid's own tree if it's also a storage:
        child.build_storage_tree()


    def __cmp__(self, other):
        "Compare entries by name"
        return cmp(self.name, other.name)

    def dump(self, tab = 0):
        "Dump this entry, and all its subentries (for debug purposes only)"
        TYPES = ["(invalid)", "(storage)", "(stream)", "(lockbytes)",
                 "(property)", "(root)"]
        print " "*tab + repr(self.name), TYPES[self.entry_type],
        if self.entry_type in (STGTY_STREAM, STGTY_ROOT):
            print self.size, "bytes",
        print
        if self.entry_type in (STGTY_STORAGE, STGTY_ROOT) and self.clsid:
            print " "*tab + "{%s}" % self.clsid

        for kid in self.kids:
            kid.dump(tab + 2)


#--- OleFileIO ----------------------------------------------------------------

class OleFileIO:
    """
    OLE container object

    This class encapsulates the interface to an OLE 2 structured
    storage file.  Use the {@link listdir} and {@link openstream} methods to
    access the contents of this file.

    Object names are given as a list of strings, one for each subentry
    level.  The root entry should be omitted.  For example, the following
    code extracts all image streams from a Microsoft Image Composer file:

        ole = OleFileIO("fan.mic")

        for entry in ole.listdir():
            if entry[1:2] == "Image":
                fin = ole.openstream(entry)
                fout = open(entry[0:1], "wb")
                while 1:
                    s = fin.read(8192)
                    if not s:
                        break
                    fout.write(s)

    You can use the viewer application provided with the Python Imaging
    Library to view the resulting files (which happens to be standard
    TIFF files).
    """

    def __init__(self, filename = None, raise_defects=DEFECT_FATAL):
        """
        Constructor for OleFileIO class.

        filename: file to open.
        raise_defects: minimal level for defects to be raised as exceptions.
        (use DEFECT_FATAL for a typical application, DEFECT_INCORRECT for a
        security-oriented application, see source code for details)
        """
        self._raise_defects_level = raise_defects
        if filename:
            self.open(filename)


    def _raise_defect(self, defect_level, message):
        """
        This method should be called for any defect found during file parsing.
        It may raise an IOError exception according to the minimal level chosen
        for the OleFileIO object.

        defect_level: defect level, possible values are:
            DEFECT_UNSURE    : a case which looks weird, but not sure it's a defect
            DEFECT_POTENTIAL : a potential defect
            DEFECT_INCORRECT : an error according to specifications, but parsing can go on
            DEFECT_FATAL     : an error which cannot be ignored, parsing is impossible
        message: string describing the defect, used with raised exception.
        """
        # added by [PL]
        if defect_level >= self._raise_defects_level:
            raise IOError, message


    def close(self):
        """
        Close an OLE2 file.

        """
        self.fp.close()
            

    def open(self, filename):
        """
        Open an OLE2 file.
        Reads the header, FAT and directory.

        filename: string-like or file-like object
        """
        # check if filename is a string-like or file-like object:
        # (it is better to check for a read() method)
        if hasattr(filename, 'read'):
            # file-like object
            self.fp = filename
        else:
            # string-like object
            self.fp = open(filename, "rb")
        # old code fails if filename is not a plain string:   
        #if type(filename) == type(""):
        #    self.fp = open(filename, "rb")
        #else:
        #    self.fp = filename

        # lists of streams in FAT and MiniFAT, to detect duplicate references
        # (list of indexes of first sectors of each stream)
        self._used_streams_fat = []
        self._used_streams_minifat = []

        header = self.fp.read(512)

        if len(header) != 512 or header[:8] != MAGIC:
            self._raise_defect(DEFECT_FATAL, "not an OLE2 structured storage file")

        # [PL] header structure according to AAF specifications:
        ##Header
        ##struct StructuredStorageHeader { // [offset from start (bytes), length (bytes)]
        ##BYTE _abSig[8]; // [00H,08] {0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1,
        ##                // 0x1a, 0xe1} for current version
        ##CLSID _clsid;   // [08H,16] reserved must be zero (WriteClassStg/
        ##                // GetClassFile uses root directory class id)
        ##USHORT _uMinorVersion; // [18H,02] minor version of the format: 33 is
        ##                       // written by reference implementation
        ##USHORT _uDllVersion;   // [1AH,02] major version of the dll/format: 3 for
        ##                       // 512-byte sectors, 4 for 4 KB sectors
        ##USHORT _uByteOrder;    // [1CH,02] 0xFFFE: indicates Intel byte-ordering
        ##USHORT _uSectorShift;  // [1EH,02] size of sectors in power-of-two;
        ##                       // typically 9 indicating 512-byte sectors
        ##USHORT _uMiniSectorShift; // [20H,02] size of mini-sectors in power-of-two;
        ##                          // typically 6 indicating 64-byte mini-sectors
        ##USHORT _usReserved; // [22H,02] reserved, must be zero
        ##ULONG _ulReserved1; // [24H,04] reserved, must be zero
        ##FSINDEX _csectDir; // [28H,04] must be zero for 512-byte sectors,
        ##                   // number of SECTs in directory chain for 4 KB
        ##                   // sectors
        ##FSINDEX _csectFat; // [2CH,04] number of SECTs in the FAT chain
        ##SECT _sectDirStart; // [30H,04] first SECT in the directory chain
        ##DFSIGNATURE _signature; // [34H,04] signature used for transactions; must
        ##                        // be zero. The reference implementation
        ##                        // does not support transactions
        ##ULONG _ulMiniSectorCutoff; // [38H,04] maximum size for a mini stream;
        ##                           // typically 4096 bytes
        ##SECT _sectMiniFatStart; // [3CH,04] first SECT in the MiniFAT chain
        ##FSINDEX _csectMiniFat; // [40H,04] number of SECTs in the MiniFAT chain
        ##SECT _sectDifStart; // [44H,04] first SECT in the DIFAT chain
        ##FSINDEX _csectDif; // [48H,04] number of SECTs in the DIFAT chain
        ##SECT _sectFat[109]; // [4CH,436] the SECTs of first 109 FAT sectors
        ##};

        # [PL] header decoding:
        # '<' indicates little-endian byte ordering for Intel (cf. struct module help)
        fmt_header = '<8s16sHHHHHHLLLLLLLLLL'
        header_size = struct.calcsize(fmt_header)
        if DEBUG_MODE: print  "fmt_header size = %d, +FAT = %d" % (header_size, header_size + 109*4) 
        header1 = header[:header_size]
        (
            self.Sig,
            self.clsid,
            self.MinorVersion,
            self.DllVersion,
            self.ByteOrder,
            self.SectorShift,
            self.MiniSectorShift,
            self.Reserved, self.Reserved1,
            self.csectDir,
            self.csectFat,
            self.sectDirStart,
            self.signature,
            self.MiniSectorCutoff,
            self.MiniFatStart,
            self.csectMiniFat,
            self.sectDifStart,
            self.csectDif
        ) = struct.unpack(fmt_header, header1)
        if DEBUG_MODE: print  struct.unpack(fmt_header,    header1)

        if self.Sig != '\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
            # OLE signature should always be present
            self._raise_defect(DEFECT_FATAL, "incorrect OLE signature")
        if self.clsid != '\x00'*16:
            # according to AAF specs, CLSID should always be zero
            self._raise_defect(DEFECT_INCORRECT, "incorrect CLSID in OLE header")
        #print  "MinorVersion = %d" , self.MinorVersion
        #print  "DllVersion   = %d" , self.DllVersion 
        if self.DllVersion not in [3, 4]:
            # version 3: usual format, 512 bytes per sector
            # version 4: large format, 4K per sector
            self._raise_defect(DEFECT_INCORRECT, "incorrect DllVersion in OLE header")
        if DEBUG_MODE: print "ByteOrder    = %X" % self.ByteOrder 
        if self.ByteOrder != 0xFFFE:
            # For now only common little-endian documents are handled correctly
            self._raise_defect(DEFECT_FATAL, "incorrect ByteOrder in OLE header")

        self.SectorSize = 2**self.SectorShift
        if DEBUG_MODE: print "SectorSize   = %d" % self.SectorSize 
        if self.SectorSize not in [512, 4096]:
            self._raise_defect(DEFECT_INCORRECT, "incorrect SectorSize in OLE header")
        if (self.DllVersion==3 and self.SectorSize!=512) \
        or (self.DllVersion==4 and self.SectorSize!=4096):
            self._raise_defect(DEFECT_INCORRECT, "SectorSize does not match DllVersion in OLE header")
        self.MiniSectorSize = 2**self.MiniSectorShift
        if DEBUG_MODE: print "MiniSectorSize   = %d" % self.MiniSectorSize 
        if self.MiniSectorSize not in [64]:
            self._raise_defect(DEFECT_INCORRECT, "incorrect MiniSectorSize in OLE header")
        if self.Reserved != 0 or self.Reserved1 != 0:
            self._raise_defect(DEFECT_INCORRECT, "incorrect OLE header (non-null reserved bytes)")
        if DEBUG_MODE: print "number of directory sectors csectDir     = %d" % self.csectDir 
        if self.SectorSize==512 and self.csectDir!=0:
            self._raise_defect(DEFECT_INCORRECT, "incorrect csectDir in OLE header")
        #print  "csectFat     = %d" % self.csectFat 
        #print  "sectDirStart = %X" % self.sectDirStart 
        #print "signature    = %d" % self.signature 
        # Signature should be zero, BUT some implementations do not follow this
        # rule => only a potential defect:
        if self.signature != 0:
            self._raise_defect(DEFECT_POTENTIAL, "incorrect OLE header (signature>0)")
        if DEBUG_MODE: 
            print "MiniSectorCutoff = %d" % self.MiniSectorCutoff 
            print "MiniFatStart     = %X" % self.MiniFatStart 
            print "csectMiniFat     = %d" % self.csectMiniFat 
            print "sectDifStart     = %X" % self.sectDifStart 
            print "csectDif         = %d" % self.csectDif 

        # calculate the number of sectors in the file
        # (-1 because header doesn't count)
        filesize = os.path.getsize(filename)
        self.nb_sect = ( (filesize + self.SectorSize-1) / self.SectorSize) - 1
        #print "Number of sectors in the file:",  self.nb_sect 

        # file clsid (probably never used, so we don't store it)
        clsid = _clsid(header[8:24])
        self.sectorsize = self.SectorSize #1 << i16(header, 30)
        self.minisectorsize = self.MiniSectorSize  #1 << i16(header, 32)
        self.minisectorcutoff = self.MiniSectorCutoff # i32(header, 56)

        # check known streams for duplicate references (these are always in FAT,
        # never in MiniFAT):
        self._check_duplicate_stream(self.sectDirStart)
        # check MiniFAT only if it is not empty:
        if self.csectMiniFat:
            self._check_duplicate_stream(self.MiniFatStart)
        # check DIFAT only if it is not empty:
        if self.csectDif:
            self._check_duplicate_stream(self.sectDifStart)

        # Load file allocation tables
        self.loadfat(header)
        # Load direcory.  This sets both the direntries list (ordered by sid)
        # and the root (ordered by hierarchy) members.
        self.loaddirectory(self.sectDirStart)#i32(header, 48))
        self.ministream = None
        self.minifatsect = self.MiniFatStart #i32(header, 60)


    def _check_duplicate_stream(self, first_sect, minifat=False):
        """
        Checks if a stream has not been already referenced elsewhere.
        This method should only be called once for each known stream, and only
        if stream size is not null.
        first_sect: index of first sector of the stream in FAT
        minifat: if True, stream is located in the MiniFAT, else in the FAT
        """
        if minifat:
            if DEBUG_MODE: print '_check_duplicate_stream: sect=%d in MiniFAT' % first_sect
            used_streams = self._used_streams_minifat
        else:
            if DEBUG_MODE: print '_check_duplicate_stream: sect=%d in FAT' % first_sect
            # some values can be safely ignored (not a real stream):
            if first_sect in (DIFSECT,FATSECT,ENDOFCHAIN,FREESECT):
                return
            used_streams = self._used_streams_fat
        
        if first_sect in used_streams:
            self._raise_defect(DEFECT_INCORRECT, 'Stream referenced twice')
        else:
            used_streams.append(first_sect)


    def dumpfat(self, fat, firstindex=0):
        "Displays a part of FAT in human-readable form for debugging purpose"
        # [PL] added only for debug
        if not DEBUG_MODE:
            return
        # dictionary to convert special FAT values in human-readable strings
        VPL=8 # valeurs par ligne (8+1 * 8+1 = 81)
        fatnames = {
            FREESECT:   "..free..",
            ENDOFCHAIN: "[ END. ]",
            FATSECT:    "FATSECT ",
            DIFSECT:    "DIFSECT "
            }
        nbsect = len(fat)
        nlines = (nbsect+VPL-1)/VPL
        print "index",
        for i in range(VPL):
            print ("%8X" % i),
        print ""
        for l in range(nlines):
            index = l*VPL
            print ("%8X:" % (firstindex+index)),
            for i in range(index, index+VPL):
                if i>=nbsect:
                    break
                sect = fat[i]
                if sect in fatnames:
                    nom = fatnames[sect]
                else:
                    if sect == i+1:
                        nom = "    --->"
                    else:
                        nom = "%8X" % sect
                print nom,
            print ""


    def dumpsect(self, sector, firstindex=0):
        "Displays a sector in a human-readable form, for debugging purpose."
        if not DEBUG_MODE:
            return
        VPL=8 # number of values per line (8+1 * 8+1 = 81)
        tab = array.array(UINT32, sector)
        nbsect = len(tab)
        nlines = int((nbsect+VPL-1)/VPL)
        print "index",
        for i in range(VPL):
            print ("%8X" % i),
        print ""
        for l in range(nlines):
            index = l*VPL
            print ("%8X:" % (firstindex+index)),
            for i in range(index, index+VPL):
                if i>=nbsect:
                    break
                sect = tab[i]
                nom = "%8X" % sect
                print nom,
            print ""

    def sect2array(self, sect):
        """
        convert a sector to an array of 32 bits unsigned integers,
        swapping bytes on big endian CPUs such as PowerPC (old Macs)
        """
        a = array.array(UINT32, sect)
        # if CPU is big endian, swap bytes:
        if sys.byteorder == 'big':
            a.byteswap()
        return a        


    def loadfat_sect(self, sect):
        """
        Adds the indexes of the given sector to the FAT
        sect: string containing the first FAT sector, or array of long integers
        return: index of last FAT sector.
        """
        # a FAT sector is an array of ulong integers.
        if isinstance(sect, array.array):
            # if sect is already an array it is directly used
            fat1 = sect
        else:
            # if it's a raw sector, it is parsed in an array
            fat1 = self.sect2array(sect)
            self.dumpsect(sect)
        # The FAT is a sector chain starting at the first index of itself.
        for isect in fat1:
            #print "isect = %X" % isect
            if isect == ENDOFCHAIN or isect == FREESECT:
                # the end of the sector chain has been reached
                break
            # read the FAT sector
            s = self.getsect(isect)
            # parse it as an array of 32 bits integers, and add it to the
            # global FAT array
            nextfat = self.sect2array(s)
            self.fat = self.fat + nextfat
        return isect


    def loadfat(self, header):
        """
        Load the FAT table.
        """
        # The header contains a sector  numbers
        # for the first 109 FAT sectors.  Additional sectors are
        # described by DIF blocks

        sect = header[76:512]

        # [PL] FAT is an array of 32 bits unsigned ints, it's more effective
        # to use an array than a list in Python.
        # It's initialized as empty first:
        self.fat = array.array(UINT32)
        self.loadfat_sect(sect)

        if self.csectDif != 0:
            # [PL] There's a DIFAT because file is larger than 6.8MB
            # some checks just in case:
            if self.csectFat <= 109:
                # there must be at least 109 blocks in header and the rest in
                # DIFAT, so number of sectors must be >109.
                self._raise_defect(DEFECT_INCORRECT, 'incorrect DIFAT, not enough sectors')
            if self.sectDifStart >= self.nb_sect:
                # initial DIFAT block index must be valid
                self._raise_defect(DEFECT_FATAL, 'incorrect DIFAT, first index out of range')
            if DEBUG_MODE: print "DIFAT analysis..." 
            # We compute the necessary number of DIFAT sectors :
            # (each DIFAT sector = 127 pointers + 1 towards next DIFAT sector)
            nb_difat = (self.csectFat-109 + 126)/127
            if DEBUG_MODE: print "nb_difat = %d" % nb_difat 
            if self.csectDif != nb_difat:
                raise IOError, 'incorrect DIFAT'
            isect_difat = self.sectDifStart
            for i in xrange(nb_difat):
                if DEBUG_MODE: print "DIFAT block %d, sector %X" % (i, isect_difat) 

                sector_difat = self.getsect(isect_difat)
                difat = self.sect2array(sector_difat)
                self.dumpsect(sector_difat)
                self.loadfat_sect(difat[:127])
                # last DIFAT pointer is next DIFAT sector:
                isect_difat = difat[127]
                if DEBUG_MODE: print "next DIFAT sector: %X" % isect_difat 
            # checks:
            if isect_difat not in [ENDOFCHAIN, FREESECT]:
                # last DIFAT pointer value must be ENDOFCHAIN or FREESECT
                raise IOError, 'incorrect end of DIFAT'

        # since FAT is read from fixed-size sectors, it may contain more values
        # than the actual number of sectors in the file.
        

        # Keep only the relevant sector indexes:
        if len(self.fat) > self.nb_sect:
            if DEBUG_MODE: print 'len(fat)=%d, shrunk to nb_sect=%d' % (len(self.fat), self.nb_sect)
            self.fat = self.fat[:self.nb_sect]
        if DEBUG_MODE: print'\nFAT:'
        self.dumpfat(self.fat)
        


    def loadminifat(self):
        """
        Load the MiniFAT table.
        """
        # MiniFAT is stored in a standard  sub-stream, pointed to by a header
        # field.
        # NOTE: there are two sizes to take into account for this stream:
        # 1) Stream size is calculated according to the number of sectors
        #    declared in the OLE header. This allocated stream may be more than
        #    needed to store the actual sector indexes.
        # (self.csectMiniFat is the number of sectors of size self.SectorSize)
        stream_size = self.csectMiniFat * self.SectorSize
        # 2) Actually used size is calculated by dividing the MiniStream size
        #    (given by root entry size) by the size of mini sectors, *4 for
        #    32 bits indexes:
        nb_minisectors = (self.root.size + self.MiniSectorSize-1) / self.MiniSectorSize
        used_size = nb_minisectors * 4
        if DEBUG_MODE: print ('loadminifat(): minifatsect=%d, nb FAT sectors=%d, used_size=%d, stream_size=%d, nb MiniSectors=%d' %
            (self.minifatsect, self.csectMiniFat, used_size, stream_size, nb_minisectors))
        if used_size > stream_size:
            # This is not really a problem, but may indicate a wrong implementation:
            self._raise_defect(DEFECT_INCORRECT, 'OLE MiniStream is larger than MiniFAT')
        # In any case, first read stream_size:
        s = self._open(self.minifatsect, stream_size, force_FAT=True).read()
        #[PL] Old code replaced by an array:
        #self.minifat = map(lambda i, s=s: i32(s, i), range(0, len(s), 4))
        self.minifat = self.sect2array(s)
        # Then shrink the array to used size, to avoid indexes out of MiniStream:
        if DEBUG_MODE: print 'MiniFAT shrunk from %d to %d sectors' % (len(self.minifat), nb_minisectors)
        self.minifat = self.minifat[:nb_minisectors]
        if DEBUG_MODE: print 'loadminifat(): len=%d' % len(self.minifat)
        if DEBUG_MODE: print '\nMiniFAT:'
        self.dumpfat(self.minifat)

    def getsect(self, sect):
        """
        Read given sector from file on disk.
        sect: sector index
        returns a string containing the sector data.
        """
        # [PL] this original code was wrong when sectors are 4KB instead of
        # 512 bytes:
        #self.fp.seek(512 + self.sectorsize * sect)
        #[PL]: added safety checks:
        #print "getsect(%X)" % sect
        try:
            self.fp.seek(self.sectorsize * (sect+1))
        except:
            if DEBUG_MODE: print ('getsect(): sect=%X, seek=%d, filesize=%d' %
                (sect, self.sectorsize*(sect+1), os.path.getsize(self.fp.name)))
            self._raise_defect(DEFECT_FATAL, 'OLE sector index out of range')
        sector = self.fp.read(self.sectorsize)
        if len(sector) != self.sectorsize:
            if DEBUG_MODE: print ('getsect(): sect=%X, read=%d, sectorsize=%d' %
                (sect, len(sector), self.sectorsize))
            self._raise_defect(DEFECT_FATAL, 'incomplete OLE sector')
        return sector


    def loaddirectory(self, sect):
        """
        Load the directory.
        sect: sector index of directory stream.
        """
        # The directory is  stored in a standard
        # substream, independent of its size.

        # open directory stream as a read-only file:
        # (stream size is not known in advance)
        
        #ML: size is equal to the number of directory sectors times sector size
        # self.csectDir * self.sectorsize
        
        self.directory_fp = self._open(sect)
        
        

        #[PL] to detect malformed documents and avoid DoS attacks, the maximum
        # number of directory entries can be calculated:
        max_entries = self.directory_fp.size / 128
        if DEBUG_MODE: print 'loaddirectory: size=%d, max_entries=%d' % (self.directory_fp.size, max_entries)

        # Create list of directory entries
        # We start with a list of "None" object
        self.direntries = [None] * max_entries

        # load root entry:
        root_entry = self._load_direntry(0)
        # Root entry is the first entry:
        self.root = self.direntries[0]

        # read and build all storage trees, starting from the root:
        self.root.build_storage_tree()


    def _load_direntry (self, sid):
        """
        Load a directory entry from the directory.
        This method should only be called once for each storage/stream when
        loading the directory.
        sid: index of storage/stream in the directory.
        return: a _OleDirectoryEntry object
        raise: IOError if the entry has always been referenced.
        """
        # check if SID is OK:
        if sid<0 or sid>=len(self.direntries):
            self._raise_defect(DEFECT_FATAL, "OLE directory index out of range")
        # check if entry was already referenced:
        if self.direntries[sid] is not None:
            self._raise_defect(DEFECT_INCORRECT,
                "double reference for OLE stream/storage")
            # if exception not raised, return the object
            return self.direntries[sid]
        #print "dir enntry sid = ", sid
        self.directory_fp.seek(sid * 128)
        entry = self.directory_fp.read(128)
        self.direntries[sid] = _OleDirectoryEntry(entry, sid, self)
        return self.direntries[sid]


    def dumpdirectory(self):
        """
        Dump directory (for debugging only)
        """
        self.root.dump()


    def _open(self, start, size = 0x7FFFFFFF, force_FAT=False):
        """
        Open a stream, either in FAT or MiniFAT according to its size.
        (openstream helper)

        start: index of first sector
        size: size of stream (or nothing if size is unknown)
        force_FAT: if False (default), stream will be opened in FAT or MiniFAT
                   according to size. If True, it will always be opened in FAT.
        """
        #print 'OleFileIO.open(): sect=%d, size=%d, force_FAT=%s' % (start, size, str(force_FAT))
        # stream size is compared to the MiniSectorCutoff threshold:
        if size < self.minisectorcutoff and not force_FAT:
            # ministream object
            if not self.ministream:
                # load MiniFAT if it wasn't already done:
                self.loadminifat()
                # The first sector index of the miniFAT stream is stored in the
                # root directory entry:
                size_ministream = self.root.size
                if DEBUG_MODE: print ('Opening MiniStream: sect=%d, size=%d' %
                    (self.root.isectStart, size_ministream))
                self.ministream = self._open(self.root.isectStart,
                    size_ministream, force_FAT=True)
            return _OleStream(self.ministream, start, size, 0,
                              self.minisectorsize, self.minifat)
        else:
            # standard stream
#            return _OleStream(self.fp, start, size, 512,
#                              self.sectorsize, self.fat)
            return _OleStream(self.fp, start, size, self.sectorsize,
                              self.sectorsize, self.fat)

    def _list(self, files, prefix, node):
        """
        (listdir helper)
        files: list of files to fill in
        prefix: current location in storage tree (list of names)
        node: current node (_OleDirectoryEntry object)
        """
        prefix = prefix + [node.name]
        for entry in node.kids:
            if entry.kids:
                self._list(files, prefix, entry)
            else:
                files.append(prefix[1:] + [entry.name])


    def listdir(self):
        """
        Return a list of streams stored in this file
        """
        files = []
        self._list(files, [], self.root)
        return files


    def _find(self, filename):
        """
        Returns directory entry of given filename. (openstream helper)
        Note: this method is case-insensitive.

        filename: path of stream in storage tree (except root entry), either:
            - a string using Unix path syntax, for example:
              'storage_1/storage_1.2/stream'
            - a list of storage filenames, path to the desired stream/storage.
              Example: ['storage_1', 'storage_1.2', 'stream']
        return: sid of requested filename
        raise IOError if file not found
        """

        # if filename is a string instead of a list, split it on slashes to
        # convert to a list:
        if isinstance(filename, basestring):
            filename = filename.split('/')
        # walk across storage tree, following given path:
        node = self.root
        for name in filename:
            for kid in node.kids:
                if kid.name.lower() == name.lower():
                    break
            else:
                raise IOError, "file not found"
            node = kid
        return node.sid


    def openstream(self, filename):
        """
        Open a stream as a read-only file object (StringIO).

        filename: path of stream in storage tree (except root entry), either:
            - a string using Unix path syntax, for example:
              'storage_1/storage_1.2/stream'
            - a list of storage filenames, path to the desired stream/storage.
              Example: ['storage_1', 'storage_1.2', 'stream']
        return: file object (read-only)
        raise IOError if filename not found, or if this is not a stream.
        """
        sid = self._find(filename)
        entry = self.direntries[sid]
        if entry.entry_type != STGTY_STREAM:
            raise IOError, "this file is not a stream"
        return self._open(entry.isectStart, entry.size)


    def get_type(self, filename):
        """
        Test if given filename exists as a stream or a storage in the OLE
        container, and return its type.

        filename: path of stream in storage tree. (see openstream for syntax)
        return: False if object does not exist, its entry type (>0) otherwise:
            - STGTY_STREAM: a stream
            - STGTY_STORAGE: a storage
            - STGTY_ROOT: the root entry
        """
        try:
            sid = self._find(filename)
            entry = self.direntries[sid]
            return entry.entry_type
        except:
            return False


    def exists(self, filename):
        """
        Test if given filename exists as a stream or a storage in the OLE
        container.

        filename: path of stream in storage tree. (see openstream for syntax)
        return: True if object exist, else False.
        """
        try:
            sid = self._find(filename)
            return True
        except:
            return False


    def get_size(self, filename):
        """
        Return size of a stream in the OLE container, in bytes.

        filename: path of stream in storage tree (see openstream for syntax)
        return: size in bytes (long integer)
        raise: IOError if file not found, TypeError if this is not a stream.
        """
        sid = self._find(filename)
        entry = self.direntries[sid]
        if entry.entry_type != STGTY_STREAM:

            raise TypeError, 'object is not an OLE stream'
        return entry.size


    def get_rootentry_name(self):
        """
        Return root entry name. Should usually be 'Root Entry' or 'R' in most
        implementations.
        """
        return self.root.name


    def getproperties(self, filename):
        """
        Return properties described in substream.

        filename: path of stream in storage tree (see openstream for syntax)
        return: a dictionary of values indexed by id (integer)
        """
        fp = self.openstream(filename)

        data = {}

        # header
        s = fp.read(28)
        clsid = _clsid(s[8:24])

        # format id
        s = fp.read(20)
        fmtid = _clsid(s[:16])
        fp.seek(i32(s, 16))

        # get section
        s = "****" + fp.read(i32(fp.read(4))-4)

        for i in range(i32(s, 4)):

            id = i32(s, 8+i*8)
            offset = i32(s, 12+i*8)
            type = i32(s, offset)

            if DEBUG_MODE: print 'property id=%d: type=%d offset=%X' % (id, type, offset)

            # test for common types first (should perhaps use
            # a dictionary instead?)

            if type == VT_I2:
                value = i16(s, offset+4)
                if value >= 32768:
                    value = value - 65536
            elif type == VT_UI2:
                value = i16(s, offset+4)
            elif type in (VT_I4, VT_ERROR):
                value = i32(s, offset+4)
            elif type == VT_UI4:
                value = i32(s, offset+4) # FIXME
            elif type in (VT_BSTR, VT_LPSTR):
                count = i32(s, offset+4)
                value = s[offset+8:offset+8+count-1]
            elif type == VT_BLOB:
                count = i32(s, offset+4)
                value = s[offset+8:offset+8+count]
            elif type == VT_LPWSTR:
                count = i32(s, offset+4)
                value = self._unicode(s[offset+8:offset+8+count*2])
            elif type == VT_FILETIME:
                value = long(i32(s, offset+4)) + (long(i32(s, offset+8))<<32)
                # This is a 64-bit int: "number of 100ns periods
                # since Jan 1,1601".  Should map this to Python time
                value = value / 10000000L # seconds
            elif type == VT_UI1:
                value = ord(s[offset+4])
            elif type == VT_CLSID:
                value = _clsid(s[offset+4:offset+20])
            elif type == VT_CF:
                count = i32(s, offset+4)
                value = s[offset+8:offset+8+count]
            else:
                value = None # everything else yields "None"


            if DEBUG_MODE: 
                print "%08x" % id, repr(value),
                print "(%s)" % VT[i32(s, offset) & 0xFFF]

            data[id] = value

        return data


        
