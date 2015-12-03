import sys
sys.path.append("../")

from photos import photoAPI, photoHTMLrenderer, photoUploader
from profile import profile_page, editprofile_page
from event import event
from user import usertools
from user import user_pages
from sessions import sessions
import TemplateAPI
import database_engine, TemplateAPI




def photo(response):
	try:
		#render an image with the photoid of 0
		response.write("<h2>ImageGrid Render Test</h2>")
		response.write(photoHTMLrenderer.imggridRender( photoAPI._photo_GetAll()))
		response.write("<br><br><br><h2>Image Render Test</h2>")
		response.write(photoHTMLrenderer.imgtagRender( 1))
	except:
		response.redirect("/internal_error")

#simple uploader page for testing.
def photo_uploader(response):
	try:
		response.write(photoUploader.RenderSimpleuploader())
	except:
		response.redirect("/internal_error")

#handler for the test photo uploader.
def photo_uploaderhandler(response):
	try:
		descriptions = response.get_field('desc')
		datalist = response.get_file('uploads')
		response.write( photoUploader.ProcessUpload(datalist, descriptions))
	except:
		response.redirect("/internal_error")

#handler for the event multiuploader
def photo_multiuploaderhander(response):
	try:
		userid = sessions.get_uid(response)
		eventid = int(response.get_field('event'))
		datalist = response.get_files('uploads')
		response.write( photoUploader.HandleEventMultiupload(datalist, userid, eventid))
	except ZeroDivisionError:
		response.redirect("/internal_error")


#handler for profile picture uploader.
def DP_uploaderhandler(response):
	try:
		userid = int(response.get_field('user'))
		datalist = response.get_file('uploads')
		response.redirect("/profile")
	except:
		response.redirect("/internal_error")

#generates a random image address for the frontpage.
def RandImg(response):
    response.write(photoAPI.Photo_GetRandom())

#renders the page for 'viewing' a photo
def PhotoView(response):
    try:
        try:
            usrid = sessions.get_uid(response)
            photoid = int(response.get_field('photo'))
        except:
            usrid = sessions.get_uid(response)
            photoid = 1

        conn = database_engine.Get_DatabaseConnection()
        curs = conn.cursor()
        curs.execute("""SELECT userid FROM photos WHERE photoid=?""", (response.get_field('photo'),))
        if curs.fetchone()[0] == usrid:
                button = photoHTMLrenderer.RenderEditButton(photoid)
        else:
                button = ""
        comments = photoAPI._photo_GetPicComments( photoid)
        result = photoHTMLrenderer.PhotoPageRender(photoid, usrid)
        page = TemplateAPI.render('photoview.tem', response, {'edit': button,'comments':comments, 'photo':photoid, 'usr':usrid, 'imgtag':result[0], 'title':result[1], 'description':result[2]})
        response.write(page)
    except:
        response.redirect("/internal_error")

def CommentCommit(response):
    try:
        usrid = sessions.get_uid(response)
        photoid = int(response.get_field('photo'))
    except:
        response.redirect("/internal_error")

    comment = response.get_field('comment')
    photoAPI.Photo_WriteComment(photoid, comment, usrid)
    response.redirect("/picview?photo="+str(photoid))


def EditPicRender(response):
        conn = database_engine.Get_DatabaseConnection()
        curs = conn.cursor()
        curs.execute("""SELECT tag FROM phototags WHERE photoid=?""", (response.get_field('photo'),))
        tagstr = ""
        for x in curs.fetchall():
                tagstr += x[0] + " "
        curs = conn.cursor()
        curs.execute("""SELECT description FROM photos WHERE photoid=?""", (response.get_field('photo'),))
        response.write("""
<style>
#photoupdate {
  display: table;
}
  #photoupdate div {
    display: table-row;
  }
  #photoupdate label, #photoupdate input {
    display: table-cell;
  }
</style>
<body style='color: white;background-color: black;'>
<p><b>Photo Data Update: </b></p>
<form action='/photometapost?photo=%s' method='post' enctype='multipart/form-data' id="photoupdate">
  <div>
    <label>Description</label>
    <input name='desc' value='%s'type=input>
  </div>
  <div>
    <label>Tags: (Separated by spaces)</label>
    <input name='tags' value='%s' type=input>
  </div>
  <div>
    <label></label>
    <input type='submit'>
  </div>
</form>
""" % (response.get_field('photo'), curs.fetchone()[0], tagstr))


def ProcessPhotoMetadata(response):
        userid = sessions.get_uid(response)
        photoid = int(response.get_field('photo'))
        conn = database_engine.Get_DatabaseConnection()

        description = response.get_field('desc')
        tags = response.get_field('tags').split(" ")

        curs = conn.cursor()
        curs.execute("""DELETE FROM phototags WHERE photoid=?""", (photoid,))
        conn.commit()
        
        response.write("""<script type="text/javascript">self.close();</script>""")
        curs = conn.cursor()
        curs.execute("""UPDATE photos SET description=? WHERE photoid=?""", (description,int(photoid),))
        conn.commit()
        curs = conn.cursor()
        for tag in tags:
                curs.execute("""INSERT INTO phototags(tag, photoid) values (?, ?)""", (tag, photoid))
        conn.commit()

def Init(server):
        server.register("/pictureuploader", photo_uploader)
        server.register("/pupload",photo_uploaderhandler) #handler for simple uploads
        server.register("/profilepicupload", DP_uploaderhandler)
        server.register("/photo", photo)
        server.register("/eventup", photo_multiuploaderhander)
        server.register("/ajax/randimg", RandImg)
        server.register("/picview", PhotoView)
        server.register("/commentpost", CommentCommit)  
        server.register("/picedit", EditPicRender)
        server.register("/photometapost", ProcessPhotoMetadata)


