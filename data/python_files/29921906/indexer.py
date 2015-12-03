import os, sys,  re  #, logging
import time
import xappy
from sensible.loginit import logger
from scripts.timing import print_timing
import books
from conf import configure

log = logger(__name__)

num_sort_regex = re.compile('\d+')


def zero_fill(matchobj):
    return matchobj.group().zfill(8)

def sortable(title):
    if title:
        sortabletitle = title.lower().strip()
        # Replace numbers with zero filled numbers
        sortabletitle = num_sort_regex.sub(zero_fill, sortabletitle)
        # Truncate to prevent bloat
        sortabletitle = sortabletitle[:30]
        return sortabletitle
    return ''

def indexer_connection(index_path=None):
    if not index_path:
        index_path = configure()
    indexer = xappy.IndexerConnection(index_path)

    # indexes
    indexer.add_field_action('searchable_text', xappy.FieldActions.INDEX_FREETEXT, nopos=True)
    indexer.add_field_action('author', xappy.FieldActions.INDEX_EXACT)
    #indexer.add_field_action('keywords', xappy.FieldActions.FACET)
    indexer.add_field_action('type', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('alpha', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('language', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('genre', xappy.FieldActions.INDEX_EXACT)
    indexer.add_field_action('sortable_title', xappy.FieldActions.SORTABLE)
    indexer.add_field_action('hidden', xappy.FieldActions.INDEX_EXACT)
    #indexer.add_field_action('modified', xappy.FieldActions.SORTABLE, type='data')

    # metadata
    indexer.add_field_action('title', xappy.FieldActions.STORE_CONTENT)
    indexer.add_field_action('alpha', xappy.FieldActions.STORE_CONTENT)
    indexer.add_field_action('language', xappy.FieldActions.STORE_CONTENT)
    indexer.add_field_action('genre', xappy.FieldActions.STORE_CONTENT)
    indexer.add_field_action('type', xappy.FieldActions.STORE_CONTENT)
    indexer.add_field_action('searchable_text', xappy.FieldActions.STORE_CONTENT)
    #indexer.add_field_action('description', xappy.FieldActions.STORE_CONTENT)
    #indexer.add_field_action('author', xappy.FieldActions.STORE_CONTENT)

    return indexer

class Indexer(object):
    
    type = ''
    fields = []
    
    def __init__(self, resource):
        self.resource = resource
        self.doc = xappy.UnprocessedDocument()
        log.debug("indexing %s - %s", self.type, self.resource)

    @staticmethod    
    def get(obj):
        klass = obj.__class__.__name__
        indexer = globals().get("%sIndexer" % klass, None)
        if indexer is None:
            raise KeyError("Indexer for object %s not found." % klass)
        return indexer
    
    def document(self):    
        self.doc.id = self.resource.url
        self.doc.fields.append(xappy.Field('type', self.type))
        
        for field in self.fields:
            value = getattr(self.resource, field)
            if value:
                self.doc.fields.append(xappy.Field(field, value))

        self.add()
        return self.doc
    
    def append(self, field, value):
        if value:
            self.doc.fields.append(xappy.Field(field, value))
        
class BookIndexer(Indexer):

    type = 'Book'
    fields = ['title', 'alpha', 'author', 'language', 'genre']
    
    def add(self):
        self.append('sortable_title', sortable(self.resource.title))
        self.append('searchable_text', self.resource.title)

class SectionIndexer(Indexer):

    type = 'Section'
    
    def add(self):
    
        hidden = self.resource.hidden and '1' or '0'          
        self.doc.fields.append(xappy.Field('hidden', hidden))
                          
        if hidden == '0':
            title = self.resource.title
            self.append('title', title)
            self.append('sortable_title', sortable(title))
            self.append('searchable_text', self.resource.astext())
            self.append('author', self.resource.book.author)
            self.append('language', self.resource.book.language)
            self.append('genre', self.resource.genre)

@print_timing
def index_books(index_path, ids):
    connection = indexer_connection(index_path)
    try:
        for bookid in ids:
            book = books.get_book(bookid)
            doc = BookIndexer(book).document()
            connection.replace(doc)
            print 'indexed book:', bookid
    finally:
        connection.flush()
        connection.close()

@print_timing
def index_all(bookid, index_path):
    connection = indexer_connection(index_path)
    try:
        book = books.get_book(bookid)    
        for obj in book.walk():
            indexer = Indexer.get(obj)
            doc = indexer(obj).document()
            connection.replace(doc)
    finally:
        connection.flush()
        connection.close()

def index(bookid, **kw):
    index_path = configure(**kw)
    return index_all(bookid, index_path)


if __name__ == '__main__':
    n = len(sys.argv)
    bookid = ''
    if n > 1:
        bookid = sys.argv[1]
    if bookid:
        print index(bookid)
    
