from django.db import models


class EventManager(models.Manager):
    def get_queryset(self):
        """
        Provide the base queryset with related `courses` and `fees` prefetched.
        
        Returns:
            QuerySet: A queryset of Event instances with the `courses` and `fees` relations prefetched to reduce database queries.
        """
        return (
            super().get_queryset().prefetch_related("courses").prefetch_related("fees")
        )

    def clone(self, original, start_date):
        """
        Create a duplicate of an existing Event with a new start date and persist it.
        
        The new event preserves the original's attributes but uses the provided start_date (and sets season to its year). If the original event's registration_type is not "N", signup, payment, and priority signup date fields are shifted by the same time delta between the new and original start dates. External URL fields (portal_url and external_url) are cleared. The new event is saved to the database, its course relations are copied, and fees are duplicated as new records associated with the new event.
        
        Parameters:
            original (Event): The Event instance to duplicate.
            start_date (date or datetime): The start date for the new Event.
        
        Returns:
            Event: The newly created and saved Event copy.
        """
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
                copy.priority_signup_start = (
                    original.priority_signup_start + start_delta
                )

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
        # if copy.can_choose and copy.registration_window == "future":
        #     copy.registrations.remove_slots_for_event(copy)
        #     copy.registrations.create_slots_for_event(copy)

        return copy


class EventFeeManager(models.Manager):
    def get_queryset(self):
        """
        Provide a queryset of EventFee objects with the related 'fee_type' loaded.
        
        Returns:
            QuerySet: EventFee queryset with the related `fee_type` included via `select_related`.
        """
        return super().get_queryset().select_related("fee_type")