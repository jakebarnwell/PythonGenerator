import config
from plyny.plio.image import PathedImage as Image, HTMLImage
from web import Page, Url

import unittest

class TestCase(unittest.TestCase):
    def setUp(self):
        self.p = config.fake_proxy()
        self.p.activate()
    
    def tearDown(self):
        self.p.deactivate()

    def test_estimate_compression(self):
        with config.fake_proxy():
            i = Image('http://radioprimetime.org/specials/focusspecials/images/dog2.jpg')
            self.assertAlmostEquals(i.estimate_compression(), 0.528500932546)
            i = Image('http://www.costumedogs.com/wp-content/uploads/2007/07/tux.jpg')
            self.assertAlmostEquals(i.estimate_compression(), 0.989372469636)
            i = Image('http://www.freefoto.com/images/01/07/01_07_1---Pair-of-Dogs_web.jpg?&k=Pair+of+Dogs')
            self.assertAlmostEquals(i.estimate_compression(), 0.268289197942)

    def test_entropy(self):
        i = Image(config.fake_server('images/test_ocr.jpg'))
        self.assertAlmostEquals(i.entropy(), 5.2323108617)

    def test_from_file(self):
        with config.fake_proxy():
            i1 = Image.from_file('test/person.jpg')
            i2 = Image('http://www.cs.unc.edu/~karl/me.jpg')
            self.assertEquals(i1.area(), i2.area())

    def test_pil(self):
        src = 'test/person.jpg'
        i = Image.from_file(src)
        sz1 = i.size()
        i2 = Image.from_pil(i.to_pil())
        sz2 = i2.size()
        self.assertEquals(sz1, sz2)

    def test_url(self):
        with config.fake_proxy():
            i = Image('http://www.cs.unc.edu/~karl/me.jpg')
            self.assertEquals(i.url(), Url('http://www.cs.unc.edu/~karl/me.jpg'))

#    def test_faces(self):
#        from plyny.plio.image import faces
#        faces.load('/usr/share/opencv/haarcascades/haarcascade_frontalface_alt2.xml')
#        # XXX above needs to not be hardcoded
#        from core.pmap import pmap
#        with config.fake_proxy():
#            y = list(map(lambda x: Image(x).faces(), ('http://www.cs.unc.edu/~karl/me.jpg', 'http://www.test.com/images/test_ocr.jpg')))
#            self.assertEquals(y[0], 1)
#            self.assertEquals(y[1], 0)

    def test_entropy(self):
        with config.fake_proxy():
            i = Image('http://www.cs.unc.edu/~karl/me.jpg')
            self.assertAlmostEquals(i.entropy(), 8.67911685935)
            i = Image(config.fake_server('images/test_ocr.jpg'))
            self.assertAlmostEquals(i.entropy(), 5.2323108617)

    def xxx_test_extract_text(self):
        # XXX
        i = Image(config.fake_server('images/test_ocr.jpg'))
        self.assertEquals(i.text().rstrip(), 'Hello World!')

    def test_parse_text(self):
        from string import ascii_letters

        p = Page(config.fake_server('image1.html'))
        for i, image in enumerate(p.images()):
            label = image.src.leaf()[4]

            if label != 'y':
                self.assertEqual(label, ascii_letters[i])
                self.assertEqual((i + 1) * 10, image.width)
                self.assertEqual((i + 1) * 20, image.height)
                self.assertEqual(label, image.title[-1])
                self.assertEqual(label, image.alt[-1])

        p = Page(config.fake_server('bad_image.html'))
        bads = list(p._get_tree().xpath('//img'))

        bad_img = HTMLImage.from_element(bads[0])
        self.assertEqual(bad_img.width, 11)
        self.assertEqual(bad_img.height, 12)

        bad_img = HTMLImage.from_element(bads[1])
        self.assertTrue(bad_img.width is None)
        self.assertTrue(bad_img.height is None)

    def test_basic_text(self):
        try:
            i = Image(Url('http://www.cs.unc.edu/~karl/Images/nav.jpg'))
            self.assertEqual(i.size(), (893, 446))

            images = set(Page(Url('http://www.cs.unc.edu/~karl')).images())
            self.assertEqual(len(images), 1)
            self.assertTrue(i in images)
        except:
            pass

        #p = Page(Url('http://www.cs.unc.edu/~karl'))
        #for e in p.images():
            #print Image.fromelement(e)

if __name__ == '__main__':
    unittest.main()
