from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, models
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .api_serializers import POSOrderCreateSerializer, POSOrderSerializer
from .models import POSOrder, POSOrderLine, POSSession
from inventory.models import Product, Location
from partners.models import Customer
from showrooms.models import Showroom, ShowroomEmployee
from showrooms.mixins import get_active_showroom_id

class POSOrderCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        ser = POSOrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        sid = get_active_showroom_id(request)
        if sid is None:
            return Response({'detail':'showroom required'}, status=status.HTTP_400_BAD_REQUEST)
        # تحقق من تعيين المستخدم للمعرض
        if not (request.user.is_superuser or ShowroomEmployee.objects.filter(user=request.user, active=True).filter(Q(showroom_id=sid) | Q(can_cross_access=True)).exists()):
            return Response({'detail':'not assigned to showroom'}, status=status.HTTP_403_FORBIDDEN)
        with transaction.atomic():
            session = POSSession.objects.filter(user=request.user, is_open=True, location__showroom_link__id=sid).first()
            if not session:
                location = Location.objects.filter(showroom_link_id=sid).first()
                if not location:
                    return Response({'detail':'no location for showroom'}, status=status.HTTP_400_BAD_REQUEST)
                session = POSSession.objects.create(user=request.user, opening_balance=0, location=location)
            location = session.location
            if data.get('location_id'):
                # السماح بتغيير الموقع داخل نفس المعرض فقط
                loc = get_object_or_404(Location, pk=data['location_id'])
                if loc.showroom_id != sid:
                    return Response({'detail':'location not in showroom'}, status=status.HTTP_403_FORBIDDEN)
                location = loc
            order = POSOrder.objects.create(session=session, location=location, is_return=data.get('is_return', False))
            if data.get('original_order_id') and order.is_return:
                try:
                    order.original_order_id = data['original_order_id']
                    order.save(update_fields=['original_order'])
                except Exception:
                    pass
            if data.get('customer_id'):
                try:
                    order.customer_id = data['customer_id']
                    order.save(update_fields=['customer'])
                except Exception:
                    pass
            # add lines
            for ln in data['lines']:
                product = get_object_or_404(Product, pk=ln['product_id'])
                POSOrderLine.objects.create(order=order, product=product, quantity=ln['quantity'], price=ln['price'])
            order.finalize_payment(data['paid_amount'], discount=data.get('discount') or 0, vat_rate=data.get('vat_rate') or 0)
            return Response(POSOrderSerializer(order).data, status=status.HTTP_201_CREATED)

class POSOrderListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        sid = get_active_showroom_id(request)
        qs = POSOrder.objects.select_related('showroom','location','customer').order_by('-id')
        if sid:
            qs = qs.filter(showroom_id=sid)
        qs = qs[:50]
        return Response(POSOrderSerializer(qs, many=True).data)
