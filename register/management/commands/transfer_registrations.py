from uuid import uuid4
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from register.models import Registration, RegistrationSlot, RegistrationFee
from events.models import Event, EventFee
from payments.models import Payment


class Command(BaseCommand):
    help = "Transfer registrations from one event to another. Development use only."

    def add_arguments(self, parser):
        """
        Add command-line arguments required by the transfer_registrations management command.
        
        Parameters:
            parser: argparse.ArgumentParser
                The parser to which the command adds:
                  - source_event_id (int): positional ID of the source event to transfer from.
                  - dest_event_id (int): positional ID of the destination event to transfer to.
                  - --dry-run / --dry-run (flag): when provided, show actions without committing changes.
        """
        parser.add_argument("source_event_id", type=int)
        parser.add_argument("dest_event_id", type=int)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Show what would be done without committing changes",
        )

    def handle(self, *args, **options):
        """
        Transfer registrations, slots, payments, and fees from one event to another based on CLI options.
        
        Creates a new Registration for each registration on the source event, reassigns matching destination RegistrationSlot entries to the new registration (matching by hole, starting_order, and slot), duplicates Payments once per source Payment and associates them with the destination event, and recreates RegistrationFee records linked to the corresponding destination EventFee. If `dry_run` is True, all database changes are rolled back at the end of the command.
        
        Parameters:
            options (dict): Command options; must include:
                - "source_event_id" (int): primary key of the source Event.
                - "dest_event_id" (int): primary key of the destination Event.
                - "dry_run" (bool, optional): if True, perform a trial run and roll back changes.
        
        Raises:
            CommandError: if the source or destination Event does not exist;
                          if a destination slot lookup does not return exactly one slot;
                          if a matching EventFee on the destination event cannot be found.
        
        Returns:
            None
        """
        src_id = options["source_event_id"]
        dst_id = options["dest_event_id"]
        dry_run = options.get("dry_run", False)

        try:
            source_event = Event.objects.get(pk=src_id)
        except Event.DoesNotExist:
            raise CommandError(f"Source event {src_id} does not exist")

        try:
            dest_event = Event.objects.get(pk=dst_id)
        except Event.DoesNotExist:
            raise CommandError(f"Destination event {dst_id} does not exist")

        regs = Registration.objects.filter(event=source_event)
        total_regs = regs.count()
        self.stdout.write(f"Found {total_regs} registrations to transfer from {source_event} to {dest_event}")

        stats = {
            "registrations_created": 0,
            "slots_updated": 0,
            "payments_created": 0,
            "fees_created": 0,
        }

        with transaction.atomic():
            for reg in regs:
                new_reg = Registration.objects.create(
                    event=dest_event,
                    course=reg.course,
                    user=reg.user,
                    signed_up_by=reg.signed_up_by,
                    expires=None,
                    notes=reg.notes,
                    # Do not copy gg_id/created_date - dev-only data
                )
                stats["registrations_created"] += 1
                self.stdout.write(f"Created registration {new_reg.pk} (src {reg.pk})")

                source_slots = reg.slots.all()

                # Map source payment PK -> new Payment so one payment is created per source payment
                payment_mapping = {}

                for s in source_slots:
                    dst_slots_qs = RegistrationSlot.objects.filter(
                        event=dest_event, hole=s.hole, starting_order=s.starting_order, slot=s.slot
                    )

                    dst_count = dst_slots_qs.count()
                    if dst_count != 1:
                        raise CommandError(
                            f"Expected exactly one destination slot for hole_id={getattr(s.hole, 'id', None)}, "
                            f"starting_order={s.starting_order}, slot={s.slot} but found {dst_count}"
                        )

                    dst_slot = dst_slots_qs.first()
                    dst_slot.status = s.status
                    dst_slot.player = s.player
                    dst_slot.registration = new_reg
                    dst_slot.save()
                    stats["slots_updated"] += 1
                    self.stdout.write(f"Updated dest slot {dst_slot.pk} from src slot {s.pk}")

                    for fee in s.fees.all():
                        src_payment = fee.payment
                        if src_payment is None:
                            new_payment = None
                        else:
                            src_pid = src_payment.pk
                            if src_pid in payment_mapping:
                                new_payment = payment_mapping[src_pid]
                            else:
                                new_payment = Payment.objects.create(
                                    payment_code=uuid4().hex[:40],
                                    payment_key=uuid4().hex,
                                    payment_amount=src_payment.payment_amount,
                                    transaction_fee=src_payment.transaction_fee,
                                    event=dest_event,
                                    user=src_payment.user,
                                    notification_type=src_payment.notification_type,
                                    confirmed=src_payment.confirmed,
                                    confirm_date=src_payment.confirm_date,
                                )
                                payment_mapping[src_pid] = new_payment
                                stats["payments_created"] += 1
                                self.stdout.write(
                                    f"Created payment {new_payment.pk} for src payment {src_payment.pk}"
                                )

                        # find corresponding event fee on destination event by fee_type
                        try:
                            dst_event_fee = EventFee.objects.get(event=dest_event, fee_type=fee.event_fee.fee_type)
                        except EventFee.DoesNotExist:
                            raise CommandError(
                                f"No matching EventFee for fee_type_id={fee.event_fee.fee_type_id} on destination event {dest_event.pk}"
                            )

                        new_fee = RegistrationFee.objects.create(
                            event_fee=dst_event_fee,
                            registration_slot=dst_slot,
                            is_paid=fee.is_paid,
                            amount=fee.amount,
                            payment=new_payment,
                        )
                        stats["fees_created"] += 1
                        self.stdout.write(f"Created registration fee {new_fee.pk} for slot {dst_slot.pk}")

            if dry_run:
                # mark transaction for rollback so nothing is committed
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("Dry run requested — rolling back all changes"))

        self.stdout.write(self.style.SUCCESS(
            f"Done. Registrations created: {stats['registrations_created']}, "
            f"Slots updated: {stats['slots_updated']}, Payments created: {stats['payments_created']}, "
            f"Fees created: {stats['fees_created']}"
        ))