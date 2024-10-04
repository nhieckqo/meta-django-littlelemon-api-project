import datetime
from rest_framework import serializers

from .models import MenuItem, Category, Cart, Order, OrderItem
from django.contrib.auth.models import User


class CategorySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Category
        fields = ['id', 'title', 'slug']


class MenuItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)
    price = serializers.DecimalField(max_digits=6, decimal_places=2)
    featured = serializers.BooleanField()
    title = serializers.CharField(max_length=255)
    
    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'featured', 'category', 'category_id']


class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True}
        }


class CartSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    menuitem = MenuItemSerializer(read_only=True)
    menuitem_id = serializers.IntegerField(write_only=True)
    unit_price = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    price = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    quantity = serializers.IntegerField()
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'menuitem', 'menuitem_id', 'quantity', 
                  'unit_price', 'price']


class OrderItemSerializer(serializers.ModelSerializer): 
    menuitem = MenuItemSerializer(read_only=True)
    unit_price = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    price = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    quantity = serializers.IntegerField(read_only=True)

    
    class Meta:
        model = OrderItem
        fields = ['id', 'menuitem', 'quantity', 'unit_price', 'price']
        
        
class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    delivery_crew_details = UserSerializer(read_only=True)
    delivery_crew = serializers.IntegerField(write_only=True)
    order_items = OrderItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    status = serializers.BooleanField()
    date = serializers.DateTimeField()
    
    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew', 'delivery_crew_details', 
                  'status', 'total', 'date', 'order_items']
        default = {
            'date': datetime.datetime.now(),
        }
    
    
    