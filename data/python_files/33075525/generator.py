import os
import re
import cache
from fields import RequiresField, ModulesField, PackagesField
from template import template, show_field
import jinja2
import simplejson as json
from wtforms import form, fields
import logging
from uuid import uuid4 as uuid

log = logging.getLogger(__name__)

safe_string = jinja2.Markup

SETUP_PY_TEMPLATE = 'setup_py.tpl'

python_file_pattern = re.compile(r'(.*)\.(py|pyc|pyo)$', re.I)
readme_file_pattern = re.compile(r'readme(\..*)?$', re.I)

from trove import all_classifiers
license_choices = \
    [('', '')] + \
    [tuple([c.split(' :: ')[-1]] * 2) for c in all_classifiers
                    if c.startswith('License :: ')]
classifier_choices = [tuple([c] * 2) for c in all_classifiers
                    if not c.startswith('License :: ')]


def create_setup(client=None):
    """
    Use the file list from the source control client to
    instantiate a new Setup object.
    """

    setup = SetupDistutils()

    packages = []
    modules = []
    readme = None

    if client:
        packages = [os.path.dirname(f)
                    for f in client.files if '__init__.' in f]

        # look for files not in a package to add to py_modules in setup
        # find README.* files, first one wins
        modules = []
        for filename in client.files:
            match = re.match(python_file_pattern, filename)
            if match:
                package = os.path.dirname(filename)
                module = match.groups()[0]
                if not module.endswith('setup') and package not in packages:
                    modules.append(module.replace('/', '.'))

            if not readme:
                match = re.match(readme_file_pattern, filename)
                if match:
                    readme = filename

    setup.process(None, **client.discovered)
    setup.readme.data = readme
    setup.py_modules.data = ' '.join(modules)
    setup.packages.data = ' '.join(packages)
    return setup


class Setup(form.Form):
    author = fields.TextField()
    author_email = fields.TextField()
    name = fields.TextField()
    description = fields.TextField()
    version = fields.TextField()
    long_description = fields.TextAreaField()
    url = fields.TextField()
    license = fields.SelectField(choices=license_choices)
    classifiers = fields.SelectMultipleField(choices=classifier_choices)
    readme = fields.HiddenField()

    # lists
    py_modules = ModulesField()
    packages = PackagesField()
    requires = RequiresField()

    def __init__(self, *args, **kwargs):
        super(Setup, self).__init__(*args, **kwargs)

        self.cache_key = str(uuid()).replace('-', '')

        for field in [self.license, self.classifiers]:
            if field.data == 'None':
                field.data = None

    def process(self, formdata=None, obj=None, **kwargs):
        super(Setup, self).process(formdata=formdata, obj=obj, **kwargs)

    def cache(self):
        data = dict(self.data)
        data['cache_key'] = self.cache_key

        cache.set(self.cache_key, json.dumps(data))

    def visible_fields(self):
        return [f for f in self if not isinstance(f, fields.HiddenField)]


class SetupDistutils(Setup):

    def generate(self, executable=False, under_test=False):
        try:
            indent = '    '
            args = ''

            for field in self.visible_fields():
                # don't show field at all if executable is on
                if not field.data and executable:
                    continue

                args += u'{}{}\n'.format(
                    indent,
                    show_field(field, self, executable))

            return safe_string(template(SETUP_PY_TEMPLATE,
                                        setup=self,
                                        executable=executable,
                                        setup_arguments=args,
                                        under_test=under_test))
        except Exception:
            log.exception('Failed to generate setup.py')
            return 'Error generating setup.py'
