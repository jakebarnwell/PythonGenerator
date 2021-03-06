import datetime
from datetime import timedelta

from django.test import TestCase
from django.forms.models import model_to_dict
from django.contrib.auth import models as auth_models
from django.core.exceptions import ValidationError

from conference import models as conference_models
from speakers import models as speakers_models

from . import models
from . import forms
from . import validators


class SubmissionTests(TestCase):
    def setUp(self):
        self.conference = conference_models.Conference(title="TestCon")
        self.conference.save()
        self.audience_level = conference_models.AudienceLevel(level=1,
            name='Level 1', conference=self.conference)
        self.audience_level.save()
        self.kind = conference_models.SessionKind(
            conference=self.conference,
            closed=False
        )
        self.kind.save()
        self.duration = conference_models.SessionDuration(
            minutes=30,
            conference=self.conference)
        self.duration.save()
        self.user = auth_models.User.objects.create_user('test', 'test@test.com',
            'testpassword')
        speakers_models.Speaker.objects.all().delete()
        self.speaker = speakers_models.Speaker(user=self.user)
        self.speaker.save()
        self.track = conference_models.Track(name="NAME", slug="SLUG", conference=self.conference)
        self.track.save()
        self.now = datetime.datetime.now()

    def tearDown(self):
        self.conference.delete()
        self.user.delete()
        self.speaker.delete()
        self.track.delete()

    def test_with_open_sessionkind(self):
        """
        Tests that a proposal can be submitted with an open sessionkind
        """
        proposal = models.Proposal(
            conference=self.conference,
            title="Proposal",
            description="DESCRIPTION",
            abstract="ABSTRACT",
            speaker=self.speaker,
            kind=self.kind,
            audience_level=self.audience_level,
            duration=self.duration,
            track=self.track
        )
        data = model_to_dict(proposal)
        data['agree_to_terms'] = True
        form = forms.ProposalSubmissionForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        now = datetime.datetime.now()
        self.kind.start_date = now - datetime.timedelta(1)
        self.kind.end_date = now + datetime.timedelta(1)
        self.kind.save()

        data = model_to_dict(proposal)
        data['agree_to_terms'] = True
        form = forms.ProposalSubmissionForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_with_closed_sessionkind(self):
        proposal = models.Proposal(
            conference=self.conference,
            title="Proposal",
            description="DESCRIPTION",
            abstract="ABSTRACT",
            speaker=self.speaker,
            kind=self.kind,
            audience_level=self.audience_level,
            duration=self.duration,
            track=self.track
        )
        self.kind.start_date = self.now - timedelta(2)
        self.kind.end_date = self.now - timedelta(1)
        self.kind.closed = None
        self.kind.save()
        form = forms.ProposalSubmissionForm(data=model_to_dict(proposal))
        self.assertFalse(form.is_valid())

        self.kind.start_date = None
        self.kind.end_date = None
        self.kind.closed = True
        self.kind.save()
        form = forms.ProposalSubmissionForm(data=model_to_dict(proposal))
        self.assertFalse(form.is_valid(), form.errors)


class MaxWordsValidatorTests(TestCase):
    def test_too_long(self):
        v = validators.MaxWordsValidator(3)
        self.assertRaises(ValidationError, v, "this is a bit too long")

    def test_ok_with_signs(self):
        v = validators.MaxWordsValidator(3)
        v("hi! hello... world!")

    def test_ok(self):
        v = validators.MaxWordsValidator(2)
        v("hello world!")

    def test_ok_with_whitespaces(self):
        v = validators.MaxWordsValidator(2)
        v("hello    \n   \t world!")
