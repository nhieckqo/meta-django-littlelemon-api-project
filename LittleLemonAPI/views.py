from django.forms import ValidationError
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User, Group
from rest_framework.authtoken.models import Token
from django.db import transaction
from djoser.views import UserViewSet

from .models import MenuItem, Category, Cart, OrderItem, Order
from .serializers import UserSerializer
from .serializers import (MenuItemSerializer, 
                          CategorySerializer, 
                          CartSerializer, 
                          OrderItemSerializer,
                          OrderSerializer)
from .permissions import IsInGroupManager, IsInGroupDeliveryCrew
from rest_framework.pagination import PageNumberPagination

# Create your views here.
class CustomUserViewSet(UserViewSet):
    def get_permissions(self):
        permission_classes = []
        if self.action in ['update', 'partial_update', 'destroy']:
            if not self.request.user.groups.filter(name='Manager').exists():
                raise PermissionDenied('You are not authorized.')
        elif self.action in ['list']:
            if not self.request.user.groups.filter(name='Manager').exists():
                raise PermissionDenied('You are only authorized to create a user. Viewing of all users is for Managers only.')
        return [permission() for permission in permission_classes]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ['title']
    
    def get_permissions(self):
        permission_classes = [IsAuthenticated]
        
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if not self.request.user.groups.filter(name='Manager').exists():
                raise PermissionDenied('You are not authorized.')
        
        return [permission() for permission in permission_classes]
   
    
class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.select_related('category').all()
    serializer_class = MenuItemSerializer
    ordering_fields = ['price', 'title']
    search_fields = ['title', 'category__title']

    def get_permissions(self):
        permission_classes = [IsAuthenticated]
        
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            if not self.request.user.groups.filter(name='Manager').exists():
                raise PermissionDenied('You are not authorized.')
        
        return [permission() for permission in permission_classes]
    


class GroupManagerViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(groups__name='Manager')
    serializer_class = UserSerializer
    permission_classes = [IsInGroupManager, IsAuthenticated]
    
    
    def create(self, request):
        username = request.data['username']
        if username:
            user = get_object_or_404(User, username=username)
            if user.groups.filter(name='Manager').exists():
                return Response({'message': 'User is already a Manager'}, status=status.HTTP_400_BAD_REQUEST)
            managers = Group.objects.get(name='Manager')
            managers.user_set.add(user)
            return Response({'message': 'User added to Manager group'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'error'}, status=status.HTTP_400_BAD_REQUEST)
            
    
    def destroy(self, request, pk=None):
        user = get_object_or_404(self.queryset, pk=pk)
        managers = Group.objects.get(name='Manager')
        managers.user_set.remove(user)
        return Response({'message':'User removed from Manager group'}, status=status.HTTP_200_OK)
    

class GroupDeliveryCrewViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(groups__name='Delivery Crew')
    serializer_class = UserSerializer
    permission_classes = [IsInGroupManager, IsAuthenticated]
    
    def create(self, request):
        username = request.data['username']
        if username:
            user = get_object_or_404(User, username=username)
            managers = Group.objects.get(name='Delivery Crew')
            managers.user_set.add(user)
            return Response({'message': 'User added to Manager group'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'error'}, status=status.HTTP_400_BAD_REQUEST)
            
    def destroy(self, request, pk=None):
        user = get_object_or_404(self.queryset, pk=pk)
        managers = Group.objects.get(name='Delivery Crew')
        managers.user_set.remove(user)
        return Response({'message':'User removed from Manager group'}, status=status.HTTP_200_OK)
    
    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
    
    
class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.select_related('menuitem', 'user').all()
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['menuitem__title', 'quantity', 'price', 'unit_price']
    search_fields = ['menuitem__title',]
    pagination_class = PageNumberPagination  # Add this line to use default pagination

    def list(self, request):
        user = request.user
        queryset = Cart.objects.filter(user=user)
        
        search = request.query_params.get('search', None)
        ordering = request.query_params.get('ordering', None)
        
        if ordering is not None:
            queryset = queryset.order_by(ordering)
        if search is not None:
            for search_field in self.search_fields:
                queryset = queryset.filter(**{f'{search_field}__icontains': search})
                
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_paginated_response(CartSerializer(page, many=True).data)
        else:
            serializer = CartSerializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        user = request.user
        menuitem_id = request.data['menuitem_id']
        old_cart = Cart.objects.filter(user=user, menuitem=menuitem_id)
        if old_cart:
            old_quantity = old_cart[0].quantity
            old_price = old_cart[0].price
        else:
            old_quantity = 0
            old_price = 0

        menuitem = get_object_or_404(MenuItem, pk=menuitem_id)
        quantity = int(request.data['quantity'])
        unit_price = menuitem.price
        price = (quantity * unit_price)

        new_quantity = old_quantity + quantity
        new_price = old_price + price

        cart, created = Cart.objects.update_or_create(
            user=user,
            menuitem=menuitem,
            defaults={
                'quantity': new_quantity, 
                'unit_price': unit_price, 
                'price': new_price
                }
        )

        serializer = CartSerializer(cart)

        if created:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Error saving item or it already exist'}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        user = request.user
        cart = get_object_or_404(self.queryset, pk=pk)

        if cart.user == user:
            cart.quantity = cart.quantity + int(request.data['quantity'])
            cart.price = cart.unit_price * cart.quantity
            cart.save()
            serializer = CartSerializer(cart)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'You are not authorized'}, status=status.HTTP_403_FORBIDDEN)
    
    def destroy(self, request):
        user = request.user

        Cart.objects.filter(user=user).delete()
        return Response({'message': 'Cart cleared'}, status=status.HTTP_200_OK)
             
    
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related('order_items').select_related('user', 'delivery_crew_details').all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['user__username','delivery_crew_details__username','date','status']
    search_fields = ['status','user__username']
    pagination_class = PageNumberPagination
    
    def list(self, request):
        user = request.user
        
        if user.groups.filter(name='Manager').exists():
            queryset = Order.objects.prefetch_related('order_items').select_related('user', 'delivery_crew_details').all()
            
        elif user.groups.filter(name='Delivery Crew').exists():
            queryset = Order.objects.prefetch_related('order_items').select_related('user', 'delivery_crew_details').filter(delivery_crew_details=user)
            
        else:
            queryset = Order.objects.prefetch_related('order_items').select_related('user', 'delivery_crew_details').filter(user=user)
        
        search = request.query_params.get('search', None)
        ordering = request.query_params.get('ordering', None)
        
        if search is not None:
            search_queries = Q()
            for field in self.search_fields:
                search_queries |= Q(**{f'{field}__icontains': search})
            queryset = queryset.filter(search_queries)
        
        if ordering is not None:
            queryset = queryset.order_by(ordering)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_paginated_response(OrderSerializer(page, many=True).data)
        else:
            serializer = OrderSerializer(queryset, many=True)
        return Response(serializer.data)
    

    def retrieve(self, request, pk=None):
        user = request.user
        order = get_object_or_404(self.queryset, pk=pk)
        
        if user.groups.filter(name='Manager').exists() or user.groups.filter(name='Delivery Crew').exists() or order.user == user:
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        else:
            return Response({'message': 'You are not authorized'}, status=status.HTTP_403_FORBIDDEN)
    
    
    def create(self, request):
        user = request.user
        
        orderitems = []
        total = 0
        
        try:
            with transaction.atomic():
                order = Order.objects.create(user=user, total=total)
                
                for item in Cart.objects.filter(user=user):
                    total = total + item.price
                    
                    orderitem = OrderItem.objects.create(
                        order=order, 
                        menuitem=item.menuitem, 
                        quantity=item.quantity, 
                        unit_price=item.unit_price, 
                        price=item.price
                    )
                    orderitems.append(orderitem)
                    
                    item.delete()
                        
                if total > 0:
                    order.total = total
                    order.save()
                    serializer = OrderSerializer(order)
                    # orderitems_serializer = OrderItemSerializer(orderitems, many=True)
                    
                    # return Response({'message': 'Order created', 'order': serializer.data, 'orderitems': orderitems_serializer.data}, status=status.HTTP_201_CREATED)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                else:
                    transaction.set_rollback(True)
                    return Response({'message': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message': 'An error occurred', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
    def update(self, request, pk=None):
        user = request.user
        
        if not (user.groups.filter(name='Manager').exists() or user.groups.filter(name='Delivery Crew').exists()):
            return Response({'message': 'You are not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        order = get_object_or_404(self.queryset, pk=pk)
        
        if user.groups.filter(name='Manager').exists(): 
            if request.data.get('delivery_crew'):
                delivery_crew_details = get_object_or_404(User, pk=request.data.get('delivery_crew'))
                if delivery_crew_details.groups.filter(name='Delivery Crew').exists():
                    order.delivery_crew_details = delivery_crew_details
                else:
                    return Response({'message': 'User is not a delivery crew'}, status=status.HTTP_400_BAD_REQUEST)
            
        if user.groups.filter(name='Manager').exists() or user.groups.filter(name='Delivery Crew').exists():
            if request.data.get('status'):
                try:
                    order.status = bool(int(request.data.get('status')))
                except ValueError:
                    return Response({'message': 'Invalid status value'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                order.save()
            except ValidationError as e:
                return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)        
    
    
    def partial_update(self, request, pk=None):
        user = request.user
        
        if not (user.groups.filter(name='Manager').exists() or user.groups.filter(name='Delivery Crew').exists()):
            return Response({'message': 'You are not authorized'}, status=status.HTTP_403_FORBIDDEN)
        
        order = get_object_or_404(self.queryset, pk=pk)
        
        if user.groups.filter(name='Manager').exists():
            # delivery_crew = get_object_or_404(User, pk=request.data['delivery_crew_id'])
            if request.data.get('delivery_crew'):
                delivery_crew_details = get_object_or_404(User, pk=request.data.get('delivery_crew'))
                if delivery_crew_details.groups.filter(name='Delivery Crew').exists():
                    order.delivery_crew_details = delivery_crew_details
                else:
                    return Response({'message': 'User is not a delivery crew'}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.groups.filter(name='Manager').exists() or user.groups.filter(name='Delivery Crew').exists():
            # s = request.data['status']
            s = request.data.get('status')
            if s:
                try:
                    order.status = bool(int(s))
                except ValueError:
                    return Response({'message': 'Invalid status value'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order.save()
        except ValidationError as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
        
    
    def destroy(self, request, pk=None):
        user = request.user
        
        if user.groups.filter(name='Manager').exists():
            order = get_object_or_404(self.queryset, pk=pk)
            order.delete()
            return Response({'message':'Order removed'}, status=status.HTTP_200_OK)
    
    
   