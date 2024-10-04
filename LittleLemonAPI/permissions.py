from rest_framework.permissions import BasePermission


class IsInGroup(BasePermission):
    """
    Custom permission to allow access only to users in a specific group.
    """
    def __init__(self, group_name, reverse=False):
        self.group_name = group_name
        self.reverse = reverse
    
    def has_permission(self, request, view):
        # Check if the user is authenticated and belongs to the required group
        if self.reverse:
            is_filtered_groups_exists = not request.user.groups.filter(name=self.group_name).exists()
        else:
            is_filtered_groups_exists = request.user.groups.filter(name=self.group_name).exists()
        return request.user and request.user.is_authenticated and is_filtered_groups_exists
        
class IsInGroupManager(IsInGroup):
    def __init__(self):
        super().__init__('Manager')
        
class IsInGroupDeliveryCrew(IsInGroup):
    def __init__(self):
        super().__init__('Delivery Crew')