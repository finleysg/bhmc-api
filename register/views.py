from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from .models import Registration, RegistrationSlot, Player
from .serializers import RegistrationSlotSerializer, RegistrationSerializer, PlayerSerializer


class PlayerViewSet(viewsets.ModelViewSet):
    serializer_class = PlayerSerializer
    queryset = Player.objects.all()

    def get_serializer_context(self):
        context = super(PlayerViewSet, self).get_serializer_context()
        return context


class RegistrationViewSet(viewsets.ModelViewSet):

    serializer_class = RegistrationSerializer

    def get_queryset(self):
        queryset = Registration.objects.all()
        event_id = self.request.query_params.get('event_id', None)
        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        return queryset

    def perform_create(self, serializer):
        signed_up_by = self.request.user.get_full_name()
        serializer.save(signed_up_by=signed_up_by, **self.request.data)


class RegistrationSlotViewsSet(viewsets.ModelViewSet):

    serializer_class = RegistrationSlotSerializer

    def get_queryset(self):
        queryset = RegistrationSlot.objects.all()
        event_id = self.request.query_params.get('event_id', None)
        player_id = self.request.query_params.get('player_id', None)
        is_open = self.request.query_params.get('is_open', False)
        if event_id is not None:
            queryset = queryset.filter(event=event_id)
        if player_id is not None:
            queryset = queryset.filter(player=player_id)
        if is_open:
            queryset = queryset.filter(player__isnull=True)
        return queryset


# @api_view(['POST', ])
# @permission_classes((permissions.IsAuthenticated,))
# @transaction.atomic()
# def drop(request):
#
#     slot_id = request.data.get("slot_id", None)
#     refund = request.data.get("refund", False)
#     if slot_id is None:
#         raise ValidationError("A registration slot id is required")
#
#     slot = RegistrationSlot.objects.get(pk=slot_id)
#
#     if refund:
#         group = slot.registration_group
#         admin = request.user.player
#         amount = calculate_refund(slot)
#         logger.info("refund for {} to {} by {}".format(amount, group.signed_up_by, admin))
#         refund_payment(group.id, "group-payment", group.payment_confirmation_code, amount, admin,
#                        "admin approved refund")
#
#     slot.registration_group = None
#     slot.player = None
#     slot.status = "A"
#     slot.is_event_fee_paid = False
#     slot.is_greens_fee_paid = False
#     slot.is_cart_fee_paid = False
#     slot.is_gross_skins_paid = False
#     slot.is_net_skins_paid = False
#     slot.save()
#
#     return Response(status=204)
#
#
# @api_view(['POST', ])
# @permission_classes((permissions.IsAuthenticated,))
# @transaction.atomic()
# def move(request):
#
#     from_slot_id = request.data.get("from", None)
#     to_slot_id = request.data.get("to", None)
#     if from_slot_id is None or to_slot_id is None:
#         raise ValidationError("Both from and to slots are required")
#
#     origin = RegistrationSlot.objects.get(pk=from_slot_id)
#     destination = RegistrationSlot.objects.get(pk=to_slot_id)
#
#     destination.registration_group = origin.registration_group
#     destination.player = origin.player
#     destination.status = "R"
#     destination.is_event_fee_paid = origin.is_event_fee_paid
#     destination.is_greens_fee_paid = origin.is_greens_fee_paid
#     destination.is_cart_fee_paid = origin.is_cart_fee_paid
#     destination.is_gross_skins_paid = origin.is_gross_skins_paid
#     destination.is_net_skins_paid = origin.is_net_skins_paid
#     destination.save()
#
#     origin.registration_group = None
#     origin.player = None
#     origin.status = "A"
#     origin.is_event_fee_paid = False
#     origin.is_greens_fee_paid = False
#     origin.is_cart_fee_paid = False
#     origin.is_gross_skins_paid = False
#     origin.is_net_skins_paid = False
#     origin.save()
#
#     return Response(status=204)


@api_view(['PUT', ])
@permission_classes((permissions.IsAuthenticated,))
def cancel_reserved_slots(request, registration_id):

    if registration_id == 0:
        raise ValidationError("Missing registration_id")

    Registration.objects.cancel_registration(registration_id)

    return Response(status=204)


# @api_view(['POST', ])
# @permission_classes((permissions.IsAuthenticated,))
# @transaction.atomic()
# def add_groups(request):
#
#     # TODO: move to manager
#     event_id = request.data["event_id"]
#     event = get_object_or_404(Event, pk=event_id)
#
#     # select all the holes with only one group
#     holes = list(RegistrationSlot.objects.filter(event=event)
#                  .distinct()
#                  .values_list("course_setup_hole", flat=True)
#                  .annotate(row_count=Count("course_setup_hole"))
#                  .filter(row_count__lte=event.group_size)
#                  .order_by("course_setup_hole"))
#
#     for hole in holes:
#         instance = Hole.objects.get(pk=hole)
#         RegistrationSlot.objects.add_slots(event, instance)
#
#     return Response({"groups_added": len(holes)}, status=201)

#
# @api_view(['POST', ])
# @permission_classes((permissions.IsAuthenticated,))
# @transaction.atomic()
# def remove_row(request):
#
#     event_id = request.data["event_id"]
#     course_setup_hole_id = request.data["course_setup_hole_id"]
#     starting_order = request.data["starting_order"]
#     event = get_object_or_404(Event, pk=event_id)
#     hole = get_object_or_404(CourseSetupHole, pk=course_setup_hole_id)
#
#     RegistrationSlot.objects.remove_hole(event, hole, starting_order)
#
#     return Response(status=204)


@api_view(['GET', ])
@permission_classes((permissions.IsAuthenticated,))
def friends(request):
    player = Player.objects.get(email=request.user.email)
    serializer = PlayerSerializer(player.favorites, context={'request': request}, many=True)
    return Response(serializer.data)


@api_view(['POST', ])
@permission_classes((permissions.IsAuthenticated,))
def add_friend(request, player_id):
    player = Player.objects.get(email=request.user.email)
    friend = get_object_or_404(Player, pk=player_id)
    player.favorites.add(friend)
    player.save()
    serializer = PlayerSerializer(player.favorites, context={'request': request}, many=True)
    return Response(serializer.data)


@api_view(['DELETE', ])
@permission_classes((permissions.IsAuthenticated,))
def remove_friend(request, player_id):
    player = Player.objects.get(email=request.user.email)
    friend = get_object_or_404(Player, pk=player_id)
    player.favorites.remove(friend)
    player.save()
    serializer = PlayerSerializer(player.favorites, context={'request': request}, many=True)
    return Response(serializer.data)
