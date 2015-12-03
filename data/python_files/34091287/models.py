import os

try:
    from PIL import Image
except ImportError:
    import Image
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User, Group
from django.utils.safestring import mark_safe
from django.utils.datastructures import SortedDict
from django.core.urlresolvers import reverse
from tagging.models import Tag
from tagging.fields import TagField

from rvcms.cms.models import USER_TYPE

# A list of sizes available for each photo, make sure "Thumb" is in there, the rest is upto you
GALLERY_SIZES = getattr(settings, "GALLERY_SIZES", {
    "Thumb": (160, 120),
    "640x480": (640, 480),
    "800x600": (800, 600),
    "1024x768": (1024, 768),
})

# These must match keys in GALLERY_SIZES, they are the order the photo.html template gets the list of photo sizes
GALLERY_SIZES_ORDER = getattr(settings, "GALLERY_SIZES_ORDER", [
    "Thumb", "640x480", "800x600", "1024x768",
])

class Album(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(null=True, blank=True)
    user_type = models.CharField(max_length=1, choices=USER_TYPE, default="E", help_text="Users able to view this album.")
    groups = models.ManyToManyField(Group, verbose_name="Groups", related_name="album_groups", null=True, blank=True, help_text="Groups that can view this album (leave blank for all groups).")

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ("name",)

class Photo(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.FileField(upload_to="gallery/")
    tags = TagField(help_text="Tags for to this image, separated by either spaces or commas.")
    albums = models.ManyToManyField(Album, null=True, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)
    rating = models.IntegerField(default=5, help_text="Image rating, 1-10")
    user = models.ForeignKey(User)

    def __unicode__(self):
        """
        Returns a string representation of a Photo object.
        """
        return self.title

    class Meta:
        ordering = ("title",)

    def albums_col(self):
        """
        Helper method that returns a comma separated list of the albums
        for this photo (as a single string).  Used for prettifying the
        albums column in list view in admin.
        """
        return ", ".join([str(album) for album in self.albums.all()])
    albums_col.short_description = "Albums"

    def tags_col(self):
        """
        Helper method that returns a comma separated list of the tags for this
        post (as a single string).  Used for prettifying the tags column in
        list view in admin.
        """
        return ", ".join([tag.name for tag in Tag.objects.get_for_object(self)])
    tags_col.short_description = "Tags"

    def save(self, rebuild_thumbs=False, *args, **kwargs):
        """
        When saving a Photo object and an image is uploaded, we go through
        the sizes in the GALLERY_SIZES dictionary and make sure a subdirectory
        exists for each size and create it if required.  We then resize the photo
        to that size and save it in each size sub folder using the same filename
        as the original image.

        The original image is left in the base folder.
        """
        super(Photo, self).save(*args, **kwargs)

        if self.image:
            original_path = os.path.join(settings.MEDIA_ROOT, str(self.image))
            filename = os.path.split(original_path)[1]
            original_image = Image.open(original_path)
            original_size = original_image.size

            for size_name, size in GALLERY_SIZES.items():
                path = os.path.join(settings.MEDIA_ROOT, "gallery/", size_name)
                if not os.path.exists(path):
                    os.mkdir(path)
                resized_path = os.path.join(path, filename)

                if not os.path.exists(resized_path) or rebuild_thumbs:
                    original_ratio = float(original_size[0]) / float(original_size[1])
                    new_ratio = float(size[0]) / float(size[1])

                    # check if the image is either wider or taller than target size and ensure that
                    # it never gets wider or taller than the target size
                    if new_ratio == original_ratio:
                        # source and target image have the same ratio
                        new_size = size
                    elif new_ratio > original_ratio:
                        # image is taller than target size, height is fixed, width is calculated
                        new_size = (int(size[1] * original_ratio), int(size[1]))
                    else:
                        # image is wider than target size, width is fixed, height is calculated
                        new_size = (int(size[0]), int(size[0] / original_ratio))

                    # resize the image using the proper aspect ratio, but no wider than the target width,
                    # and no taller than the target height (see if statement above).
                    resized_image = original_image.resize(new_size, Image.ANTIALIAS)

                    # finally, saved the resized image
                    resized_image.save(resized_path)

    def url(self):
        """
        Returns the url of the original image, can be used in templates using:

        <img src="{{ photo.url }}" />

        For different sizes, see: "sizes", which uses a similar syntax in templates:

        <img src="{{ photo.sizes.Thumb.url }}" />
        """
        return os.path.join(settings.MEDIA_URL, str(self.image))

    def html(self):
        """
        Returns the html <img> tag code for the original image, can be used in templates using:

        {{ photo.html }}

        Which generates:

        <img src="/media/gallery/Thumb/image.jpg" width="160" height="120" alt="Image Title" title="Image Title" />

        For different sizes, see "sizes", which uses a similar syntax in templates:

        {{ photo.sizes.Thumb.html }}
        """
        return mark_safe('<img src="%s" alt="" />' % self.url())

    def sizes(self):
        """
        Returns a dictionary of sizes and the url where each image is located,
        and some html code for the image that templates can use, for example:

        {
            'Thumb': {
                'url': '/media/gallery/Thumb/image.jpg',
                'html': '<img src="/media/gallery/Thumb/image.jpg" width="160" height="120" alt="Image Title" title="Image Title" />',
                'page': '/gallery/albums/wallpapers/photo/Thumb/image-slug/',
            },
            '1024x768': {
                'url': '/media/gallery/1024x768/image.jpg',
                'html': '<img src="/media/gallery/1024x768/image.jpg" width="1024" height="768" alt="Image Title" title="Image Title" />',
                'page': '/gallery/albums/wallpapers/photo/1024x768/image-slug/',
            }
        }

        Can be used by templates using:

        {{ photo.sizes.Thumb.html }}

        or:

        <ul class="photos">
            {% for photo in album.photos %}
                <li><img src="{{ photo.sizes.Thumb.url }}" /></li>
            {% endfor %}
        </ul>

        or:

        <h2>Sizes:</h2>
        <p><a href="{{ photo.sizes.1024x768.page }}">1024x768</a></p>
        """
        sizes = SortedDict()

        # only run if an image is attached
        if self.image:
            filename = os.path.split(str(self.image))[1]

            # Now add the other sizes, sorted by the GALLERY_SIZES_ORDER setting
            for size_name in GALLERY_SIZES_ORDER:
                path = os.path.join(settings.MEDIA_URL, "gallery/", size_name)
                sizes[size_name] = {
                    "url": os.path.join(path, filename),
                    "html": mark_safe('<img src="%s" alt="" />' % os.path.join(path, filename)),
                }

        # Return our sizes dictionary
        return sizes

    def tags_list(self):
        """
        Because using photo.tags in templates doesn't sort the tags properly,
        or allow access to the tag object fields in templates.
        """
        return Tag.objects.get_for_object(self)

    def tags_html(self):
        """
        Returns a list of the tags for this photo, formatted as a set of
        html links, for using in templates:

        <h2>Tags:</h2>
        <p>{{ photo.tags_html }}</p>
        """
        return mark_safe(", ".join(['<a href="%s">%s</a>' % (reverse("gallery-tag", args=[tag]), str(tag.name)) for tag in self.tags_list()]))

    class Meta:
        ordering = ("title",)
