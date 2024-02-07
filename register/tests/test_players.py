import json

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.utils import timezone as tz
from http import HTTPStatus
from rest_framework.test import APIClient
from unittest import mock, skip

from events.models import Event


def update_event_to_registering(event_id):
    event = Event.objects.get(pk=event_id)
    event.start_date = date.today() + timedelta(days=7)
    event.signup_start = tz.now() - timedelta(days=2)
    event.signup_end = tz.now() + timedelta(days=2)
    event.save()
    return event


def update_event_to_future(event_id):
    event = Event.objects.get(pk=event_id)
    event.start_date = date.today() + timedelta(days=14)
    event.signup_start = tz.now() + timedelta(days=1)
    event.signup_end = tz.now() + timedelta(days=10)
    event.save()


class PlayerViewTests(TestCase):
    fixtures = ["player", "user"]

    def setUp(self):
        self.factory = RequestFactory()

    def test_can_create_player(self):
        self.user = User.objects.get(email="finleysg@gmail.com")
        data = json.dumps({
            "first_name": "Tiger",
            "last_name": "Woods",
            "email": "tw@golf.com",
            "ghin": "1234567"
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/players/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertIsNotNone(response.data["id"])

    def test_can_update_self(self):
        self.user = User.objects.get(email="hogan@golf.com")
        data = json.dumps({
            "id": 2,
            "first_name": "Ben",
            "last_name": "Hogan",
            "email": "hogan@golf.com",
            "ghin": "1234567",
            "tee": "Club",
            "favorites": []
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.put("/api/players/2/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data["ghin"], "1234567")

    def test_cannot_update_other_player(self):
        self.user = User.objects.get(email="finleysg@gmail.com")
        data = json.dumps({
            "id": 2,
            "first_name": "Ben",
            "last_name": "Hogan",
            "email": "hogan@golf.com",
            "ghin": "1234567",
            "tee": "Club",
            "favorites": []
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.put("/api/players/2/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertTrue("To update a player, use the admin website" in response.data["non_field_errors"][0])

    def test_cannot_duplicate_email(self):
        self.user = User.objects.get(email="finleysg@gmail.com")
        data = json.dumps({
            "first_name": "Ben",
            "last_name": "Hogan",
            "email": "hogan@golf.com",
            "ghin": "1234567",
            "tee": "Club"
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/players/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertTrue("player with this Email already exists" in response.data["email"][0])

    def test_cannot_duplicate_ghin(self):
        self.user = User.objects.get(email="finleysg@gmail.com")
        data = json.dumps({
            "first_name": "New",
            "last_name": "Player",
            "email": "new-guy@golf.com",
            "ghin": "125741",
            "tee": "Club"
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/players/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertTrue("player with this GHIN already exists" in response.data["ghin"][0])

    @skip("not working")
    def test_add_friends(self):
        self.user = User.objects.get(email="finleysg@gmail.com")
        client = APIClient()
        client.force_authenticate(user=self.user)

        response = client.post("/api/friends/add/2/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data[0]["email"], "hogan@golf.com")

    # def test_get_friends(self):
    #     self.user = User.objects.get(email="finleysg@gmail.com")
    #     client = APIClient()
    #     client.force_authenticate(user=self.user)
    #
    #     client.post("/api/friends/add/2/")
    #     client.post("/api/friends/add/3/")
    #     response = client.get("/api/friends/1/")
    #
    #     self.assertEqual(response.status_code, HTTPStatus.OK)
    #     self.assertEqual(len(response.data), 2)

    @skip("not working")
    def test_remove_friends(self):
        self.user = User.objects.get(email="finleysg@gmail.com")
        client = APIClient()
        client.force_authenticate(user=self.user)

        client.post("/api/friends/add/2/")
        client.post("/api/friends/add/3/")
        response = client.delete("/api/friends/remove/2/")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.data), 1)
