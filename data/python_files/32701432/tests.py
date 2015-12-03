import unittest
import transaction

from pyramid import testing

from .models import DBSession, Session, Event
import json


class TestMyView(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        from sqlalchemy import create_engine
        engine = create_engine('sqlite://')
        from .models import (
            Base,
            Session,
            Event
            )
        DBSession.configure(bind=engine)
        Base.metadata.create_all(engine)

    def tearDown(self):
        DBSession.remove()
        testing.tearDown()

    def test_it(self):
        from .views import track
        request = testing.DummyRequest()
        request.POST = {'data':"W3siZXZlbnQiOiJBY3Rpb246IFRhcHBlZCBvbiBGZWVkIFRhYiIsInByb3BlcnRpZXMiOnsiZGlzdGluY3RfaWQiOiJjY2NkMjNiN2UzZTI5YTM0ZDAzYmVhNDQxYWVlYmRmNWM2Y2U5Mzg3Iiwic3lzdGVtX25hbWUiOiJpUGhvbmUgT1MiLCJ0aW1lIjoxMzI5NDUyNjE0LCJtcF9saWIiOiJpcGhvbmUiLCJwcm9maWxlX3BhdGgiOiJOaXNoLUJoYXQiLCJzeXN0ZW1fdmVyc2lvbiI6IjQuMyIsIm1vZGVsIjoiaVBob25lIFNpbXVsYXRvciIsIm1wX25hbWVfdGFnIjoiTmlzaCBCaGF0IC0gaVBob25lIFNpbXVsYXRvciA0LjMiLCJleHRlcm5hbF9pZCI6ImMtbVh6TGZWUnF1dUl5T012RFBlYUEiLCJhcHBfdmVyc2lvbiI6InYxLjAtMTA5OS1nYjBhYzQ4NCIsInRva2VuIjoiMGViOWI5OGMxNWViZDdkOTg5Y2ViODRjMWZjYzhlYWYiLCJ0YWJfYmFyX25hbWUiOiJGZWVkIn19LHsiZXZlbnQiOiJBY3Rpb246IFRhcHBlZCBvbiBNZSBUYWIiLCJwcm9wZXJ0aWVzIjp7ImRpc3RpbmN0X2lkIjoiY2NjZDIzYjdlM2UyOWEzNGQwM2JlYTQ0MWFlZWJkZjVjNmNlOTM4NyIsInN5c3RlbV9uYW1lIjoiaVBob25lIE9TIiwidGltZSI6MTMyOTQ1MjYxNSwibXBfbGliIjoiaXBob25lIiwicHJvZmlsZV9wYXRoIjoiTmlzaC1CaGF0Iiwic3lzdGVtX3ZlcnNpb24iOiI0LjMiLCJtb2RlbCI6ImlQaG9uZSBTaW11bGF0b3IiLCJtcF9uYW1lX3RhZyI6Ik5pc2ggQmhhdCAtIGlQaG9uZSBTaW11bGF0b3IgNC4zIiwiZXh0ZXJuYWxfaWQiOiJjLW1YekxmVlJxdXVJeU9NdkRQZWFBIiwiYXBwX3ZlcnNpb24iOiJ2MS4wLTEwOTktZ2IwYWM0ODQiLCJ0b2tlbiI6IjBlYjliOThjMTVlYmQ3ZDk4OWNlYjg0YzFmY2M4ZWFmIiwidGFiX2Jhcl9uYW1lIjoiTWUifX0seyJldmVudCI6IkFjdGlvbjogVGFwcGVkIG9uIEZlZWQgVGFiIiwicHJvcGVydGllcyI6eyJkaXN0aW5jdF9pZCI6ImNjY2QyM2I3ZTNlMjlhMzRkMDNiZWE0NDFhZWViZGY1YzZjZTkzODciLCJzeXN0ZW1fbmFtZSI6ImlQaG9uZSBPUyIsInRpbWUiOjEzMjk0NTI2MTYsIm1wX2xpYiI6ImlwaG9uZSIsInByb2ZpbGVfcGF0aCI6Ik5pc2gtQmhhdCIsInN5c3RlbV92ZXJzaW9uIjoiNC4zIiwibW9kZWwiOiJpUGhvbmUgU2ltdWxhdG9yIiwibXBfbmFtZV90YWciOiJOaXNoIEJoYXQgLSBpUGhvbmUgU2ltdWxhdG9yIDQuMyIsImV4dGVybmFsX2lkIjoiYy1tWHpMZlZScXV1SXlPTXZEUGVhQSIsImFwcF92ZXJzaW9uIjoidjEuMC0xMDk5LWdiMGFjNDg0IiwidG9rZW4iOiIwZWI5Yjk4YzE1ZWJkN2Q5ODljZWI4NGMxZmNjOGVhZiIsInRhYl9iYXJfbmFtZSI6IkZlZWQifX0seyJldmVudCI6IkFjdGlvbjogVGFwcGVkIG9uIEV4cGxvcmUgVGFiIiwicHJvcGVydGllcyI6eyJkaXN0aW5jdF9pZCI6ImNjY2QyM2I3ZTNlMjlhMzRkMDNiZWE0NDFhZWViZGY1YzZjZTkzODciLCJzeXN0ZW1fbmFtZSI6ImlQaG9uZSBPUyIsInRpbWUiOjEzMjk0NTI2MjAsIm1wX2xpYiI6ImlwaG9uZSIsInByb2ZpbGVfcGF0aCI6Ik5pc2gtQmhhdCIsInN5c3RlbV92ZXJzaW9uIjoiNC4zIiwibW9kZWwiOiJpUGhvbmUgU2ltdWxhdG9yIiwibXBfbmFtZV90YWciOiJOaXNoIEJoYXQgLSBpUGhvbmUgU2ltdWxhdG9yIDQuMyIsImV4dGVybmFsX2lkIjoiYy1tWHpMZlZScXV1SXlPTXZEUGVhQSIsImFwcF92ZXJzaW9uIjoidjEuMC0xMDk5LWdiMGFjNDg0IiwidG9rZW4iOiIwZWI5Yjk4YzE1ZWJkN2Q5ODljZWI4NGMxZmNjOGVhZiIsInRhYl9iYXJfbmFtZSI6IkV4cGxvcmUifX0seyJldmVudCI6IkFjdGlvbjogVGFwcGVkIG9uIEZlYXR1cmVkIFRhYiIsInByb3BlcnRpZXMiOnsiZGlzdGluY3RfaWQiOiJjY2NkMjNiN2UzZTI5YTM0ZDAzYmVhNDQxYWVlYmRmNWM2Y2U5Mzg3Iiwic3lzdGVtX25hbWUiOiJpUGhvbmUgT1MiLCJ0aW1lIjoxMzI5NDUyNjIxLCJtcF9saWIiOiJpcGhvbmUiLCJwcm9maWxlX3BhdGgiOiJOaXNoLUJoYXQiLCJzeXN0ZW1fdmVyc2lvbiI6IjQuMyIsIm1vZGVsIjoiaVBob25lIFNpbXVsYXRvciIsIm1wX25hbWVfdGFnIjoiTmlzaCBCaGF0IC0gaVBob25lIFNpbXVsYXRvciA0LjMiLCJleHRlcm5hbF9pZCI6ImMtbVh6TGZWUnF1dUl5T012RFBlYUEiLCJhcHBfdmVyc2lvbiI6InYxLjAtMTA5OS1nYjBhYzQ4NCIsInRva2VuIjoiMGViOWI5OGMxNWViZDdkOTg5Y2ViODRjMWZjYzhlYWYiLCJ0YWJfYmFyX25hbWUiOiJGZWF0dXJlZCJ9fSx7ImV2ZW50IjoiQWN0aW9uOiBUYXBwZWQgb24gRXhwbG9yZSBUYWIiLCJwcm9wZXJ0aWVzIjp7ImRpc3RpbmN0X2lkIjoiY2NjZDIzYjdlM2UyOWEzNGQwM2JlYTQ0MWFlZWJkZjVjNmNlOTM4NyIsInN5c3RlbV9uYW1lIjoiaVBob25lIE9TIiwidGltZSI6MTMyOTQ1MjYyMiwibXBfbGliIjoiaXBob25lIiwicHJvZmlsZV9wYXRoIjoiTmlzaC1CaGF0Iiwic3lzdGVtX3ZlcnNpb24iOiI0LjMiLCJtb2RlbCI6ImlQaG9uZSBTaW11bGF0b3IiLCJtcF9uYW1lX3RhZyI6Ik5pc2ggQmhhdCAtIGlQaG9uZSBTaW11bGF0b3IgNC4zIiwiZXh0ZXJuYWxfaWQiOiJjLW1YekxmVlJxdXVJeU9NdkRQZWFBIiwiYXBwX3ZlcnNpb24iOiJ2MS4wLTEwOTktZ2IwYWM0ODQiLCJ0b2tlbiI6IjBlYjliOThjMTVlYmQ3ZDk4OWNlYjg0YzFmY2M4ZWFmIiwidGFiX2Jhcl9uYW1lIjoiRXhwbG9yZSJ9fSx7ImV2ZW50IjoiQWN0aW9uOiBWaWV3ZWQgR3VpZGUiLCJwcm9wZXJ0aWVzIjp7ImRpc3RpbmN0X2lkIjoiY2NjZDIzYjdlM2UyOWEzNGQwM2JlYTQ0MWFlZWJkZjVjNmNlOTM4NyIsInRpdGxlIjoibWFrZSBxdWljayBwaWNrbGVkIHB1cnBsZSBjYXVsaWZsb3dlciIsInN5c3RlbV9uYW1lIjoiaVBob25lIE9TIiwibXBfbGliIjoiaXBob25lIiwidGltZSI6MTMyOTQ1MjYyMywicHJvZmlsZV9wYXRoIjoiTmlzaC1CaGF0Iiwic3lzdGVtX3ZlcnNpb24iOiI0LjMiLCJtb2RlbCI6ImlQaG9uZSBTaW11bGF0b3IiLCJtcF9uYW1lX3RhZyI6Ik5pc2ggQmhhdCAtIGlQaG9uZSBTaW11bGF0b3IgNC4zIiwiZXh0ZXJuYWxfaWQiOiJjLW1YekxmVlJxdXVJeU9NdkRQZWFBIiwidXVpZCI6IjhmZDk1MGIyMmE2ZTQ2YTdhODU2N2JhYTlmZDNmZjlhIiwiYXBwX3ZlcnNpb24iOiJ2MS4wLTEwOTktZ2IwYWM0ODQiLCJtcF9ub3RlIjoibWFrZSBxdWljayBwaWNrbGVkIHB1cnBsZSBjYXVsaWZsb3dlciIsInRva2VuIjoiMGViOWI5OGMxNWViZDdkOTg5Y2ViODRjMWZjYzhlYWYifX1d"}
        info = track(request)
        dbsession = DBSession()
        session = dbsession.query(Session).all()[0]
        event = dbsession.query(Event).filter_by(time=1329452615).all()[0]
        self.assertEqual(session.time, 1329452623)
        self.assertEqual(event.name, "Action: Tapped on Me Tab")
        self.assertEqual(session.profile_path, "Nish-Bhat")
        self.assertEqual(session.token,"0eb9b98c15ebd7d989ceb84c1fcc8eaf")