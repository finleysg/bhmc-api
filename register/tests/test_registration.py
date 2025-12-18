import json

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase, RequestFactory
from django.utils import timezone as tz
from http import HTTPStatus
from rest_framework.test import APIClient
from unittest import mock, skip

from events.models import Event
from register.models import RegistrationSlot, Registration


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


class RegistrationTests(TestCase):
    fixtures = ["fee_type", "event", "event_fee", "registration_slot", "course", "hole", "user", "player"]

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.get(email="finleysg@gmail.com")

    # Test for CREATE/POST ###
    def test_season_registration_create(self):
        update_event_to_registering(event_id=1)
        data = json.dumps({
            "event": 1,
            "slots": []
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/registration/", data=data, content_type="application/json")
        # 201 Created
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        # Registration created
        self.assertEqual(response.data["event"], 1)
        self.assertEqual(response.data["signed_up_by"], "Stuart Finley")
        self.assertEqual(len(response.data["slots"]), 1)
        self.assertEqual(response.data["slots"][0]["status"], "P")
        self.assertEqual(response.data["slots"][0]["player"]["id"], 1)  # default to current player on first slot

    @skip("not working")
    def test_season_registration_update(self):
        update_event_to_registering(event_id=1)
        data = json.dumps({
            "event": 1,
            "slots": []
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/registration/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        new_id = response.data["id"]
        update = response.data
        update["notes"] = "hello!"
        response = client.put("/api/registration/{}/".format(new_id),
                              data=json.dumps(update),
                              content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual("hello!", response.data["notes"])
        self.assertIsNotNone(response.data["slots"][0]["player"])

    @skip("not working")
    @mock.patch("stripe.PaymentIntent.create")
    def test_registration_payment(self, mock_intent):
        update_event_to_registering(event_id=1)
        data = json.dumps({
            "event": 1,
            "slots": []
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/registration/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        new_id = response.data["id"]
        update = response.data
        update["notes"] = "hello!"
        response = client.put("/api/registration/{}/".format(new_id),
                              data=json.dumps(update),
                              content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        slot_id = response.data["slots"][0]["id"]
        mock_intent.return_value.stripe_id = "stripe_id"
        mock_intent.return_value.client_secret = "client_secret"
        payment_data = json.dumps({
            "event": 1,
            "user": 1,
            "notification_type": "R",
            "payment_details": [
                {
                    "event_fee": 1,
                    "registration_slot": slot_id
                },
                {
                    "event_fee": 3,
                    "registration_slot": slot_id
                }
            ]
        })

        response = client.post("/api/payments/", data=payment_data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    def test_weeknight_registration_create(self):
        update_event_to_registering(event_id=3)
        data = json.dumps({
            "event": 3,
            "course": 1,
            "slots": [
                {
                    "event": 3,
                    "id": 1,
                    "starting_order": 0,
                    "slot": 0,
                    "status": "A",
                    "hole": 1,
                    "player": None
                },
                {
                    "event": 3,
                    "id": 2,
                    "starting_order": 0,
                    "slot": 1,
                    "status": "A",
                    "hole": 1,
                    "player": None
                },
                {
                    "event": 3,
                    "id": 3,
                    "starting_order": 0,
                    "slot": 2,
                    "status": "A",
                    "hole": 1,
                    "player": None
                }
            ]
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/registration/", data=data, content_type="application/json")
        # 201 Created
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        # Registration created
        self.assertEqual(response.data["event"], 3)
        self.assertEqual(response.data["signed_up_by"], "Stuart Finley")
        self.assertEqual(len(response.data["slots"]), 3)
        self.assertEqual(response.data["slots"][0]["status"], "P")
        self.assertEqual(response.data["slots"][0]["player"]["id"], 1)

    @skip("not working")
    def test_weeknight_registration_update(self):
        update_event_to_registering(event_id=3)
        data = json.dumps({
            "event": 3,
            "course": 1,
            "slots": [
                {
                    "event": 3,
                    "id": 1,
                    "starting_order": 0,
                    "slot": 0,
                    "status": "A",
                    "hole_id": 1
                },
                {
                    "event": 3,
                    "id": 2,
                    "starting_order": 0,
                    "slot": 1,
                    "status": "A",
                    "hole_id": 1
                },
                {
                    "event": 3,
                    "id": 3,
                    "starting_order": 0,
                    "slot": 2,
                    "status": "A",
                    "hole_id": 1
                }
            ]
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/registration/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        new_id = response.data["id"]
        update = response.data
        update["notes"] = "test"
        response = client.put("/api/registration/{}/".format(new_id),
                              data=json.dumps(update),
                              content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data["notes"], "test")

    def test_registration_not_started(self):
        update_event_to_future(event_id=4)
        data = json.dumps({
            "event": 4,
            "slots": []
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/registration/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.data["detail"], "The event is not currently open for registration")

    def test_event_is_full(self):
        event = update_event_to_registering(event_id=4)
        event.registration_maximum = 1
        event.save()

        slot = RegistrationSlot(event_id=4, starting_order=0, status="R")
        slot.save()

        data = json.dumps({
            "event": 4,
            "slots": []
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/registration/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.data["detail"], "The event field is full")

    @skip("not working")
    def test_cancel_registration(self):
        update_event_to_registering(event_id=4)
        data = json.dumps({
            "event": 4,
            "slots": []
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/registration/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        new_id = response.data["id"]
        update = response.data
        update["notes"] = "this will be canceled"
        response = client.put("/api/registration/{}/".format(new_id),
                              data=json.dumps(update),
                              content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.OK)

        response = client.put("/api/registration/{}/cancel/".format(new_id))

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

        try:
            Registration.objects.get(pk=new_id)
        except ObjectDoesNotExist:
            is_none = True
            self.assertTrue(is_none)

        slots = RegistrationSlot.objects.filter(registration=new_id)
        self.assertEqual(len(slots), 0)

    def test_cancel_weeknight_registration(self):
        update_event_to_registering(event_id=3)
        data = json.dumps({
            "event": 3,
            "course": 1,
            "slots": [
                {
                    "event": 3,
                    "id": 1,
                    "starting_order": 0,
                    "slot": 0,
                    "status": "A",
                    "hole": 1,
                    "player": None
                },
                {
                    "event": 3,
                    "id": 2,
                    "starting_order": 0,
                    "slot": 1,
                    "status": "A",
                    "hole": 1,
                    "player": None
                },
                {
                    "event": 3,
                    "id": 3,
                    "starting_order": 0,
                    "slot": 2,
                    "status": "A",
                    "hole": 1,
                    "player": None
                }
            ]
        })
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/registration/", data=data, content_type="application/json")

        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        new_id = response.data["id"]
        response = client.put("/api/registration/{}/cancel/".format(new_id))

        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

        try:
            Registration.objects.get(pk=new_id)
        except ObjectDoesNotExist:
            is_none = True
            self.assertTrue(is_none)

        slot = RegistrationSlot.objects.get(pk=1)
        self.assertEqual(slot.status, "A")
