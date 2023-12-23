from django.db import models


class EventManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related("courses").prefetch_related("fees")

    def clone(self, original, start_date):
        copy = self.get(pk=original.id)
        copy.pk = None
        copy.start_date = start_date
        copy.season = start_date.year

        # relative dates/times
        if original.registration_type != "N":
            start_delta = start_date - original.start_date
            copy.signup_start = original.signup_start + start_delta
            copy.signup_end = original.signup_end + start_delta
            if original.payments_end is not None:
                copy.payments_end = original.payments_end + start_delta
            if original.priority_signup_start is not None:
                copy.priority_signup_start = original.priority_signup_start + start_delta

        # remove url values
        copy.portal_url = None
        copy.external_url = None

        copy.save()

        # courses
        copy.courses.add(*original.courses.all())

        # copy (creating new) fees
        fees = original.fees.filter(event_id=original.id)
        for fee in fees:
            fee.event_id = copy.id
            fee.pk = None
            fee.save()

        # safe to create registration slots now that courses have been created
        if copy.can_choose and copy.registration_window == "future":
            copy.registrations.remove_slots_for_event(copy)
            copy.registrations.create_slots_for_event(copy)

        return copy


class EventFeeManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related("fee_type")
