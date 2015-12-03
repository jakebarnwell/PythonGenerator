import csv
import datetime
from cStringIO import StringIO
from django.utils.timezone import utc
from django.http import HttpResponse
from django.conf import settings
from pytz import timezone
from reportlab.pdfgen import canvas
from cStringIO import StringIO

def contact_csv(contacts):
    from subscribers.models import Inquiry
    fh = StringIO()
    writer = UnicodeWriter(fh)
    for obj in contacts:           
        if isinstance(obj, Inquiry):
            row = [obj.type.code] + obj.contact.get_address_lines()
        else:
            row = obj.get_address_lines()
        writer.writerow(row)
    return fh.getvalue()

def contact_csv_response(contacts):
    response = HttpResponse(contact_csv(contacts))
    response['Content-type'] = "text/csv; charset=utf-8"
    response['Content-disposition'] = "attachment; filename=contacts.csv"
    return response

def contact_pdf_response(contacts):
    from subscribers.models import Inquiry
    # Print mailing labels, appropriate for a Dymo printer.
    out = StringIO()
    width = 3.5 * 72. # convert from inches to points (1/72 inch).
    height = 1.125 * 72. # convert from inches to points (1/72 inch).
    c = canvas.Canvas(out, pagesize=(width, height))
    c.setFont("Helvetica", 12)
    for obj in contacts:
        if isinstance(obj, Inquiry):
            address_lines = obj.contact.get_address_lines()
            code = obj.response_type.code
        else:
            address_lines = obj.get_address_lines()
            code = ""
        i = 0
        for i, line in enumerate(address_lines):
            c.drawString(10, height - height / 6. * (i + 1), line)
            c.drawString(180, height - height / 6. * 5.5, code)
        c.showPage()
    c.save()
    response = HttpResponse(out.getvalue())
    response['Content-type'] = "application/pdf"
    response['Content-disposition'] = "attachment; filename=labels.pdf"
    return response



#
# Unicode CSV taken from http://docs.python.org/library/csv.html#csv-examples
#

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]

def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')

import csv, codecs, cStringIO

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
